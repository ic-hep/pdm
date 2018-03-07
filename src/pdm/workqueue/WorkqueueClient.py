#!/usr/bin/env python
"""Client for Workqueue application."""
from pdm.framework.RESTClient import RESTClient

from .WorkqueueDB import JobProtocol


class WorkqueueClient(RESTClient):
    """A client class for WorkqueueService."""

    def __init__(self):
        """Load config & configure client."""
        super(WorkqueueClient, self).__init__('workqueue')

    def list(self, src_siteid, src_filepath, credentials,  # pylint: disable=too-many-arguments
             max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP):
        """
        List a given path.

        Args:
            src_siteid (int): The id of the site containing the path to be listed.
            src_filepath (str): The path to list.
            credentials (str): Token allowing access to the users credentials from the cred service.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('list', data={'src_siteid': src_siteid,
                                       'src_filepath': src_filepath,
                                       'credentials': credentials,
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol}).data

    def copy(self, src_siteid, src_filepath, dst_siteid,  # pylint: disable=too-many-arguments
             dst_filepath, credentials, max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP):
        """
        Copy a one path to another.

        Args:
            src_siteid (int): The id of the site containing the path to be copied from.
            src_filepath (str): The path to copy from.
            dst_siteid (int): The id of the site containing the path to be copied to.
            dst_filepath (str): The path to copy to.
            credentials (str): Token allowing access to the users credentials from the cred service.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('copy', data={'src_siteid': src_siteid,
                                       'src_filepath': src_filepath,
                                       'dst_siteid': dst_siteid,
                                       'dst_filepath': dst_filepath,
                                       'credentials': credentials,
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol}).data

    def remove(self, src_siteid, src_filepath, credentials,  # pylint: disable=too-many-arguments
               max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP):
        """
        Remove a given path.

        Args:
            src_siteid (int): The id of the site containing the path to be removed.
            src_filepath (str): The path to remove.
            credentials (str): Token allowing access to the users credentials from the cred service.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('remove', data={'src_siteid': src_siteid,
                                         'src_filepath': src_filepath,
                                         'credentials': credentials,
                                         'max_tries': max_tries,
                                         'priority':  priority,
                                         'protocol': protocol}).data
