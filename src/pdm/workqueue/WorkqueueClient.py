#!/usr/bin/env python
""" Client for Workqueue application. """

from pdm.framework.RESTClient import RESTClient
from .WorkqueueDB import JobProtocol

class WorkqueueClient(RESTClient):
    """ A client class for WorkqueueService. """

    def __init__(self):
        """ Load config & configure client. """
        super(WorkqueueClient, self).__init__('workqueue')

    def list(self, user, src_siteid, credentials, max_tries=2, priority=5 , protocol=JobProtocol.GRIDFTP):
        """ Call the hello function on the server and return the result.
        """
        return self.post('list', data={'user': user,
                                       'src_siteid': src_siteid,
                                       'credentials': credentials,
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol})

    def copy(self, user, src_siteid, dst_siteid, credentials, max_tries, priority, protocol):
        """ Returns a dict of turtles.
            Key is ID (tid) and value is turtle name.
        """
        return self.post('copy', data={'user': user,
                                       'src_siteid': src_siteid,
                                       'dst_siteid': dst_siteid,
                                       'credentials': credentials,
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol})

    def remove(self, user, src_siteid, credentials, max_tries, priority, protocol):
        return self.post('remove', data={'user': user,
                                         'src_siteid': src_siteid,
                                         'credentials': credentials,
                                         'max_tries': max_tries,
                                         'priority':  priority,
                                         'protocol': protocol})
