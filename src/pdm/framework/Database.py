#!/usr/bin/python env
""" Database helpers.
"""

import json
from datetime import datetime
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import StaticPool

class MemSafeSQAlchemy(SQLAlchemy):
  """ A wrapper around SQLAlchemy which detects if an in-memory database on
      sqlite and disables pooling.
      This is required or each pool will get a different handle,
      so only 1 in threads requests will actually have a created database!
  """
  def apply_driver_hacks(self, app, info, options):
    """ Apply hacks to database driver options as required.
    """
    if info.drivername == "sqlite" and not info.database:
      # This should be fine for testing as long as sqlite version is "high enough"
      options["connect_args"] = {'check_same_thread':False}
      options["poolclass"] = StaticPool
    return super(MemSafeSQAlchemy, self).apply_driver_hacks(app, info, options)

class JSONTableEncoder(json.JSONEncoder):
    """JSON DB Table Encoder."""

    def default(self, obj):
        """Default encoding method."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, JSONMixin):
            cols = [column.name for column in obj.__table__.columns
                                if column.name not in obj.__excluded_fields__]
            return {column: getattr(obj, column) for column in cols}
        return super(JSONTableEncoder, self).default(obj)

#pylint: disable=too-few-public-methods
class JSONMixin(object):
    """
    JSON serialisation mixin for DB tables.

    A mixin class which provides basic serialisation
    for SQLAlchemy based table classes.
    """

    # No fields excluded by default
    __excluded_fields__ = []

    def json(self):
        """JSONify the table object."""
        return json.dumps(self, cls=JSONTableEncoder)

    @classmethod
    def from_json(cls, json_str):
        """Load object from JSON string."""
        return cls(**json.loads(json_str))
