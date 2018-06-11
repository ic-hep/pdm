"""Workqueue Service."""
import os
import stat
from enum import Enum
from functools import partial
from itertools import groupby
from operator import attrgetter
from pprint import pformat

from flask import request, abort, current_app
# from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import export_ext, db_model, startup, decode_json_data
from pdm.userservicedesk.HRService import HRService
from pdm.site.SiteClient import SiteClient
from .WorkqueueDB import WorkqueueModels, JobStatus, JobType


def require_attrs(*attrs):
    """Require the given attrs."""
    required = set(attrs).difference(request.data)
    if required:
        abort(400, description="Missing data attributes: %s" % list(required))
    return attrs


def by_number(limit=20):
    """Extract next n job elements."""
    Job = request.db.tables.Job  # pylint: disable=invalid-name
    JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
    return JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
                                   JobElement.attempts < JobElement.max_tries)\
                           .join(JobElement.job)\
                           .filter(Job.type.in_(request.data['types']))\
                           .order_by(Job.priority)\
                           .order_by(Job.id)\
                           .order_by(Job.status)\
                           .with_for_update()\
                           .limit(limit)\
                           .all()


def by_size(size=150000000, list_limit=20):
    """Extract job elements up to size."""
    Job = request.db.tables.Job  # pylint: disable=invalid-name
    JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
    elements = JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
                                       JobElement.attempts < JobElement.max_tries)\
                               .join(JobElement.job)\
                               .filter(Job.type.in_(request.data['types']))\
                               .order_by(Job.priority)\
                               .order_by(Job.id)\
                               .order_by(Job.status)\
                               .order_by(JobElement.size.desc())\
                               .with_for_update()
#                               .limit(limit)
#                               .all()  # without this line we have a generator.
    list_count = 0
    total_size = 0
    ret = []
    for element in elements:
        if total_size + element.size > size:
            continue
        if element.type == JobType.LIST:
            list_count += 1
            if list_count > list_limit:
                continue
        total_size += element.size
        ret.append(element)

    return ret


class Algorithm(Enum):  # pylint: disable=too-few-public-methods
    """JobElement extraction algorithms."""

    # could use a wrapper here instead of partial, but cant just use function as it will be
    # considered a method of Algorithm rather than a member of the enum
    BY_NUMBER = partial(by_number)
    BY_SIZE = partial(by_size)

    def __call__(self, *args, **kwargs):
        """Call algorithm."""
        return self.value(*args, **kwargs)


@export_ext("/workqueue/api/v1.0")
@db_model(WorkqueueModels)
class WorkqueueService(object):
    """Workqueue Service."""

    @staticmethod
    @startup
    def configure_workqueueservice(config):
        """Setup the WorkqueueService."""
        current_app.workqueueservice_workerlogs = config.pop('workerlogs', '/tmp/workers')
        current_app.site_client = SiteClient()

    @staticmethod
    @export_ext('worker/jobs', ["POST"])
    @decode_json_data
    def get_next_job():
        """Get the next job."""
        current_app.log.debug("Worker requesting job batch, request: %s", pformat(request.data))
        require_attrs('types')
#        Job = request.db.tables.Job  # pylint: disable=invalid-name
#        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        alg_name = request.data.get('algorithm', 'BY_NUMBER').upper()
        elements = Algorithm[alg_name](**request.data.get('alg_args', {}))
#       elements = JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
#                                           JobElement.attempts < JobElement.max_tries)\
#                                   .join(JobElement.job)\
#                                   .filter(Job.type.in_(request.data['types']))\
#                                   .order_by(Job.priority)\
#                                   .order_by(Job.id)\
#                                   .limit(10)\
#                                   .all()
        if not elements:
            abort(404, description="No work to be done.")

        work = []
        for job, elements_group in groupby(elements, key=attrgetter('job')):
            elements = []
#            for element in list(elements_group):
            for element in iter(elements_group):
                element.status = JobStatus.SUBMITTED
                element.update()  # should be a bulk update
                element_dict = element.asdict()
                element_dict['token'] = request.token_svc.issue("%d.%d" % (job.id, element.id))
                elements.append(element_dict)
            job.status = max(ele.status for ele in job.elements)
            job_dict = job.asdict()
            job_dict['elements'] = elements
            work.append(job_dict)
            job.update()
        current_app.log.debug("Sending worker job batch: %s", pformat(work))
        return jsonify(work)

    # pylint: disable=too-many-branches, too-many-locals, too-many-statements
    @staticmethod
    @export_ext('worker/jobs/<int:job_id>/elements/<int:element_id>', ['PUT'])
    @decode_json_data
    def return_output(job_id, element_id):
        """Return a job."""
        if not request.token_ok:
            abort(403, description="Invalid token")
        if request.token != '%d.%d' % (job_id, element_id):
            abort(403,
                  description="Token not valid for element %d of job %d" % (element_id, job_id))
        current_app.log.debug("Received data from worker for job.element %s.%s: %s",
                              job_id, element_id, pformat(request.data))
        require_attrs('returncode', 'host', 'log')

        # Update job status.
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        element = JobElement.query.get_or_404((element_id, job_id))
        if element.type == JobType.LIST and request.data['returncode'] == 0:
            require_attrs('listing')
            element.listing = request.data['listing']
        element.attempts += 1
        element.status = JobStatus.DONE if request.data['returncode'] == 0 else JobStatus.FAILED
        element.update()

