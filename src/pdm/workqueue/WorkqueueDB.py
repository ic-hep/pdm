"""Workqueue SQL DB Module."""
import uuid
import json
import re
from datetime import datetime

from enum import unique, IntEnum
from flask import current_app
from sqlalchemy.orm import relationship
from sqlalchemy import (Column, Integer, SmallInteger, ForeignKey,
                        String, TEXT, TIMESTAMP, CheckConstraint, PickleType, PrimaryKeyConstraint)

from pdm.framework.Database import JSONMixin, JSONTableEncoder, DictMixin
from pdm.utils.db import managed_session


def subdict(dct, keys):
    """Create a sub dictionary."""
    return {k: dct[k] for k in keys if k in dct}


class EnumBase(IntEnum):
    """Base enum."""

    def __str__(self):
        """Return the value of the enum."""
        return str(self.value)  # pylint: disable=no-member

    @classmethod
    def values(cls):
        """Return tuple of all possible enum values."""
        return tuple(enu.value for enu in cls)

    @classmethod
    def parse(cls, obj):
        """Convert arg to enum."""
        if isinstance(obj, int):
            return cls(obj)
        if isinstance(obj, basestring):
            if obj.isdigit():
                return cls(int(obj))
            return cls[obj.upper()]
        if not isinstance(obj, cls):
            raise ValueError("Failed to parse '%s' to enum type '%s'" % (obj, cls.__name__))
        return obj

@unique
class JobStatus(EnumBase):
    """Job status enum."""

    NEW = 0
    DONE = 1
    FAILED = 2
    SUBMITTED = 3


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
    DUMMY = 2


PROTOCOLMAP = {JobProtocol.GRIDFTP: 'gsiftp',
               JobProtocol.SSH: 'ssh',
               JobProtocol.DUMMY: 'dummy'}

COMMANDMAP = {JobType.LIST: {JobProtocol.GRIDFTP: 'pdm-gfal2-ls.py',
                             JobProtocol.SSH: 'sftp',
                             JobProtocol.DUMMY: 'dummy.sh list'},
              JobType.REMOVE: {JobProtocol.GRIDFTP: 'pdm-gfal2-rm.py',
                               JobProtocol.SSH: 'sftp',
                               JobProtocol.DUMMY: 'dummy.sh remove'},
              JobType.COPY: {JobProtocol.GRIDFTP: 'pdm-gfal2-copy.py',
                             JobProtocol.SSH: 'scp',
                             JobProtocol.DUMMY: 'dummy.sh copy'}}
SHELLPATH_REGEX = re.compile(r'^[/~][a-zA-Z0-9/_.*~-]*$')

def shellpath_sanitise(path):
    """Sanitise the path for use in bash shell."""
    if SHELLPATH_REGEX.match(path) is None:
        raise ValueError("Possible injection content in filepath '%s'" % path)
    return path

class AlexColumn(Column):
    def __init__(self, *args, **kwargs):
        self._required = kwargs.pop('required', False)
        self._allowed = kwargs.pop('allowed', False)
        super(AlexColumn, self).__init__(*args, **kwargs)

    @property
    def required(self):
        return self._required
    @property
    def allowed(self):
        return self._allowed



