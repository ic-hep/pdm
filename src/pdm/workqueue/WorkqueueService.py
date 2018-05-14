"""Workqueue Service."""
import os
import json
import re
import time
import stat
from enum import Enum
from functools import partial
from datetime import date
from itertools import groupby
from operator import attrgetter

from flask import request, abort, current_app
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import (export_ext, db_model, startup,
                                      decode_json_data, startup_test)
from pdm.userservicedesk.HRService import HRService
from pdm.site.SiteClient import SiteClient
from pdm.framework.Database import JSONTableEncoder
from .WorkqueueDB import WorkqueueModels, JobStatus, JobType


#def blah(listing, job):
#    JobElement = current_app.db.tables.JobElement
#    files = []
#
#    for root, items in listing.iteritems():
#        for i, item in enumerate(items):
#            if not stat.S_ISREG(int(item['st_mode'])):
#                continue
#            if job.type == JobType.COPY and len(listing) == 1 and\
#                    len(items) == 1 and os.path.splitext(job.dst_filepath)[1]:
#                dst_filepath = job.dst_filepath
#            else:
#                dst_filepath = os.path.join(job.dst_filepath,
#                                            os.path.relpath(root, job.src_filepath),
#                                            item['name'])
#            files.append(JobElement(id=i + 1,
#                                    src_filepath=os.path.join(root, item['name']),
#                                    dst_filepath=dst_filepath,
#                                    max_tries=job.max_tries,
#                                    type=job.type))
#
##        files.extend(JobElement(id=i + 1,
##                                src_filepath=os.path.join(root, item['name']),
##                                dst_filepath=os.path.join(job.dst_filepath,  # need to be careful if they pass dir instead of file....check this
##                                                          os.path.relpath(root, job.src_filepath),
##                                                          item['name']),
##                                max_tries=job.max_tries,
##                                type=job.type)
##                     for i, item in enumerate(items)
##                     if stat.S_ISREG(int(item['st_mode'])))
#    return files


@export_ext("/workqueue/api/v1.0")
@db_model(WorkqueueModels)
class WorkqueueService(object):
    """Workqueue Service."""

#    @staticmethod
#    @startup_test
#    def preload_turtles():
#        """ Creates an example database if DB is empty.
#        """
#        log = current_app.log
#        db = current_app.db
#        Job = db.tables.Job
#        JobElement = db.tables.JobElement
#
#        job = Job(user_id=17, type=JobType.COPY, src_siteid=123, src_filepath='/blah', dst_siteid=1234, dst_filepath="/dude")
#        job.elements.append(JobElement(id=1, type=JobType.LIST, src_filepath='/dude1'))
#        job.elements.append(JobElement(id=2, type=JobType.LIST, src_filepath='/dude2'))
#        job.elements.append(JobElement(id=3, type=JobType.LIST, src_filepath='/dude3'))
#        job.add()
#        job = Job(user_id=18, type=JobType.REMOVE, src_siteid=123, src_filepath='/blah')
#        job.elements.append(JobElement(id=1, type=JobType.LIST, src_filepath='/dude4'))
#        job.elements.append(JobElement(id=2, type=JobType.LIST, src_filepath='/dude5'))
#        job.elements.append(JobElement(id=3, type=JobType.LIST, src_filepath='/dude6'))
#        job.add()
#
#        print json.dumps(Job.query.all(), cls=WorkqueueJobEncoder).replace(',', ',\n')
#        print json.dumps(JobElement.query.all(), cls=WorkqueueJobEncoder).replace(',', ',\n')


#        print "HERE", job.dst_siteid
#        db.session.commit()
#        print "THERE", job.dst_siteid
#        from pprint import pprint
#        j = Job.query.all()[0]
#        pprint(j)
#        print "CHECK", j.dst_siteid
#        pprint(j.elements[0].__dict__)

    @staticmethod
    @startup
    def configure_workqueueservice(config):
        """Setup the WorkqueueService."""
        current_app.workqueueservice_workerlogs = config.pop('workerlogs', '/tmp/workers')

    @staticmethod
    @export_ext('worker/jobs', ["POST"])
    @decode_json_data
    def get_next_job():
        """Get the next job."""
        require_attrs('types')
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        elements = Algorithm[request.data.get('algorithm', 'BY_NUMBER')](**request.data.get('alg_args', {}))
#        elements = JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
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
#            job_dict = dict(job.noenum_for_json(), elements=[])
#            job_dict = job.noenum_for_json()
#            job_dict['elements'] = []
            elements = []
            for element in list(elements_group):  # iter(elements_group)
                element.status = JobStatus.SUBMITTED
                element.update()  # should be a bulk update
                element_dict = element.noenum_for_json()
                element_dict['token'] = request.token_svc.issue("%d.%d" % (job.id, element.id))
                elements.append(element_dict)
#                job_dict['elements'].append(element_dict)
#                job_dict['elements'].append(dict(element.noenum_for_json(), token=request.token_svc.issue("%d.%d" % (job.id, element.id))))
            job.status = max(ele.status for ele in job.elements)
            job_dict = job.noenum_for_json()
            job_dict['elements'] = elements
            work.append(job_dict)
#            job.status = JobStatus.SUBMITTED
#            job.status = max(ele.status for ele in job.elements)
            job.update()
        return jsonify(work)

    @staticmethod
    @export_ext('worker/jobs/<int:job_id>/elements/<int:element_id>', ['PUT'])
    @decode_json_data
    def return_output(job_id, element_id):
        """Return a job."""
        if not request.token_ok:
            abort(403, description="Invalid token")
        if request.token != '%d.%d' % (job_id, element_id):
            abort(403, description="Token not valid for element %d of job %d" % (element_id, job_id))
        require_attrs('returncode', 'host', 'log')

        # Update job status.
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        element = JobElement.query.get_or_404((element_id, job_id))
        if element.type == JobType.LIST:
            require_attrs('listing')
        element.attempts += 1
        element.status = JobStatus.DONE if request.data['returncode'] == 0 else JobStatus.FAILED
        element.listing = request.data['listing']
        element.update()

