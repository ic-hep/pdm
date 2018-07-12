#!/usr/bin/env python
"""Client for Workqueue application."""
from pdm.framework.RESTClient import RESTClient

from .WorkqueueDB import JobProtocol


class WorkqueueClient(RESTClient):
    """A client class for WorkqueueService."""

    def __init__(self):
        """Load config & configure client."""
        super(WorkqueueClient, self).__init__('workqueue')

    def list(self, siteid, filepath,  # pylint: disable=too-many-arguments
             max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        List a given path.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            siteid (int): The id of the site containing the path to be listed.
            filepath (str): The path to list.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('list', data={'src_siteid': siteid,
                                       'src_filepath': filepath,
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol,
                                       'extra_opts': kwargs})

    def copy(self, src_siteid, src_filepath, dst_siteid,  # pylint: disable=too-many-arguments
             dst_filepath, max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        Copy a one path to another.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            src_siteid (int): The id of the site containing the path to be copied from.
            src_filepath (str): The path to copy from.
            dst_siteid (int): The id of the site containing the path to be copied to.
            dst_filepath (str): The path to copy to.
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
                                       'max_tries': max_tries,
                                       'priority':  priority,
                                       'protocol': protocol,
                                       'extra_opts': kwargs})

    def remove(self, siteid, filepath,  # pylint: disable=too-many-arguments
               max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        Remove a given path.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            siteid (int): The id of the site containing the path to be removed.
            filepath (str): The path to remove.
            credentials (str): Token allowing access to the users credentials from the cred service.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('remove', data={'src_siteid': siteid,
                                         'src_filepath': filepath,
                                         'max_tries': max_tries,
                                         'priority':  priority,
                                         'protocol': protocol,
                                         'extra_opts': kwargs})

    def rename(self, src_siteid, src_filepath,  # pylint: disable=too-many-arguments
               dst_filepath, max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        Rename a filepath.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            src_siteid (int): The id of the site containing the filepath to be renamed.
            src_filepath (str): The filepath to rename.
            dst_filepath (str): The new filepath.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('rename', data={'src_siteid': src_siteid,
                                         'src_filepath': src_filepath,
                                         'dst_siteid': src_siteid,
                                         'dst_filepath': dst_filepath,
                                         'max_tries': max_tries,
                                         'priority':  priority,
                                         'protocol': protocol,
                                         'extra_opts': kwargs})

    def mkdir(self, siteid, filepath,  # pylint: disable=too-many-arguments
              max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        Make a directory.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            siteid (int): The id of the site containing the dir path to be created.
            filepath (str): The dir path to create.
            credentials (str): Token allowing access to the users credentials from the cred service.
            max_tries (int): The maximum number of times to attempt the listing. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('mkdir', data={'src_siteid': siteid,
                                        'src_filepath': filepath,
                                        'max_tries': max_tries,
                                        'priority':  priority,
                                        'protocol': protocol,
                                        'extra_opts': kwargs})

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

    def elements(self, job_id):
        """
        Get a job elements for job with given id.

        Args:
            job_id (int): The id number of the job containing elements to get.

        Returns:
            dict: the jobs elements as dicts.
        """
        return self.get('jobs/%s/elements' % job_id)

    def element(self, job_id, element_id):
        """
        Get a job element by id.

        Args:
            job_id (int): The id number of the job to get.
            element_id (int): The id number of the job element to get.

        Returns:
            dict: Representation of job element.
        """
        return self.get('jobs/%s/elements/%s' % (job_id, element_id))

    def status(self, job_id, element_id=None):
        """
        Get a jobs status.

        This returns the human readable status rather than the integer code. This
        function will also retrieve the number of attempts the system has made for the
        given job.

        Args:
            job_id (int): The id number of the job to query.
            element_id (int): The id number of the job element to query.

        Returns:
            dict: Representation of the status with keys (jobid, status, attempts(element only) )
        """
        if element_id is None:
            return self.get('jobs/%s/status' % job_id)
        return self.get('jobs/%s/elements/%s/status' % (job_id, element_id))

    def output(self, job_id, element_id=None, attempt=None):
        """
        Get job output.

        Gets the output for the given job element if it's ready. The optional parameter attempt
        allows the user to get the output for a given attempt. If this parameter is None
        (the default) then the latest attempts output is retrieved.

        Args:
            job_id (int): The id number of the job to fetch output from.
            element_id (int): The id number of the job element to fetch output from.
                              (default: None = first)
            attempt (int): The attempt number to get the output from. (default: None = latest)

        Returns:
            dict: Representation of the output with keys (jobid, elementid, type, log).
                  log is the contents of the job elements log file. If the job element in question
                  was a LIST type job then there will be the additional key "listing" which will be
                  a JSON encoded list of files/directories each as a dict.
        """
        if element_id is None:
            return self.get('jobs/%s/output' % job_id)
        if attempt is None:
            return self.get('jobs/%s/elements/%s/output' % (job_id, element_id))
        return self.get('jobs/%s/elements/%s/output/%s' % (job_id, element_id, attempt))
