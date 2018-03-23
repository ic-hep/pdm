"""Workqueue Service."""
import os
import json
import re
from functools import wraps

from flask import request, abort, current_app

from pdm.framework.FlaskWrapper import export_ext, db_model, jsonify, startup
from pdm.userservicedesk.HRService import HRService

from .WorkqueueDB import WorkqueueModels, WorkqueueJobEncoder, JobStatus, JobType, JobProtocol


SHELLPATH_REGEX = re.compile(r'^/[a-zA-Z0-9/_.*~-]*$')
LISTPARSE_REGEX = re.compile(r'^(?=[-dlpscbD])(?P<permissions>\S+)\s+'
                             r'(?P<nlinks>\S+)\s+'
                             r'(?P<userid>\S+)\s+'
                             r'(?P<groupid>\S+)\s+'
                             r'(?P<size>\S+)\s+'
                             r'(?P<datestamp>\S+\s+\S+\s+\S+)\s+'
                             r'(?P<name>[^\t\n\r\f\v]*)\s*$', re.MULTILINE)


def decode_json_data(func):
    """Decorator to automatically decode json data."""
    @wraps(func)
    def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
        if not isinstance(request.data, dict):
            request.data = json.loads(request.data)
        return func(*args, **kwargs)
    return wrapper


@export_ext("/workqueue/api/v1.0")
@db_model(WorkqueueModels)
class WorkqueueService(object):
    """Workqueue Service."""

    @staticmethod
    @startup
    def configure_workqueueservice(config):
        """Setup the WorkqueueService."""
        current_app.workqueueservice_workerlogs = config.pop('workerlogs', '/tmp/workers')

    @staticmethod
    @export_ext('worker', ["POST"])
    @decode_json_data
    def get_next_job():
        """Get the next job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter(Job.status.in_((JobStatus.NEW, JobStatus.FAILED)),
                               Job.type.in_(request.data['types']),
                               Job.attempts <= Job.max_tries)\
                       .order_by(Job.priority)\
                       .first_or_404()
        job.status = JobStatus.SUBMITTED
        job.update()
        return jsonify((job, request.token_svc.issue(str(job.id))))

    @staticmethod
    @export_ext('worker/<int:job_id>', ['PUT'])
    @decode_json_data
    def return_output(job_id):
        """Return a job."""
        if not request.token_ok:
            abort(403, description="Invalid token")
        if int(request.token) != job_id:
            abort(403, description="Token not valid for job %d" % job_id)

        # Update job status.
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.get_or_404(job_id)
        job.attempts += 1
        job.status = JobStatus.DONE
        if request.data['returncode'] != 0:
            job.status = JobStatus.FAILED
        job.update()

        # Write log file.
        dir_ = os.path.join(current_app.workqueueservice_workerlogs,
                            job.log_uid[:2],
                            job.log_uid)
        if not os.path.exists(dir_):
            os.makedirs(dir_)
        with open(os.path.join(dir_, 'attempt%i.log' % job.attempts), 'wb') as logfile:
            logfile.write("Job run on host: %s\n" % request.data['host'])
            logfile.write(request.data['log'])
        return '', 200

    @staticmethod
    @export_ext("jobs", ['POST'])
    @decode_json_data
    def post_job():
        """Add a job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        allowed_attrs = require_attrs('type', 'src_siteid', 'src_filepath') +\
                        ('credentials', 'max_tries', 'priority', 'protocol', 'extra_opts')
        request.data['type'] = to_enum(request.data['type'], JobType)
        request.data['src_filepath'] = shellpath_sanitise(request.data['src_filepath'])
        if 'protocol' in request.data:
            request.data['protocol'] = to_enum(request.data['protocol'], JobProtocol)
        if request.data['type'] == JobType.COPY:
            allowed_attrs += require_attrs('dst_siteid', 'dst_filepath')
            request.data['dst_filepath'] = shellpath_sanitise(request.data['dst_filepath'])
        job = Job(user_id=HRService.check_token(), **subdict(request.data, allowed_attrs))
        job.add()
        return job.enum_json()

    @staticmethod
    @export_ext('list', ['POST'])
    @decode_json_data
    def list():
        """List a remote dir."""
        request.data['type'] = JobType.LIST
        return WorkqueueService.post_job()

    @staticmethod
    @export_ext('copy', ['POST'])
    @decode_json_data
    def copy():
        """Copy."""
        request.data['type'] = JobType.COPY
        return WorkqueueService.post_job()

    @staticmethod
    @export_ext('remove', ['POST'])
    @decode_json_data
    def remove():
        """Remove."""
        request.data['type'] = JobType.REMOVE
        return WorkqueueService.post_job()

    @staticmethod
    @export_ext("jobs", ['GET'])
    def get_jobs():
        """Get all jobs for a user."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        return json.dumps(Job.query.filter_by(user_id=HRService.check_token()).all(),
                          cls=WorkqueueJobEncoder)

    @staticmethod
    @export_ext("jobs/<int:job_id>", ['GET'])
    def get_job(job_id):
        """Get job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .first_or_404()
        return job.enum_json()

    @staticmethod
    @export_ext('jobs/<int:job_id>/output', ['GET'])
    def get_output(job_id):
        """Get job output."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .filter(Job.status.in_((JobStatus.DONE, JobStatus.FAILED)))\
                       .first_or_404()
        logfilename = os.path.join(current_app.workqueueservice_workerlogs,
                                   job.log_uid[:2],
                                   job.log_uid,
                                   "attempt%i.log" % job.attempts)
        if not os.path.exists(logfilename):
            abort(500, description="log directory/file not found.")
        with open(logfilename, 'rb') as logfile:
            log = logfile.read()

        return_dict = {'jobid': job.id, 'log': log}
        if job.type == JobType.LIST:
            return_dict.update(listing=[dict(match.groupdict(),
                                             is_directory=match.group('permissions')
                                                               .startswith('d'))
                                        for match in LISTPARSE_REGEX.finditer(log)])
        return json.dumps(return_dict)

    @staticmethod
    @export_ext("jobs/<int:job_id>/status", ['GET'])
    def get_status(job_id):
        """Get job status."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .first_or_404()
        # pylint: disable=no-member
        return json.dumps({'jobid': job.id, 'status': JobStatus(job.status).name})


def subdict(dct, keys):
    """Create a sub dictionary."""
    return {k: dct[k] for k in keys if k in dct}


def shellpath_sanitise(path):
    """Sanitise the path for use in bash shell."""
    if SHELLPATH_REGEX.match(path) is None:
        abort(400, description="Possible injection content in filepath '%s'" % path)
    return path


def require_attrs(*attrs):
    """Require the given attrs."""
    required = set(attrs).difference(request.data)
    if required:
        abort(400, description="Missing data attributes: %s" % list(required))
    return attrs


def to_enum(obj, enum_type):
    """Convert arg to enum."""
    if isinstance(obj, enum_type):
        return obj
    if isinstance(obj, int):
        try:
            return enum_type(obj)
        except ValueError as err:
            abort(400, description=err.message)
    if isinstance(obj, basestring):
        if obj.isdigit():
            try:
                return enum_type(int(obj))
            except ValueError as err:
                abort(400, description=err.message)
        try:
            return enum_type[obj.upper()]
        except KeyError as err:
            abort(400, description="%s is not a valid %s" % (err.message, enum_type.__name__))
    abort(400, description="Failed to convert '%s' to enum type '%s'" % (obj, enum_type))