#        Job = request.db.tables.Job
#        try:
#            job = Job.query.filter_by(id=job_id).one()
#        except NoResultFound:
#            abort(500, description="Couldn't find job with id %d even after updating element" % job_id)
#        except MultipleResultsFound:
#            abort(500, description="Multiple jobs with id %d found!" % job_id)
        job = element.job
        job.status = max(ele.status for ele in job.elements)
        if job.type != JobType.LIST and element.type == JobType.LIST and element.status == JobStatus.DONE:
###############
            for root, items in element.listing.iteritems():
                for i, item in enumerate(items):
                    if not stat.S_ISREG(int(item['st_mode'])):  # int cast necessary?
                        continue
                    if job.type == JobType.COPY and len(element.listing) == 1 and \
                            len(items) == 1 and os.path.splitext(job.dst_filepath)[1]:
                        dst_filepath = job.dst_filepath
                    else:
                        dst_filepath = os.path.join(job.dst_filepath,
                                                    os.path.relpath(root, job.src_filepath),
                                                    item['name'])
                    job.elements.append(JobElement(id=i + 1,
                                                   src_filepath=os.path.join(root, item['name']),
                                                   dst_filepath=dst_filepath,
                                                   max_tries=job.max_tries,
                                                   type=job.type,
                                                   size=int(item["st_size"])))  # int cast necessary?

##########
#            for i, item in enumerate(request.data['listing']):
#                if item['is_directory']:
#                    continue
#                job.elements.append(JobElement(id=i + 1,
#                                               src_filepath=os.path.join(os.path.dirname(element.src_filepath), item['name']),
#                                               dst_filepath=os.path.dirname(element.dst_filepath),
#                                               extra_opts=element.extra_opts,
#                                               max_tries=element.max_tries,
#                                               type=job.type))
            job.status = JobStatus.SUBMITTED
        job.update()

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
        return '', 200

    @staticmethod
    @export_ext("jobs", ['POST'])
    @decode_json_data
    def post_job():
        """Add a job."""
        site_client = SiteClient()
        Job = request.db.tables.Job  # pylint: disable=invalid-name
        user_id = HRService.check_token()
        request.data['user_id'] = user_id
        request.data['src_credentials'] = site_client.get_cred(request.data['src_siteid'], user_id)
        request.data['dst_credentials'] = site_client.get_cred(request.data['dst_siteid'], user_id)
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
    def get_output(job_id, element_id=0, attempt=None):
        """Get job output."""
        JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
        element = JobElement.query.filter_by(job_id=job_id, id=element_id)\
                                  .filter(JobElement.status.in_((JobStatus.DONE, JobStatus.FAILED)))\
                                  .join(JobElement.job)\
                                  .filter_by(user_id=HRService.check_token())\
                                  .first_or_404()

        if attempt is None:
            if element.attempts == 0:
                abort(404, description="No attempts have yet been recorded for element %d of job %d. Please try later."
                                       % (element_id, job_id))
            attempt = element.attempts

        if attempt not in xrange(1, element.attempts + 1):
            abort(400, description="Invalid attempt '%s', job has been tried %s time(s)"
                  % (attempt, element.attempts))

        logfilename = os.path.join(current_app.workqueueservice_workerlogs,
                                   element.job.log_uid[:2],
                                   element.job.log_uid,
                                   str(element_id),
                                   "attempt%i.log" % attempt)
        if not os.path.exists(logfilename):
            abort(500, description="log directory/file not found.")
        with open(logfilename, 'rb') as logfile:
            log = logfile.read()

        return_dict = {'jobid': element.job_id, 'elementid': element.id, 'type': JobType(element.type).name, 'log': log}
        if element.type == JobType.LIST:
            return_dict.update(listing=element.listing)
        return jsonify(return_dict)

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


def require_attrs(*attrs):
    """Require the given attrs."""
    required = set(attrs).difference(request.data)
    if required:
        abort(400, description="Missing data attributes: %s" % list(required))
    return attrs


def by_number(n=10):
    Job = request.db.tables.Job  # pylint: disable=invalid-name
    JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
    return JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
                                   JobElement.attempts < JobElement.max_tries)\
                           .join(JobElement.job)\
                           .filter(Job.type.in_(request.data['types']))\
                           .order_by(Job.priority)\
                           .order_by(Job.id)\
                           .order_by(Job.status)\
                           .limit(n)\
                           .all()


M = 1000000


def by_size(size=100*M):
    from sqlalchemy import func
    Job = request.db.tables.Job  # pylint: disable=invalid-name
    JobElement = request.db.tables.JobElement  # pylint: disable=invalid-name
    return JobElement.query.filter(JobElement.status.in_((JobStatus.NEW, JobStatus.FAILED)),
                                   JobElement.attempts < JobElement.max_tries)\
                           .join(JobElement.job)\
                           .filter(Job.type.in_(request.data['types']))\
                           .order_by(Job.priority)\
                           .order_by(Job.id)\
                           .order_by(Job.status)\
                           .order_by(JobElement.size.desc())\
                           .group_by(JobElement.id, JobElement.job_id)\
                           .having(func.sum(JobElement.size) < size)\
                           .all()
                           #.limit(20)
                           #.count()


class Algorithm(Enum):
    # could use a wrapper here but cant just use function as it will be
    # considered a method of Algorithm rather than a member of the enum
    BY_NUMBER = partial(by_number)
    BY_SIZE = partial(by_size)

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)
