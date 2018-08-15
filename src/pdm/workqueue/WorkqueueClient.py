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
            max_tries (int): The maximum number of times to attempt the copy. (default: 2)
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
            max_tries (int): The maximum number of times to attempt the remove. (default: 2)
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

    def rename(self, siteid, src_filepath,  # pylint: disable=too-many-arguments
               dst_filepath, max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP, **kwargs):
        """
        Rename a filepath.

        Variable keyword args are passed directly on to the worker script as extra_opts.

        Args:
            siteid (int): The id of the site containing the filepath to be renamed.
            src_filepath (str): The filepath to rename.
            dst_filepath (str): The new filepath.
            max_tries (int): The maximum number of times to attempt the rename. (default: 2)
            priority (int): The DIRAC priority (0-9) of the job. (default: 5)
            protocol (JobProtocol): The protocol type to use. (default: GRIDFTP)

        Returns:
            dict: The job object as stored in the workqueue database.
        """
        return self.post('rename', data={'src_siteid': siteid,
                                         'src_filepath': src_filepath,
                                         'dst_siteid': siteid,
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
            max_tries (int): The maximum number of times to attempt the mkdir. (default: 2)
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
            list: the jobs elements as dicts.
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

        Gets the output for all attempts, for all elements of the given job if they are ready. The
        optional parameter element_id allows the user to get the output for a given job element,
        while attempt allows the user to get the output for a given attempt of a specific element.

        Note:
             Specifying attempt without an element_id is an error and will not return that attempt
             for all elements but will instead be ignored and the user will get the output for all
             attempts, for all elements.

        Args:
            job_id (int): The id number of the job to fetch latest output from.
            element_id (int): The id number of the job element to fetch latest output from.
                              (default: None = all)
            attempt (int): The attempt number to get the output from. This may be negative in order
                           to index from the back. (default: None = all)

        Returns:
            list: List of lists with the outer list being the list of elements for the given job,
                  or a single element if element_id is specified. The inner list represents the
                  attempts, or a single attempt if attempt is given. Each attempt is a dictionary
                  with keys (jobid, elementid, attempt, type, status, log, (listing)). Log is the
                  contents of the log file for that attempt. If the job element in question was a
                  LIST type job then there will be the additional key "listing" which will be a JSON
                  encoded dictionary of form {directory: [files],...}.

        Examples:
            >>> WorkqueueClient().output(12)
            [
              [
                {
                  "jobid": 12,
                  "elementid": 0,
                  "attempt": 1,
                  "type": "LIST",
                  "status": "DONE",
                  "log": "The output from the LIST command for file1 run on the worker",
                  "listing": {"root": ["file1", "file2"]}
                }
              ],
              [
                {
                  "jobid": 12,
                  "elementid": 1,
                  "attempt": 1,
                  "type": "COPY",
                  "status": "FAILED",
                  "log": "The output from the COPY command run on the worker"
                },
                {
                  "jobid": 12,
                  "elementid": 1,
                  "attempt": 2,
                  "type": "COPY",
                  "status": "DONE",
                  "log": "The output from the COPY command run on the worker"
                }
              ]
            ]

            >>> WorkqueueClient().output(12, 1)
            [
              [
                {
                  "jobid": 12,
                  "elementid": 1,
                  "attempt": 1,
                  "type": "COPY",
                  "status": "FAILED",
                  "log": "The output from the COPY command run on the worker"
                },
                {
                  "jobid": 12,
                  "elementid": 1,
                  "attempt": 2,
                  "type": "COPY",
                  "status": "DONE",
                  "log": "The output from the COPY command run on the worker"
                }
              ]
            ]

            >>> WorkqueueClient().output(12, 1, 1)
            [
              [
                {
                  "jobid": 12,
                  "elementid": 1,
                  "attempt": 1,
                  "type": "COPY",
                  "status": "FAILED",
                  "log": "The output from the COPY command run on the worker"
                }
              ]
            ]
        """
        if element_id is None:
            return self.get('jobs/%s/output' % job_id)
        if attempt is None:
            return [self.get('jobs/%s/elements/%s/output' % (job_id, element_id))]
        return [[self.get('jobs/%s/elements/%s/output/%s' % (job_id, element_id, attempt))]]
