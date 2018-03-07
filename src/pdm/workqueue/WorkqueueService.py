"""Workqueue Service."""
import os
import json
import re

from flask import request, abort

from pdm.framework.FlaskWrapper import export_ext, db_model
from pdm.utils.config import getConfig
from pdm.userservicedesk.HRService import HRService

from .WorkqueueDB import WorkqueueModels, JobStatus, JobType


SHELLPATH_REGEX = re.compile(r'^/[a-zA-Z0-9/-_.*]*$')
LISTPARSE_REGEX = re.compile(r'^(?P<permissions>\S+)\s+'
                             '(?P<nlinks>\S+)\s+'
                             '(?P<userid>\S+)\s+'
                             '(?P<groupid>\S+)\s+'
                             '(?P<size>\S+)\s+'
                             '(?P<datestamp>\S+\s+\S+\s+\S+)\s+'
                             '(?P<name>.*)$', re.MULTILINE)


@export_ext("/workqueue/api/v1.0")
@db_model(WorkqueueModels)
class WorkqueueService(object):
    """Workqueue Service."""

    @staticmethod
    @export_ext('worker', ["POST"])
    def get_next_job():
        """Get the next job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter(Job.status.in_(JobStatus.NEW, JobStatus.FAILED),
                               Job.type.in_(request.data['types']),
                               Job.attempts <= Job.max_tries)\
                       .order_by(Job.priority)\
                       .first_or_404()
        job.status = JobStatus.SUBMITTED
        job.update()
        return job.json()

    @staticmethod
    @export_ext('worker/<int:job_id>', ['PUT'])
    def return_output(job_id):
        """Return a job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name

        # Update job status.
        job = Job.query.filter_by(id=job_id).get_or_404()
        job.attempts += 1
        job.status = JobStatus.DONE
        if request.data['returncode'] != 0:
            job.status = JobStatus.FAILED
        job.update()

        # Write log file.
        dir_ = os.path.join(getConfig("app/workqueue").get('workerlogs', '/tmp/workers'),
                            job.log_uid[:2],
                            job.log_uid)
        os.makedirs(dir_)
        with open(os.path.join(dir_, 'attempt%i.log' % job.attempts), 'wb') as logfile:
            logfile.write("Job run on host: %s\n" % request.data['host'])
            logfile.write(request.data['log'])

    @staticmethod
    @export_ext("jobs", ['POST'])
    def post_job():
        """Add a job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        allowed_attrs = require_attrs('type', 'src_siteid', 'src_filepath') +\
                        ('credentials', 'max_tries', 'priority', 'protocol')
        request.data['src_filepath'] = shellpath_sanitise(request.data['src_filepath'])
        if request.data['type'] == JobType.COPY:
            allowed_attrs += require_attrs('dst_siteid', 'dst_filepath')
            request.data['dst_filepath'] = shellpath_sanitise(request.data['dst_filepath'])
        job = Job(user_id=HRService.check_token(), **subdict(request.data, allowed_attrs))
        job.add()
        return job.json()

    @staticmethod
    @export_ext('list', ['POST'])
    def list():
        """List a remote dir."""
        request.data['type'] = JobType.LIST
        return WorkqueueService.post_job()
#        Job = request.db.tables.Job
#        allowed_attrs = require_attrs('src_siteid', 'src_filepath')\
#                        + ('credentials', 'max_tries', 'priority', 'protocol')
#        request.data['src_filepath'] = shellpath_sanitise(request.data['src_filepath'])
#        # user_id to be replaced with one extracted via token from Janusz's service.
#        job = Job(user_id=get_user_id(), type=JobType.LIST, **subdict(request.data, allowed_attrs))
#        job.add()
#        return json.dumps(job, cls=JSONTableEncoder)

    @staticmethod
    @export_ext('copy', ['POST'])
    def copy():
        """Copy."""
        request.data['type'] = JobType.COPY
        return WorkqueueService.post_job()
#        Job = request.db.tables.Job
#        allowed_attrs = require_attrs('src_siteid', 'src_filepath', 'dst_siteid', 'dst_filepath')\
#                        +('credentials', 'max_tries', 'priority', 'protocol')
#        request.data['src_filepath'] = shellpath_sanitise(request.data['src_filepath'])
#        request.data['dst_filepath'] = shellpath_sanitise(request.data['dst_filepath'])
#        job = Job(user_id=get_user_id(), type=JobType.COPY, **subdict(request.data, allowed_attrs))
#        job.add()
#        return json.dumps(job, cls=JSONTableEncoder)

    @staticmethod
    @export_ext('remove', ['POST'])
    def remove():
        """Remove."""
        request.data['type'] = JobType.REMOVE
        return WorkqueueService.post_job()
#        Job = request.db.tables.Job
#        allowed_attrs = require_attrs('src_siteid', 'src_filepath') +\
#                        ('credentials', 'max_tries', 'priority', 'protocol')
#        request.data['src_filepath'] = shellpath_sanitise(request.data['src_filepath'])
#        job = Job(user_id=get_user_id(), type=JobType.REMOVE, **subdict(request.data, allowed_attrs))
#        job.add()
#        return json.dumps(job, cls=JSONTableEncoder)

    @staticmethod
    @export_ext("jobs/<int:job_id>", ['GET'])
    def get_job(job_id):
        """Get job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id)\
                       .get_or_404()
        return job.json()

    @staticmethod
    @export_ext('jobs/<int:job_id>/output', ['GET'])
    def get_output(job_id):
        """Get job output."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id)\
                       .filter(Job.status.in_(JobStatus.DONE, JobStatus.FAILED))\
                       .get_or_404()
        dir_ = os.path.join(getConfig("app/workqueue").get('workerlogs', '/tmp/workers'),
                            job.log.guid[:2],
                            job.log.guid)
        with open(os.path.join(dir_, "attempt%i.log" % job.attempts, 'rb')) as logfile:
            log = logfile.read()

        return_dict = {'jobid': job.id, 'log': log}
        if job.type == JobType.LIST:
            return_dict.update(listing=[dict(match.groupdict(),
                                             is_directory=match.group('permissions').startswith('d'))
                                        for match in LISTPARSE_REGEX.finditer(log)])
        return json.dumps(return_dict)

    @staticmethod
    @export_ext("jobs/<int:job_id>/status", ['GET'])
    def get_status(job_id):
        """Get job status."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id)\
                       .get_or_404()
        return json.dumps({'jobid': job.id, 'status': job.status.name})


def subdict(dct, keys):
    """Create a sub dictionary."""
    return {k: dct[k] for k in keys if k in dct}


def shellpath_sanitise(path):
    """Sanitise the path for use in bash shell."""
    if SHELLPATH_REGEX.match(path) is None:
        abort(400)
    return path


def require_attrs(*attrs):
    """Require the given attrs."""
    if set(attrs).difference_update(request.data):
        abort(400)
    return attrs


#def get_user_id():
#    """Placeholder for Janusz code to get token from request and return id."""
#    # request.token -> id
#    return 1
