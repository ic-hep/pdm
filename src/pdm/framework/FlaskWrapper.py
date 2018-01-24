#!/usr/bin/env python
""" A wrapper around Flask that provides application specific
    authentication, logging and database services.
"""

import os
import inspect
import functools
from flask import Flask, current_app, request
from flask_sqlalchemy import SQLAlchemy

def export_inner(obj, ename, methods=None):
  """ Inner function for export decorators.
      Obj is the object to export,
      See the export_ext function for further more details on the other
      parameters.
  """
  if not methods:
    methods = ["GET"]
  obj._is_exported = True
  obj._export_name = ename
  obj._export_methods = methods
  obj._export_auth = []
  return obj

def export(obj):
  """ Class/Function decorator.
      Export a class or function via the GET method on the web-server.
      The export name will be the __name__ value of the object.
  """
  return export_inner(obj, obj.__name__)

def export_ext(ename, methods=None):
  """ Class/Function decorator.
      Export a class or function via the web-server with extra options.
      ename - Export name of the item. This may be a relative name to inherit
              from the parent object, or absolute for an absolute path on the
              webserver.
      methods - A list of flask-style method names, i.e. ["GET", "POST"]
                to allow access to this object. Defaults to GET only if set
                to None.
  """
  return functools.partial(export_inner, ename=ename, methods=methods)

def startup(obj):
  """ Funciton decorator.
      Marks a function to be called at start-up on the webserver.
      The function will be called at the end of daemonisation before
      requests are accepted. The function is run in the application context
      (so flask.current_app is available, but not flask.request).
      The function should take a single parameter, which will recieve a
      dictionary of config options from the config file. If the application
      uses any keys, they should be removed from the dictionary.
  """
  obj._is_startup = True
  return obj

def db_model(db_obj):
  """ Attaches a non-instantiated class as the database model for this class.
      The annotated class should be exported with the export decorator.
      The database class should have an __init__ which takes a single model
      parameter. All database classes should be defined within __init__ and
      use the model parameter as the base class.
  """
  def attach_db(obj):
    obj._db_model = db_obj
    return obj
  return attach_db


class DBContainer(object):
  """ A container of DB Table models.
      References to the table objects are dynamitcally attached to an instance
      of this object at runtime.
  """
  pass

class FlaskServer(Flask):
  """ A wrapper around a flask application server providing additional
      configuration & runtime helpers.
  """

  @staticmethod
  def __init_handler():
    """ This function is registered as a "before_request" callback and
        handles checking the request authentication. It also posts various
        parts of the app context into the request proxy object for ease of
        use.
    """
    # TODO: Actually process auth
    request.db = current_app.db

  def __update_dbctx(self, dbobj):
    """ Updates this objects database object within the application context.
        dbobj - The new database object (should be an instance of SQLAlchemy()
        Returns None.
    """
    self.__db = dbobj
    with self.app_context():
      current_app.db = dbobj

  def __add_tables(self):
    """ Creates a new DBContainer within the database object
        (as db.tables) and attaches all currently pending tables to it.
        Returns None.
    """
    self.__db.tables = DBContainer()
    registry = self.__db.Model._decl_class_registry
    for tbl_name, tbl_inst in registry.iteritems():
      if hasattr(tbl_inst, '__tablename__'):
        setattr(self.__db.tables, tbl_name, tbl_inst)

  def __init__(self):
    """ Constructs the server.
    """
    Flask.__init__(self, "bah") # TODO: Proper name here!
    self.before_request(self.__init_handler)
    self.__update_dbctx(None)
    self.__startup_funcs = []
    
  def enable_db(self, db_uri):
    """ Enables a database connection pool for this server.
        db_uri - An SQLAlchemy compliant Db conection string.
        Should be called before any calls to attach_obj.
        Returns None.
    """
    self.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(self)
    self.__update_dbctx(db)

  def before_startup(self, config):
    """ This function calls creates the database (if enabled) and calls
        any functions registered with the @startup constructor.
        This should be called immediately before starting the main request
        loop.
        The config parmemter is passed through to the registered functions,
        it should be a dictionary of config parameters.
        Returns None.
    """
    with self.app_context():
      if self.__db:
        self.__add_tables()
        self.__db.create_all()
      for func in self.__startup_funcs:
        func(config)

  def attach_obj(self, obj_inst, root_path='/'):
    """ Attaches an object tree to this web service.
        For each exported object, it is attached to the path tree and
        then all of its children are checked for the exported flag.
        obj_inst - The root object to start scanning.
        root_path - The base path to start attaching relative paths from.
        Returns None.
    """
    if hasattr(obj_inst, '_is_exported'):
      ename = obj_inst._export_name
      obj_path = os.path.join(root_path, ename)
      if not callable(obj_inst):
        # TODO: Proper logging
        print "Class %s at %s" % (obj_inst, obj_path)
        if hasattr(obj_inst, '_db_model'):
          # TODO: Tidy this up!
          print "Extending DB model with %s" % obj_inst._db_model
          obj_inst._db_model(self.__db.Model)
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
