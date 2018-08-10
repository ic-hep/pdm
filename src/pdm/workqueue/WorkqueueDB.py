"""Workqueue SQL DB Module."""
import uuid
import re
from datetime import datetime

from enum import unique, IntEnum
from flask import current_app, abort
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import (Column, Integer, SmallInteger, ForeignKey,
                        String, TEXT, TIMESTAMP, CheckConstraint, PickleType)

from pdm.framework.Database import JSONMixin
from pdm.utils.db import managed_session


def subdict(dct, keys, **kwargs):
    """Create a sub dictionary."""
    return_dict = {k: dct[k] for k in keys if k in dct}
    return_dict.update(kwargs)
    return return_dict


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
    RENAME = 3
    MKDIR = 4


@unique
class JobProtocol(EnumBase):
    """Job protocol enum."""

    GRIDFTP = 0
    SSH = 1
    DUMMY = 2


PROTOCOLMAP = {JobProtocol.GRIDFTP: 'gsiftp',
               JobProtocol.SSH: 'ssh',
               JobProtocol.DUMMY: 'dummy'}

COMMANDMAP = {JobType.LIST: {JobProtocol.GRIDFTP: 'pdm_gfal2_ls.py',
                             JobProtocol.SSH: 'sftp',
                             JobProtocol.DUMMY: 'dummy.sh list'},
              JobType.REMOVE: {JobProtocol.GRIDFTP: 'pdm_gfal2_rm.py',
                               JobProtocol.SSH: 'sftp',
                               JobProtocol.DUMMY: 'dummy.sh remove'},
              JobType.COPY: {JobProtocol.GRIDFTP: 'pdm_gfal2_copy.py',
                             JobProtocol.SSH: 'scp',
                             JobProtocol.DUMMY: 'dummy.sh copy'},
              JobType.RENAME: {JobProtocol.GRIDFTP: 'pdm_gfal2_rename.py',
                               JobProtocol.SSH: 'echo',
                               JobProtocol.DUMMY: 'dummy.sh rename'},
              JobType.MKDIR: {JobProtocol.GRIDFTP: 'pdm_gfal2_mkdir.py',
                              JobProtocol.SSH: 'echo',
                              JobProtocol.DUMMY: 'dummy.sh mkdir'}}
SHELLPATH_REGEX = re.compile(r'^[/~][a-zA-Z0-9/_.*~-]*$')


def shellpath_sanitise(path):
    """Sanitise the path for use in bash shell."""
    if SHELLPATH_REGEX.match(path) is None:
        raise ValueError("Possible injection content in filepath '%s'" % path)
    return path


class SmartColumn(Column):  # pylint: disable=too-many-ancestors, abstract-method
    """SQLAlchemy model column that knows if it is a requirement or allowed attribute."""

    def __init__(self, *args, **kwargs):
        """Initialisation."""
        self._required = kwargs.pop('required', False)
        self._allowed = kwargs.pop('allowed', False)
        super(SmartColumn, self).__init__(*args, **kwargs)

    @property
    def required(self):
        """Return if column is a required attribute."""
        return self._required

    @property
    def allowed(self):
        """Return if column is an allowed attribute."""
        return self._required or self._allowed


class SmartColumnAwareMixin(object):
    """Mixin class to facilitate grouping of required or allowed columns."""

    @classmethod
    def required_args(cls):
        """Get required args."""
        # Note use getattr(column, 'required') instead of column.required
        # to allow use with regular columns
        return {column.name for column in cls.__table__.columns.values()
                if getattr(column, 'required', False)}

    @classmethod
    def allowed_args(cls):
        """Get allowed args."""
        return {column.name for column in cls.__table__.columns.values()
                if getattr(column, 'allowed', False)}


