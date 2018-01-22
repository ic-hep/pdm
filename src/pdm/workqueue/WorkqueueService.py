"""App."""
import os
import uuid

from flask import request

from pdm.framework.FlaskWrapper import export_ext, db_model
from pdm.utils.config import getConfig

from .WorkqueueDB import WorkqueueModels, JobStatus


@export_ext("/workqueue/api/v1.0")
@db_model(WorkqueueModels)
class WorkqueueService(object):
    """Workqueue Service."""

    @staticmethod
    @export_ext('jobs', ["POST"])
    def get_job():
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
    @export_ext('jobs/<int:job_id>', ['PUT'])
    def return_output(job_id):
        """Return a job."""
        db = request.db
        Job = db.tables.Job  # pylint: disable=invalid-name
        Log = db.tables.Log  # pylint: disable=invalid-name

        # Update job status.
        job = Job.query.filter_by(id=job_id).one()
        job.attempts += 1
        job.status = JobStatus.DONE
        if request.data['returncode'] != 0:
            job.status = JobStatus.FAILED
        job.update()

        # Add log record to DB.
        log = Log.query.filter_by(job_id=job_id).one_or_none()
        if log is None:
            log = Log(job_id=job_id, guid=uuid.uuid4())
            log.add()

        # Write log file.
        dir_ = os.path.join(getConfig("app/workqueue").get('workerlogs', '/tmp/workers'),
                            log.guid[:2],
                            log.guid)
        os.makedirs(dir_)
        with open(os.path.join(dir_, 'attempt%i.log' % job.attempts), 'wb') as logfile:
            logfile.write("Job run on host: %s\n" % request.data['host'])
            logfile.write(request.data['log'])
