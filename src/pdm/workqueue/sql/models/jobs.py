"""Workqueue Jobs Table SQL Module."""
from datetime import datetime

from pdm.utils.enum import enum_constraint
from pdm.utils.db import managed_session

from .. import db
from ..enums import JobStatus, JobType


class Job(db.Model):
    """Jobs table."""

    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)  # pylint: disable=invalid-name
    user_id = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.SmallInteger, nullable=False, default=5)
    type = db.Column(*enum_constraint(db, 'type', JobType), nullable=False)  # pylint: disable=invalid-name
    status = db.Column(*enum_constraint(db, 'status', JobStatus), nullable=False,
                       default=JobStatus.NEW.name)
    # These cause problems with our version of SQLAlchemy
    # type = db.Column(db.Enum(JobType), nullable=False) # pylint: disable=invalid-name
    # status = db.Column(db.Enum(JobStatus), nullable=False, default=JobStatus.NEW)
    src_sitepath = db.Column(db.String(250))
    dst_sitepath = db.Column(db.String(250))
    extra_opts = db.Column(db.Text)  # db.String(250))#JSON)
    max_tries = db.Column(db.SmallInteger, nullable=False, default=2)
    retries = db.Column(db.SmallInteger, nullable=False, default=0)
    timestamp = db.Column(db.TIMESTAMP, nullable=False,
                          default=datetime.utcnow, onupdate=datetime.utcnow)
    logs = db.relationship("Log", back_populates="job")
    db.CheckConstraint('retries <= max_tries')

    def add(self):
        with managed_session(db) as session:
            session.add(self)

    def remove(self):
        with managed_session(db) as session:
            session.delete(self)

    def update(self):
        with managed_session(db) as session:
            session.merge(self)

    def __str__(self):
        return "Job(id=%i)" % self.id
    def __repr__(self):
        return "Job(id=%i)" % self.id

    @staticmethod
    def get(ids=None, status=None, prioritised=True):
        """Retrieve jobs from database."""
        query = Job.query
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
        with managed_session(db) as session:
            Job.query.filter(Job.id.in_(set(ids))).delete()