#    Job = request.db.tables.Job
#    try:
#        job = Job.query.filter_by(id=job_id).one()
#    except NoResultFound:
#        abort(500, description="Couldn't find job with id %d even after updating element" % job_id)
#    except MultipleResultsFound:
#        abort(500, description="Multiple jobs with id %d found!" % job_id)
        job = element.job
        job.status = max(ele.status for ele in job.elements)

        # Write log file.
        dir_ = os.path.join(current_app.workqueueservice_workerlogs,
                            job.log_uid[:2],
                            job.log_uid,
                            str(element_id))
        if not os.path.exists(dir_):
            os.makedirs(dir_)
        with open(os.path.join(dir_, 'attempt%i.log' % element.attempts), 'wb') as logfile:
            logfile.write("Job run on host: %s\n" % request.data['host'])
            logfile.write(request.data['log'])

        # Expand listing for COPY or REMOVE jobs.
        if job.type == JobType.COPY\
            and element.type == JobType.LIST\
                and element.status == JobStatus.DONE:
            element_counter = 0
            dir_copy = False
            for root, listing in sorted(element.listing.iteritems(), key=lambda item: len(item[0])):
                # is int cast necessary?
                files = [file_ for file_ in listing if stat.S_ISREG(int(file_['st_mode'])) and
                         file_['name'] not in ('.', '..')]  # gfal treats . and .. as files??!
                if len(files) != len(listing):
                    dir_copy = True
                for file_ in files:
                    element_counter += 1
                    src_filepath = os.path.join(root, file_['name'])
                    common_prefix_length = len(os.path.commonprefix((src_filepath,
                                                                     job.src_filepath)))
                    rel_filepath = src_filepath[common_prefix_length:].lstrip('/')
                    dst_filepath = job.dst_filepath
                    if rel_filepath and dir_copy:
                        dst_filepath = os.path.join(job.dst_filepath,
                                                    os.path.basename(job.src_filepath.rstrip('/')),
                                                    rel_filepath)
                    elif rel_filepath:
                        dst_filepath = os.path.join(job.dst_filepath, rel_filepath)
                    job.elements.append(JobElement(id=element_counter,
                                                   src_filepath=os.path.join(root, file_['name']),
                                                   dst_filepath=dst_filepath,
                                                   max_tries=element.max_tries,
                                                   type=job.type,
                                                   size=int(file_["st_size"])))  # int cast needed?
            job.status = JobStatus.SUBMITTED
        elif job.type == JobType.REMOVE\
            and element.type == JobType.LIST\
                and element.status == JobStatus.DONE:
            element_counter = 0
            top_root = None
            for root, listing in sorted(element.listing.iteritems(),
                                        key=lambda item: len(item[0]), reverse=True):
                entries = sorted((entry for entry in listing if entry['name'] not in ('.', '..')),
                                 key=lambda x: stat.S_ISDIR(int(x['st_mode'])))
                if len(entries) != len(listing):  # when removing a single file this is false.
                    top_root = root
                for entry in entries:
                    element_counter += 1
                    name = entry['name']
                    if stat.S_ISDIR(int(entry['st_mode'])):
                        name += '/'
                    job.elements.append(JobElement(id=element_counter,
                                                   src_filepath=os.path.join(root, name),
                                                   max_tries=element.max_tries,
                                                   type=job.type,
                                                   size=int(entry["st_size"])))
            # Need to remove top level directory
            if top_root is not None:
                element_counter += 1
                job.elements.append(JobElement(id=element_counter,
                                               src_filepath=top_root.rstrip('/') + '/',
                                               max_tries=element.max_tries,
                                               type=job.type,
                                               size=0))  # work out size better
            job.status = JobStatus.SUBMITTED
        job.update()
        return '', 200

    @staticmethod
    @export_ext("jobs", ['POST'])
    @decode_json_data
    def post_job():
        """Add a job."""
        require_attrs('src_siteid')
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        user_id = HRService.check_token()
        request.data['user_id'] = user_id
        request.data['src_credentials'] = current_app.site_client\
                                                     .get_cred(request.data['src_siteid'], user_id)
        if request.data['type'] == JobType.COPY:
            require_attrs('dst_siteid')
            request.data['dst_credentials'] = current_app.site_client\
                                                         .get_cred(request.data['dst_siteid'],
                                                                   user_id)
        try:
            job = Job(**request.data)
            job.add()
        except Exception as err:
            abort(400, description=err.message)
        return jsonify(job)

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
        return jsonify(Job.query.filter_by(user_id=HRService.check_token()).all())

    @staticmethod
    @export_ext("jobs/<int:job_id>", ['GET'])
    def get_job(job_id):
        """Get job."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .first_or_404()
        return jsonify(job)

    @staticmethod
    @export_ext("jobs/<int:job_id>/elements", ['GET'])
    def get_elements(job_id):
        """Get all jobs for a user."""
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        elements = JobElement.query.filter_by(job_id=job_id)\
                                   .join(JobElement.job)\
                                   .filter_by(user_id=HRService.check_token())\
                                   .all()
        return jsonify(elements)

    @staticmethod
    @export_ext("jobs/<int:job_id>/elements/<int:element_id>", ['GET'])
    def get_element(job_id, element_id):
        """Get all jobs for a user."""
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        element = JobElement.query.filter_by(id=element_id, job_id=job_id)\
                                  .join(JobElement.job)\
                                  .filter_by(user_id=HRService.check_token())\
                                  .first_or_404()
        return jsonify(element)

    @staticmethod
    @export_ext('jobs/<int:job_id>/output', ['GET'])
    @export_ext('jobs/<int:job_id>/elements/<int:element_id>/output', ['GET'])
    @export_ext('jobs/<int:job_id>/elements/<int:element_id>/output/<int:attempt>', ['GET'])
    def get_output(job_id, element_id=None, attempt=None):  # pylint: disable=too-many-branches
        """Get job output."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .first_or_404()

        log_filebase = os.path.join(current_app.workqueueservice_workerlogs,
                                    job.log_uid[:2],
                                    job.log_uid)

        if element_id is not None:
            if element_id not in xrange(len(job.elements)):
                abort(404, description="Job element %s.%s not found" % (job_id, element_id))
            element = job.elements[element_id]
            if element.status not in (JobStatus.DONE, JobStatus.FAILED):
                abort(400, description="Job element %s.%s not yet ready" % (job_id, element_id))
            if element.attempts == 0:
                abort(400, description="No attempts have yet been recorded for element %d of "
                                       "job %d. Please try later." % (element_id, job_id))
            if attempt is None:
                attempt = element.attempts
            if attempt not in xrange(1, element.attempts + 1):
                abort(400, description="Invalid attempt '%s', job.element %s.%s has been tried %s "
                                       "time(s)" % (attempt, job_id, element_id, element.attempts))

            log_filename = os.path.join(log_filebase, str(element_id), "attempt%i.log" % attempt)
            if not os.path.exists(log_filename):
                abort(500, description="log directory/file %s not found for job.element %s.%s."
                      % (log_filename, job_id, element_id))
            with open(log_filename, 'rb') as logfile:
                log = logfile.read()

            return_dict = {'jobid': job_id, 'elementid': element_id, 'attempt': attempt,
                           'type': JobType(element.type).name,  # pylint: disable=no-member
                           'status': JobStatus(element.status).name,  # pylint: disable=no-member
                           'log': log}
            if element.type == JobType.LIST:
                return_dict.update(listing=element.listing)
            return jsonify(return_dict)

        return_list = []
        for element in job.elements:
            if element.status not in (JobStatus.DONE, JobStatus.FAILED):
                current_app.log.warn("Job element %s.%s not yet ready", job_id, element.id)
                continue
            if element.attempts == 0:
                current_app.log.warn("No attempts have yet been recorded for element %d of "
                                     "job %d. Please try later.", element.id, job_id)
                continue
            if attempt is None:
                attempt = element.attempts
            if attempt not in xrange(1, element.attempts + 1):
                current_app.log.warn("Invalid attempt '%s', job.element %s.%s has been tried %s "
                                     "time(s)", attempt, job_id, element.id, element.attempts)
                continue

            log_filename = os.path.join(log_filebase, str(element.id), "attempt%i.log" % attempt)
            if not os.path.exists(log_filename):
                abort(500, description="log directory/file %s not found for job.element %s.%s."
                      % (log_filename, job_id, element.id))
            with open(log_filename, 'rb') as logfile:
                log = logfile.read()

            return_dict = {'jobid': job_id, 'elementid': element.id, 'attempt': attempt,
                           'type': JobType(element.type).name,  # pylint: disable=no-member
                           'status': JobStatus(element.status).name,  # pylint: disable=no-member
                           'log': log}
            if element.type == JobType.LIST:
                return_dict.update(listing=element.listing)
            return_list.append(return_dict)
        return jsonify(return_list)

    @staticmethod
    @export_ext("jobs/<int:job_id>/status", ['GET'])
    def get_job_status(job_id):
        """Get job status."""
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        job = Job.query.filter_by(id=job_id, user_id=HRService.check_token())\
                       .first_or_404()
        # pylint: disable=no-member
        return jsonify({'jobid': job.id,
                        'status': JobStatus(job.status).name})

    @staticmethod
    @export_ext("jobs/<int:job_id>/elements/<int:element_id>/status", ['GET'])
    def get_element_status(job_id, element_id):
        """Get element status."""
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        element = JobElement.query.filter_by(id=element_id, job_id=job_id)\
                                  .join(JobElement.job)\
                                  .filter_by(user_id=HRService.check_token())\
                                  .first_or_404()
        # pylint: disable=no-member
        return jsonify({'jobid': element.job_id,
                        'elementid': element.id,
                        'status': JobStatus(element.status).name,
                        'attempts': element.attempts})
