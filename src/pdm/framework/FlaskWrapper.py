#!/usr/bin/env python

import os
import inspect
import functools
from flask import Flask, current_app, request
from flask_sqlalchemy import SQLAlchemy

def export_inner(obj, ename, methods=None):
  if not methods:
    methods = ["GET"]
  obj._is_exported = True
  obj._export_name = ename
  obj._export_methods = methods
  obj._export_auth = []
  return obj

def export(obj):
  return export_inner(obj, obj.__name__)

def export_ext(ename, methods=None):
  return functools.partial(export_inner, ename=ename, methods=methods)

def startup(obj):
  obj._is_startup = True
  return obj

def db_model(db_obj):
  def attach_db(obj):
    obj._db_model = db_obj
    return obj
  return attach_db


class DBContainer(object):
  pass

class FlaskServer(Flask):

  @staticmethod
  def __init_handler():
    # TODO: Actually process auth
    request.db = current_app.db

  def __update_dbctx(self, dbobj):
    self.__db = dbobj
    with self.app_context():
      current_app.db = dbobj

  def __add_tables(self):
    print "*** ADD ***"
    print self.__db.metadata.tables
    print self.__db.Model._decl_class_registry.keys()
    self.__db.tables = DBContainer()
    registry = self.__db.Model._decl_class_registry
    for tbl_name, tbl_inst in registry.iteritems():
      if hasattr(tbl_inst, '__tablename__'):
        setattr(self.__db.tables, tbl_name, tbl_inst)
    print "*** ADD ***"
    pass

  def __init__(self):
    Flask.__init__(self, "bah") # TODO: Proper name here!
    self.before_request(self.__init_handler)
    self.__update_dbctx(None)
    self.__startup_funcs = []
    
  def enable_db(self, db_uri):
    self.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(self)
    self.__update_dbctx(db)
    print dir(db)

  def before_startup(self):
    with self.app_context():
      if self.__db:
        self.__add_tables()
        self.__db.create_all()
      for func in self.__startup_funcs:
        func()

  def attach_obj(self, obj_inst, root_path='/'):
    if hasattr(obj_inst, '_is_exported'):
      ename = obj_inst._export_name
      obj_path = os.path.join(root_path, ename)
      if not callable(obj_inst):
        # TODO: Proper logging
        print "Class %s at %s" % (obj_inst, obj_path)
        if hasattr(obj_inst, '_db_model'):
          # TODO: Tidy this up!
          print "Extending DB model with %s" % obj_inst._db_model
          db_model = obj_inst._db_model(self.__db.Model)
        items = [x for x in dir(obj_inst) if not x.startswith('_')]
        for obj_item in [getattr(obj_inst, x) for x in items]:
          self.attach_obj(obj_item, obj_path)
      else:
        print "Attaching %s at %s" % (obj_inst, obj_path)
        self.add_url_rule(obj_path, obj_inst.__name__, obj_inst,
                          methods=obj_inst._export_methods)
    elif hasattr(obj_inst, '_is_startup'):
      if obj_inst._is_startup:
        self.__startup_funcs.append(obj_inst)