class WorkqueueModels(object):  # pylint: disable=too-few-public-methods
    """DB Models."""

    def __init__(self, db_base):
        """Initialisation."""
        class Job(db_base, JSONMixin):
            """Jobs table."""

            __tablename__ = 'jobs'
            id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
            user_id = AlexColumn(Integer, nullable=False, allowed=True, required=True)
            log_uid = AlexColumn(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
            src_siteid = AlexColumn(Integer, nullable=False, allowed=True, required=True)
            dst_siteid = AlexColumn(Integer, allowed=True)
            src_filepath = AlexColumn(TEXT, nullable=False, required=True, allowed=True)
            dst_filepath = AlexColumn(TEXT, allowed=True)
            extra_opts = AlexColumn(TEXT, allowed=True)
            src_credentials = AlexColumn(TEXT, allowed=True)
            dst_credentials = AlexColumn(TEXT, allowed=True)
            timestamp = Column(TIMESTAMP, nullable=False,
                               default=datetime.utcnow, onupdate=datetime.utcnow)
            priority = AlexColumn(SmallInteger,
                              CheckConstraint('priority in {0}'.format(tuple(xrange(10)))),
                              nullable=False, allowed=True,
                              default=5)
            type = AlexColumn(SmallInteger,  # pylint: disable=invalid-name
                          CheckConstraint('type in {0}'.format(JobType.values())),
                          nullable=False, allowed=True, required=True)
            protocol = AlexColumn(SmallInteger,
                              CheckConstraint('protocol in {0}'.format(JobProtocol.values())),
                              nullable=False, allowed=True,
                              default=JobProtocol.GRIDFTP)
            status = Column(SmallInteger,
                            CheckConstraint('status in {0}'.format(JobStatus.values())),
                            nullable=False,
                            default=JobStatus.NEW)
            elements = relationship("JobElement", back_populates="job",
                                        cascade="all, delete-orphan")

            @classmethod
            def required_args(cls):
                return set(column.name for column in cls.__table__.columns.values() if getattr(column, 'required', False))
            @classmethod
            def allowed_args(cls):
                return set(column.name for column in cls.__table__.columns.values() if getattr(column, 'allowed', False))

            def noenum_for_json(self):
                return super(Job, self).encode_for_json()

            def encode_for_json(self):
                return dict(super(Job, self).encode_for_json(),
                            type=JobType(self.type).name,
                            protocol=JobProtocol(self.protocol).name,
                            status=JobStatus(self.status).name)

            def __init__(self, **kwargs):
                """Initialisation."""
                required_args = self.required_args().difference(kwargs)
                if required_args:
                    raise ValueError("Missing %s" % list(required_args))
                kwargs['src_filepath'] = shellpath_sanitise(kwargs['src_filepath'])
                kwargs['type'] = JobType.parse(kwargs['type'])
                if 'protocol' in kwargs:
                    kwargs['protocol'] = JobProtocol.parse(kwargs['protocol'])
                if kwargs['type'] == JobType.COPY:
                    required_args = {'dst_siteid', 'dst_filepath'}.difference(kwargs)
                    if required_args:
                        raise ValueError("Missing %s" % list(required_args))
                    kwargs['dst_filepath'] = shellpath_sanitise(kwargs['dst_filepath'])

                super(Job, self).__init__(**subdict(kwargs, self.allowed_args()))
                element = JobElement(id=0, **kwargs)
                element.type = JobType.LIST  # reset it afterwards so that the arg requirements for a copy job are checked by jobelement
                self.elements = [element]

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

        class JobElement(db_base, JSONMixin):
            """Jobs table."""

            __tablename__ = 'jobelements'
            __table_args__ = (
                   CheckConstraint('attempts <= max_tries'),
            )
            id = AlexColumn(Integer, primary_key=True, required=True, allowed=True)  # pylint: disable=invalid-name
            job_id = Column(Integer, ForeignKey('jobs.id'), primary_key=True)
            job = relationship("Job", back_populates="elements")
            src_filepath = AlexColumn(TEXT, nullable=False, required=True, allowed=True)
            dst_filepath = AlexColumn(TEXT, allowed=True)
            listing = Column(PickleType, nullable=True)
            size = AlexColumn(Integer, nullable=False, default=0, allowed=True)
            max_tries = AlexColumn(SmallInteger, nullable=False, default=2, allowed=True)
            attempts = Column(SmallInteger, nullable=False, default=0)
            timestamp = Column(TIMESTAMP, nullable=False,
                               default=datetime.utcnow, onupdate=datetime.utcnow)
            type = AlexColumn(SmallInteger,  # pylint: disable=invalid-name
                          CheckConstraint('type in {0}'.format(JobType.values())),
                          nullable=False, allowed=True, required=True)
            status = Column(SmallInteger,
                            CheckConstraint('status in {0}'.format(JobStatus.values())),
                            nullable=False,
                            default=JobStatus.NEW)
#            CheckConstraint('attempts <= max_tries')
#            PrimaryKeyConstraint('job_id', 'id')

            @classmethod
            def required_args(cls):
                return set(column.name for column in cls.__table__.columns.values() if getattr(column, 'required', False))
            @classmethod
            def allowed_args(cls):
                return set(column.name for column in cls.__table__.columns.values() if getattr(column, 'allowed', False))

            def noenum_for_json(self):
                return super(JobElement, self).encode_for_json()

            def encode_for_json(self):
                return dict(super(JobElement, self).encode_for_json(),
                            type=JobType(self.type).name,
                            status=JobStatus(self.status).name)

            def __init__(self, **kwargs):
                """Initialisation."""
                required_args = self.required_args().difference(kwargs)
                if required_args:
                    raise ValueError("Missing %s" % list(required_args))
                kwargs['src_filepath'] = shellpath_sanitise(kwargs['src_filepath'])
                kwargs['type'] = JobType.parse(kwargs['type'])
                if kwargs['type'] == JobType.COPY:
                    required_args = {'dst_filepath'}.difference(kwargs)
                    if required_args:
                        raise ValueError("Missing %s" % list(required_args))
                    kwargs['dst_filepath'] = shellpath_sanitise(kwargs['dst_filepath'])
                super(JobElement, self).__init__(**subdict(kwargs, self.allowed_args()))

            def update(self):
                """Update session with current element."""
                with managed_session(current_app,
                                     message="Error updating job element",
                                     http_error_code=500) as session:
                    session.merge(self)
