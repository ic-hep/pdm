#!/usr/bin/python env
""" Database helpers.
"""

import json
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

#pylint: disable=too-few-public-methods
class JSONMixin(object):
    """ A mixin class which provides basic serialisation
        for SQLAlchemy based table classes.
    """

    def serialise(self):
        """ Convert table to a JSON string. """
        res = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            res[col.name] = val
        return jsonify(res)


def from_json(base_cls, json_str):
    """ Create a database table class instance from a given
        JSON string.
        base_cls - The class type to create an instance of.
        json_str - The JSON string.
        Returns an instance of type base_cls
    """
    json_obj = json.loads(json_str)
    return base_cls(**json_obj)
