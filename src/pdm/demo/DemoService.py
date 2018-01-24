#!/usr/bin/env python

import flask
from flask import request, jsonify
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model
from pdm.framework.Database import from_json

import pdm.demo.DemoDB

@export_ext("/demo/api/v1.0")
@db_model(pdm.demo.DemoDB.DBModel)
class DemoService(object):

  @staticmethod
  @startup
  def preload_turtles(config):
    log = flask.current_app.log
    test_param = config.pop("test_param", 0)
    log.info("Hello Turtles (%u)", test_param)
    db = flask.current_app.db
    Turtle = db.tables.Turtle
    num = db.session.query(Turtle).count()
    if num:
      print "%u turtle(s) already exist." % num
      return
    # No turtles, add some...
    turtles = (Turtle(name='Timmy'),
               Turtle(name='Jimmy'),
               Turtle(name='Mimmy'),
              )
    db.session.bulk_save_objects(turtles)
    db.session.commit()
    
  @staticmethod
  @export
  def hello():
    return jsonify("Hello World!\n")

  @staticmethod
  @export_ext("turtles")
  def turtles_get():
    db = request.db
    Turtle = db.tables.Turtle
    res = {x.id:x.name for x in db.session.query(Turtle).all()}
    return jsonify(res)

  @staticmethod
  @export_ext("turtles/<int:tid>")
  def turtles_info(tid):
    db = request.db
    Turtle = db.tables.Turtle
    res = Turtle.query.filter_by(id=tid).first_or_404()
    return res.serialise()

  @staticmethod
  @export_ext("turtles/<int:tid>", ["DELETE"])
  def turtles_delete(tid):
    db = request.db
    Turtle = db.tables.Turtle
    res = Turtle.query.filter_by(id=tid).first_or_404()
    if res.name == 'Timmy':
      return "Undeletable\n", 401
    db.session.delete(res)
    db.session.commit()
    return ""

  @staticmethod
  @export_ext("turtles", ["POST"])
  def turtles_add():
    db = request.db
    Turtle = db.tables.Turtle
    res = from_json(Turtle, request.data)
    db.session.add(res)
    db.session.commit()
    return res.serialise()

