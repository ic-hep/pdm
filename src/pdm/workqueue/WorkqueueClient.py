#!/usr/bin/env python
"""Client for Workqueue application."""
import json
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
        return self.post('list', data=json.dumps({'src_siteid': src_siteid,
                                                  'src_filepath': src_filepath,
                                                  'credentials': credentials,
                                                  'max_tries': max_tries,
                                                  'priority':  priority,
                                                  'protocol': protocol}))

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
        return self.post('copy', data=json.dumps({'src_siteid': src_siteid,
                                                  'src_filepath': src_filepath,
                                                  'dst_siteid': dst_siteid,
                                                  'dst_filepath': dst_filepath,
                                                  'credentials': credentials,
                                                  'max_tries': max_tries,
                                                  'priority':  priority,
                                                  'protocol': protocol}))

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
        return self.post('remove', data=json.dumps({'src_siteid': src_siteid,
                                                    'src_filepath': src_filepath,
                                                    'credentials': credentials,
                                                    'max_tries': max_tries,
                                                    'priority':  priority,
                                                    'protocol': protocol}))

    def jobs(self):
        """
        Get all jobs for a user.

        Returns:
            list: The users jobs as dicts.
        """
        return self.get('jobs')

    def job(self, job_id):
        """
        Get a job by id.

        Args:
            job_id (int): The id number of the job to get.

        Returns:
            dict: Representation of job.
        """
        return self.get('jobs/%s' % job_id)

    def status(self, job_id):
        """
        Get a jobs status.

        This returns the human readable status rather than the integer code.

        Args:
            job_id (int): The id number of the job to query.

        Returns:
            dict: Representation of the status with keys (jobid, status)
        """
        return self.get('jobs/%s/status' % job_id)

    def output(self, job_id):
        """
        Get job output.

        Gets the output for the given job if it's ready.

        Args:
            job_id (int): The id number of the job to fetch output from.

        Returns:
            dict: Representation of the output with keys (jobid, log).
                  log is the contents of the job log file. If the job in question was a LIST type
                  job then there will be the additional key "listing" which will be a JSON encoded
                  list of files/directories each as a dict containing the following keys:
                  (permissions, nlinks, userid, groupid, size, datestamp, name, is_directory).
            """
        return self.get('jobs/%s/output' % job_id)
