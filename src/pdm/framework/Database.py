#!/usr/bin/python env
""" Database helpers.
"""

import json
from flask import jsonify

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
