"""Workqueue SQL DB Module."""
import uuid
import json
from datetime import datetime

from enum import unique, IntEnum
from flask import current_app
from sqlalchemy import (Column, Integer, SmallInteger,
                        String, TEXT, TIMESTAMP, CheckConstraint)

from pdm.framework.Database import JSONMixin, JSONTableEncoder
from pdm.utils.db import managed_session


class EnumBase(IntEnum):
    """Base enum."""

    def __str__(self):
        """Return the value of the enum."""
        return str(self.value)

    @classmethod
    def values(cls):
        """Return tuple of all possible enum values."""
        return tuple(enu.value for enu in cls)


@unique
class JobStatus(EnumBase):
    """Job status enum."""

    NEW = 0
    SUBMITTED = 1
    DONE = 2
    FAILED = 3


@unique
class JobType(EnumBase):
    """Job type enum."""

    LIST = 0
    COPY = 1
    REMOVE = 2


@unique
class JobProtocol(EnumBase):
    """Job protocol enum."""

    GRIDFTP = 0
    SSH = 1


class WorkqueueJobEncoder(JSONTableEncoder):
    """
    Workqueue Job DB Table Encoder.

    Will turn enums into human readable form.
    """

    #pylint: disable=method-hidden
    def default(self, obj):
        """Default encoding method."""
        return_obj = super(WorkqueueJobEncoder, self).default(obj)
        if isinstance(obj, JSONMixin):
            return_obj['type'] = JobType(obj.type).name
            return_obj['protocol'] = JobProtocol(obj.protocol).name
            return_obj['status'] = JobStatus(obj.status).name
        return return_obj


PROTOCOLMAP = {JobProtocol.GRIDFTP: 'gsiftp',
               JobProtocol.SSH: 'ssh'}

COMMANDMAP = {JobType.LIST: {JobProtocol.GRIDFTP: 'gfal-ls',
                             JobProtocol.SSH: 'sftp'},
              JobType.REMOVE: {JobProtocol.GRIDFTP: 'gfal-rm',
                               JobProtocol.SSH: 'sftp'},
              JobType.COPY: {JobProtocol.GRIDFTP: 'globus-url-copy',
                             JobProtocol.SSH: 'scp'}}


class WorkqueueModels(object):  # pylint: disable=too-few-public-methods
    """DB Models."""

    def __init__(self, db_base):
        """Initialisation."""
        class Job(db_base, JSONMixin):
            """Jobs table."""

            __tablename__ = 'jobs'
            id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
            user_id = Column(Integer, nullable=False)
            src_siteid = Column(Integer, nullable=False)
            dst_siteid = Column(Integer)
            src_filepath = Column(TEXT, nullable=False)
            dst_filepath = Column(TEXT)
            extra_opts = Column(TEXT)
            credentials = Column(TEXT)
            log_uid = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
            max_tries = Column(SmallInteger, nullable=False, default=2)
            attempts = Column(SmallInteger, nullable=False, default=0)
            timestamp = Column(TIMESTAMP, nullable=False,
                               default=datetime.utcnow, onupdate=datetime.utcnow)
            priority = Column(SmallInteger,
                              CheckConstraint('priority in {0}'.format(tuple(xrange(10)))),
                              nullable=False,
                              default=5)
            type = Column(SmallInteger,  # pylint: disable=invalid-name
                          CheckConstraint('type in {0}'.format(JobType.values())),
                          nullable=False)
            protocol = Column(SmallInteger,
                              CheckConstraint('protocol in {0}'.format(JobProtocol.values())),
                              nullable=False,
                              default=JobProtocol.GRIDFTP)
            status = Column(SmallInteger,
                            CheckConstraint('status in {0}'.format(JobStatus.values())),
                            nullable=False,
                            default=JobStatus.NEW)
            CheckConstraint('retries <= max_tries')

            def add(self):
                """Add job to session."""
                with managed_session(current_app,
                                     message="Error adding job",
                                     http_error_code=500) as session:
                    session.add(self)

            def remove(self):
                """Remove job from session."""
                with managed_session(current_app,
                                     message="Error removing job",
                                     http_error_code=500) as session:
                    session.delete(self)

            def update(self):
                """Update session with current job."""
                with managed_session(current_app,
                                     message="Error updating job",
                                     http_error_code=500) as session:
                    session.merge(self)

            def enum_json(self):
                """Dump as JSON document with enums expanded."""
                return json.dumps(self, cls=WorkqueueJobEncoder)

            @staticmethod
            def get(ids=None, status=None, prioritised=True):
                """Retrieve jobs from database."""
                query = current_app.db.session.query
                if isinstance(ids, int):
                    ids = (ids,)
                if ids is not None:
                    query = query.filter(Job.id.in_(set(ids)))
                if status is not None:
                    query = query.filter_by(status=status)
                if prioritised:
                    query = query.order_by(Job.priority)
                return query.all()

            @staticmethod
            def remove_all(ids):
                """Remove jobs from database."""
                if isinstance(ids, int):
                    ids = (ids,)
                with managed_session(current_app,
                                     message="Error removing all jobs.",
                                     http_error_code=500) as session:
                    session.query.filter(Job.id.in_(set(ids))).delete()
