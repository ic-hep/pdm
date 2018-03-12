from datetime import datetime
import json
from json import JSONEncoder
import socket
import asyncore
import logging
from textwrap import dedent

from pdm.workqueue.sql.models import Job
from pdm.workqueue.sql.enums import JobStatus

class JSONJobEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Job):
            return {i:k for i, k in obj.__dict__.iteritems() if i in obj.__table__.columns}
        return super(test, self).default(obj)


class QueueManager(asyncore.dispatcher):
    """Receives connections and establishes handlers for each client.
    """
    
    def __init__(self, address, semaphore):
        asyncore.dispatcher.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.semaphore = semaphore
        self.logger.debug('binding to %s', self.address)
        self.listen(1)

    def handle_accept(self):
        sock, address = self.accept()
        self.logger.debug('handle_accept() -> %s', address)
        WorkerHandler(sock=sock, semaphore=self.semaphore)
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return

class WorkerHandler(asyncore.dispatcher):
    """Handles echoing messages from a single client.
    """
    
    def __init__(self, sock, semaphore):
        asyncore.dispatcher.__init__(self, sock=sock)
        self.logger = logging.getLogger('WorkerHandler%s' % str(sock.getsockname()))
        self.semaphore = semaphore
   
    def handle_read(self):
        """Read an incoming message from the client and put it into our outgoing queue."""
        data = self.recv(256)
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)

    def writable(self):
        return self.semaphore.acquire(False)

    def handle_write(self):
        job = Job.query.filter_by(status=JobStatus.NEW.name)\
                       .order_by(Job.priority)\
                       .first()
        if job is not None:
            self.send(dedent(r'''
            HTTP/1.1 200 OK
            Content-Type: application/json

            %s
            ''' % json.dumps(job, cls=JSONJobEncoder)).strip())
            job.status = JobStatus.SUBMITTED.name
            job.update()
        else:
            self.send(dedent(r'''
            HTTP/1.1 500 Bad
            ''').strip()) 
        self.handle_close()

    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
