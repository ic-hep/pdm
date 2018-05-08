#!/usr/bin/python env
""" Database helpers.
"""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import StaticPool

class MemSafeSQLAlchemy(SQLAlchemy):
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
        return super(MemSafeSQLAlchemy, self).apply_driver_hacks(app, info, options)

class JSONTableEncoder(json.JSONEncoder):
    """JSON DB Table Encoder."""

    #pylint: disable=method-hidden
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


class DictMixin(object):
    """
    Iterable mixin for DB tables.

    Mixin class that provides an iterable view on a DB
    model allong with dict like getitem accessor methods.

    This allows amongst other things easy dictionary representation
    of models using the following:

    dict(model)
    """

    @property
    def columns(self):
        """list of db model column names."""
        return [column.name for column in self.__table__.columns]

    def __iter__(self):
        """Iterator through db columns."""
        return ((column.name, self[column.name]) for column in self.__table__.columns)

    def __getitem__(self, item):
        """Get specific column value."""
        if item not in self.columns:
            raise KeyError("Invalid attribute name: %s" % item)
        return getattr(self, item)

    def __len__(self):
        """Returns number of db columns."""
        return len(self.columns)
