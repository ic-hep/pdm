#!/usr/bin/env python

from flask import request
from pdm.framework.FlaskWrapper import export, export_ext, db_model
from pdm.demo.DemoDB import DBModel

@export_ext("/demo/api/v1.0")
#@db_model(DBModel)
class DemoService(object):

  @staticmethod
  @export_ext("hello", ['GET', 'POST'])
  def hello():
    print "DB Test: %s" % request.db
    return "Hello World!\n"

