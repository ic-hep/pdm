#!/usr/bin/env python
"""Worker script."""
import os
import uuid
import random
# import shlex
import socket
import subprocess
from urlparse import urlsplit, urlunsplit
from tempfile import NamedTemporaryFile
from contextlib import contextmanager

from requests.exceptions import Timeout

from pdm.framework.RESTClient import RESTClient
from pdm.cred.CredClient import CredClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.utils.daemon import Daemon
from pdm.utils.config import getConfig
from .WorkqueueDB import COMMANDMAP, PROTOCOLMAP, JobType


@contextmanager
def TempX509Files(token):
    """Create temporary grid credential files."""
    cert, key = CredClient().get_cred(token)
    with NamedTemporaryFile() as certfile,\
            NamedTemporaryFile() as keyfile:
        certfile.write(cert)
        certfile.flush()
        os.fsync(certfile.fileno())

        keyfile.wite(key)
        keyfile.flush()
        os.fsync(keyfile.fileno())
        yield certfile, keyfile


class Worker(RESTClient, Daemon):
    """Worker Daemon."""

    def __init__(self):
        """Initialisation."""
        RESTClient.__init__(self, 'workqueue')
        self._uid = uuid.uuid4()
        Daemon.__init__(self,
                        pidfile='/tmp/worker-%s.pid' % self._uid,
                        logfile='/tmp/worker-%s.log' % self._uid,
                        target=self.run)
        self._types = [JobType[type_.upper()] for type_ in  # pylint: disable=unsubscriptable-object
                       getConfig('client').get('types', ('LIST', 'COPY', 'REMOVE'))]
        self._current_process = None

    def terminate(self, *_):
        """Terminate worker daemon."""
        Daemon.terminate(self, *_)
        if self._current_process is not None:
            self._current_process.terminate()

    def run(self):
        """Daemon main method."""
        endpoint_client = EndpointClient()
        while True:
            try:
                job = self.post('jobs', data={'types': [type_.value for type_ in self._types]})
            except Timeout:
                continue

            src_endpoints = (urlsplit(site) for site in endpoint_client.get_mappings(job['src_siteid']).itervalues())
            dst_endpoints = (urlsplit(site) for site in endpoint_client.get_mappings(job['dst_siteid']).itervalues())

            src = [urlunsplit(site._replace(path=job['src_filepath'])) for site in src_endpoints if site.schema == PROTOCOLMAP[job['protocol']]]
            dst = [urlunsplit(site._replace(path=job['dst_filepath'])) for site in dst_endpoints if site.schema == PROTOCOLMAP[job['protocol']]]
            if not src:
                raise Exception("no src")
            with TempX509Files(job['credentials']) as (certfile, keyfile):
                command = "%s %s" % (COMMANDMAP[job['type']][job['protocol']], random.choice(src))
                if job['type'] == JobType.COPY and dst:
                    command += " %s" % random.choice(dst)
                # self._current_porcess = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, X509_USER_CERT=certfile.name, X509_USER_KEY=keyfile.name))
                # stdout, stderr = self._current_process.communicate(timeout=2)
                # self.put('jobs/%s' % job['id'], data={'stdout': stdout, 'stderr': stderr})
                self._current_process = subprocess.Popen('(set -x && %s)' % command,
                                                         shell=True,
                                                         stdout=subprocess.PIPE,
                                                         stderr=subprocess.STDOUT,
                                                         env=dict(os.environ,
                                                                  X509_USER_CERT=certfile.name,
                                                                  X509_USER_KEY=keyfile.name))
                log, _ = self._current_process.communicate()
                self.put('jobs/%s' % job['id'],
                         data={'log': log,
                               'returncode': self._current_process.returncode,
                               'host': socket.gethostbyaddr(socket.getfqdn)})


if __name__ == '__main__':
    Worker().start()
