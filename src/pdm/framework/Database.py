#!/usr/bin/python env

import json
from flask import jsonify

class JSONMixin(object):

  def serialise(self):
    res = {}
    for col in self.__table__.columns:
      val = getattr(self, col.name)
      res[col.name] = val
    return jsonify(res)


def from_json(base_obj, jsonstr):
  obj = json.loads(jsonstr)
  return base_obj(**obj)