class WorkqueueModels(object):  # pylint: disable=too-few-public-methods
    """DB Models."""

    def __init__(self, db_base):
        """Initialisation."""
        class Job(db_base, JSONMixin, SmartColumnAwareMixin):
            """Jobs table."""

            __tablename__ = 'jobs'
            id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
            user_id = SmartColumn(Integer, nullable=False, allowed=True, required=True)
            log_uid = SmartColumn(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
            src_siteid = SmartColumn(Integer, nullable=False, allowed=True, required=True)
            dst_siteid = SmartColumn(Integer, allowed=True)
            src_filepath = SmartColumn(TEXT, nullable=False, required=True, allowed=True)
            dst_filepath = SmartColumn(TEXT, allowed=True)
            extra_opts = SmartColumn(PickleType, allowed=True)
            src_credentials = SmartColumn(TEXT, allowed=True)
            dst_credentials = SmartColumn(TEXT, allowed=True)
            timestamp = Column(TIMESTAMP, nullable=False,
                               default=datetime.utcnow, onupdate=datetime.utcnow)
            priority = SmartColumn(SmallInteger,
                                   CheckConstraint('priority in {0}'.format(tuple(xrange(10)))),
                                   nullable=False, allowed=True, default=5)
            type = SmartColumn(SmallInteger,  # pylint: disable=invalid-name
                               CheckConstraint('type in {0}'.format(JobType.values())),
                               nullable=False, allowed=True, required=True)
            protocol = SmartColumn(SmallInteger,
                                   CheckConstraint('protocol in {0}'.format(JobProtocol.values())),
                                   nullable=False, allowed=True, default=JobProtocol.GRIDFTP)
            status = Column(SmallInteger,
                            CheckConstraint('status in {0}'.format(JobStatus.values())),
                            nullable=False, default=JobStatus.NEW)
            elements = relationship("JobElement", back_populates="job",
                                    cascade="all, delete-orphan")

            def asdict(self):
                """
                Convert to a dict.

                This makes use of the JSONMixin.encode_for_json() rather than just simply returning
                dict(self) in order to get datetime.isoformat() conversions. Crucially it keeps the
                enums in their integer form.

                Used primarily for communication between Workqueue and Worker.
                """
                return super(Job, self).encode_for_json()

            def encode_for_json(self):
                """
                Convert to JSON.

                Conversion for sending to clients. This includes the expansion of enums into
                human-readable names and removing of credentials.
                """
                # pylint: disable=no-member
                return_dict = dict(super(Job, self).encode_for_json(),
                                   type=JobType(self.type).name,
                                   protocol=JobProtocol(self.protocol).name,
                                   status=JobStatus(self.status).name)
                # Don't return credentials to clients.
                return_dict.pop('src_credentials', None)
                return_dict.pop('dst_credentials', None)
                return return_dict

            def __init__(self, **kwargs):
                """Initialisation."""
                required_args = self.required_args().difference(kwargs)
                if required_args:
                    raise ValueError("Missing %s" % list(required_args))
                kwargs['src_filepath'] = shellpath_sanitise(kwargs['src_filepath'])
                kwargs['type'] = JobType.parse(kwargs['type'])
                if 'protocol' in kwargs:
                    kwargs['protocol'] = JobProtocol.parse(kwargs['protocol'])
                if kwargs['type'] in (JobType.COPY, JobType.RENAME):
                    required_args = {'dst_siteid', 'dst_filepath'}.difference(kwargs)
                    if required_args:
                        raise ValueError("Missing %s" % list(required_args))
                    kwargs['dst_filepath'] = shellpath_sanitise(kwargs['dst_filepath'])

                super(Job, self).__init__(**subdict(kwargs, self.allowed_args()))
                if kwargs['type'] == JobType.MKDIR:
                    self.elements = [JobElement(**dict(kwargs, id=0, size=0))]
                else:
                    self.elements = [JobElement(**subdict(kwargs,
                                                          ('src_filepath', 'max_tries'),
                                                          id=0,
                                                          type=JobType.LIST))]

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

        class JobElement(db_base, JSONMixin, SmartColumnAwareMixin):
            """Jobs table."""

            __tablename__ = 'jobelements'
            __table_args__ = (
                CheckConstraint('attempts <= max_tries'),
            )
            # pylint: disable=invalid-name
            id = SmartColumn(Integer, primary_key=True, required=True, allowed=True)
            job_id = Column(Integer, ForeignKey('jobs.id'), primary_key=True)
            job = relationship("Job", back_populates="elements")
            src_filepath = SmartColumn(TEXT, nullable=False, required=True, allowed=True)
            dst_filepath = SmartColumn(TEXT, allowed=True)
            listing = Column(PickleType, nullable=True)
            monitoring_info = Column(PickleType, nullable=True)
            size = SmartColumn(Integer, nullable=False, default=0, allowed=True)
            max_tries = SmartColumn(SmallInteger, nullable=False, default=2, allowed=True)
            attempts = Column(SmallInteger, nullable=False, default=0)
            timestamp = Column(TIMESTAMP, nullable=False,
                               default=datetime.utcnow, onupdate=datetime.utcnow)
            type = SmartColumn(SmallInteger,  # pylint: disable=invalid-name
                               CheckConstraint('type in {0}'.format(JobType.values())),
                               nullable=False, allowed=True, required=True)
            status = Column(SmallInteger,
                            CheckConstraint('status in {0}'.format(JobStatus.values())),
                            nullable=False, default=JobStatus.NEW)

            def asdict(self):
                """
                Convert to a dict.

                This makes use of the JSONMixin.encode_for_json() rather than just simply returning
                dict(self) in order to get datetime.isoformat() conversions. Crucially it keeps the
                enums in their integer form.
                """
                return super(JobElement, self).encode_for_json()

            def encode_for_json(self):
                """
                Convert to JSON.

                Conversion for sending to clients. This includes the expansion of enums into
                human-readable names.
                """
                return dict(super(JobElement, self).encode_for_json(),
                            type=JobType(self.type).name,  # pylint: disable=no-member
                            status=JobStatus(self.status).name)  # pylint: disable=no-member

            def __init__(self, **kwargs):
                """Initialisation."""
                required_args = self.required_args().difference(kwargs)
                if required_args:
                    raise ValueError("Missing %s" % list(required_args))
                kwargs['src_filepath'] = shellpath_sanitise(kwargs['src_filepath'])
                kwargs['type'] = JobType.parse(kwargs['type'])
                if kwargs['type'] in (JobType.COPY, JobType.RENAME):
                    required_args = {'dst_filepath'}.difference(kwargs)
                    if required_args:
                        raise ValueError("Missing %s" % list(required_args))
                    kwargs['dst_filepath'] = shellpath_sanitise(kwargs['dst_filepath'])
                super(JobElement, self).__init__(**subdict(kwargs, self.allowed_args()))

            def update(self):
                """Update session with current element."""
                message = "Error updating job element"
                try:
                    with managed_session(current_app, message=message) as session:
                        session.merge(self)
                except IntegrityError as err:
                    if 'constraint failed' in str(err):
                        abort(400, description="Max tries reached, no more attempts allowed")
                    abort(500, description=message)
                except Exception:
                    abort(500, description=message)
