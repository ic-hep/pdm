#!/usr/bin/python env
""" Database helpers.
"""

import json
from collections import Mapping
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import StaticPool


# pylint: disable=too-few-public-methods
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
            options["connect_args"] = {'check_same_thread': False}
            options["poolclass"] = StaticPool
        return super(MemSafeSQLAlchemy, self).apply_driver_hacks(app, info, options)


class DictMixin(object):
    """
    Iterable mixin for DB tables.

    Mixin class that provides an iterable view on a DB
    model allong with dict like getitem accessor methods.

    This allows amongst other things easy dictionary representation
    of models using the following:

    dict(model)
    """

    # No fields excluded by default
    __excluded_fields__ = []

    @property
    def columns(self):
        """list of db model column names."""
        return [name for name, _ in self]

    # This doesn't match the return from a normal mapping which is just keys.
    # This is necessary to allow dictionary conversion as dict constructor
    # doesn't recognise this class as a Mapping despite the manual registration.
    # Only way to change this is to give flask_sqlalchemy.make_declarative_base()
    # a new meta which is a subclass of ABCMeta. Our version doesn't allow this so
    # until we can update we have to do it this way.
    def __iter__(self):
        """Iterator through db columns."""
        return ((column.name, getattr(self, column.name)) for column in self.__table__.columns
                if column.name not in self.__excluded_fields__)

    def __getitem__(self, item):
        """Get specific column value."""
        if item not in self.columns:
            raise KeyError("Invalid attribute name: %s" % item)
        return getattr(self, item)

    def __len__(self):
        """Returns number of db columns."""
        return len(self.columns)
Mapping.register(DictMixin)  # pylint: disable=no-member


# pylint: disable=too-few-public-methods
class JSONMixin(DictMixin):
    """
    JSON serialisation mixin for DB tables.

    A mixin class which provides basic serialisation
    for SQLAlchemy based table classes.
    """

    def encode_for_json(self):
        """Return an object that can be encoded with the default JSON encoder."""
        ret = {}
        for key, value in self:
            if isinstance(value, datetime):
                value = value.isoformat()
            ret[key] = value
        return ret

    def json(self):
        """JSONify the table object."""
        return json.dumps(self.encode_for_json())

    @classmethod
    def from_json(cls, json_str):
        """Load object from JSON string."""
        return cls(**json.loads(json_str))


class JSONTableEncoder(json.JSONEncoder):
    """JSON DB Table Encoder."""

    # pylint: disable=method-hidden
    def default(self, obj):
        """Default encoding method."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, JSONMixin):
            return obj.encode_for_json()
        return super(JSONTableEncoder, self).default(obj)
