"""Workqueue Logs Table SQL Module."""
from .. import db


class Log(db.Model):
    """Logs table."""

    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)  # pylint: disable=invalid-name
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    guid = db.Column(db.String(36), nullable=False)
    job = db.relationship("Job", back_populates="logs")
