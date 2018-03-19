from flask import current_app

from pdm.workqueue.sql.models import Job
from pdm.workqueue.sql.enums import JobType


def list(user_id, src_sitepath, priority=5, max_tries=2):
    Job(user_id=user_id,
        priority=priority,
        type=JobType.LIST.name,
        src_sitepath=src_sitepath,
        dst_sitepath=None,
        extra_opts=None,
        max_tries=max_tries).add()
    current_app.semaphore.release()

def copy(user_id, src_sitepath, dst_sitepath, priority=5, max_tries=2, extra_opts=None):
    Job(user_id=user_id,
        priority=priority,
        type=JobType.COPY.name,
        src_sitepath=src_sitepath,
        dst_sitepath=dst_sitepath,
        extra_opts=extra_opts,
        max_tries=max_tries).add()
    current_app.semaphore.release()

def delete(user_id, src_sitepath, priority=5, max_tries=2):
    Job(user_id=user_id,
        priority=priority,
        type=JobType.REMOVE.name,
        src_sitepath=src_sitepath,
        dst_sitepath=None,
        extra_opts=None,
        max_tries=max_tries).add()
    current_app.semaphore.release()
