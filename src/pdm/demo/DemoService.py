#!/usr/bin/env python
""" A service for demonstrating FlaskWrapper. """

import flask
from flask import request, current_app
from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import (export, export_ext, startup,
                                        startup_test, db_model)

import pdm.demo.DemoDB

@export_ext("/demo/api/v1.0")
@db_model(pdm.demo.DemoDB.DBModel)
class DemoService(object):
    """ The main endpoint container class for DemoService. """

    #pylint disable=invalid-name
    @staticmethod
    @startup
    def start_turtles(config):
        """ Configure the turtles application.
            Prints valud of "test_param" from the config.
        """
        log = current_app.log
        test_param = config.pop("test_param", 0)
        log.info("Hello Turtles (%u)", test_param)

    @staticmethod
    @startup_test
    def preload_turtles():
        """ Creates an example database if DB is empty.
        """
        log = current_app.log
        db = current_app.db
        Turtle = db.tables.Turtle
        num = db.session.query(Turtle).count()
        if num:
            log.info("%u turtle(s) already exist.", num)
            return
        # No turtles, add some...
        turtles = (Turtle(name='Timmy'),
                   Turtle(name='Jimmy'),
                   Turtle(name='Mimmy'),
                  )
        for turtle in turtles:
            db.session.add(turtle)
        db.session.commit()

    @staticmethod
    @export_ext("/")
    def web_entry():
        """ Redirect clients to the turtles page. """
        return flask.redirect("/web/turtles")

    @staticmethod
    @export_ext("/web/turtles")
    def website():
        """ Render the turtles page. """
        db = request.db
        Turtle = db.tables.Turtle
        turtles = [x.name for x in db.session.query(Turtle).all()]
        return flask.render_template("turtles.html", turtles=turtles)

    @staticmethod
    @export
    def hello():
        """ Return a test string. """
        return jsonify("Hello World!\n")

    @staticmethod
    @export_ext("turtles")
    def turtles_get():
        """ Get a list of all turtle IDs and names. """
        db = request.db
        Turtle = db.tables.Turtle
        res = {x.id:x.name for x in db.session.query(Turtle).all()}
        return jsonify(res)

    @staticmethod
    @export_ext("turtles/<int:tid>")
    def turtles_info(tid):
        """ Get a full turtle entry. """
        db = request.db
        Turtle = db.tables.Turtle
        res = Turtle.query.filter_by(id=tid).first_or_404()
        return res.json()

    @staticmethod
    @export_ext("turtles/<int:tid>", ["DELETE"])
    def turtles_delete(tid):
        """ Remove a turtle from the DB. """
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
        """ Add a turtle to the DB. """
        db = request.db
        Turtle = db.tables.Turtle
        res = Turtle.from_json(request.data)
        db.session.add(res)
        db.session.commit()
        return res.json()

    @staticmethod
    @export_ext("turtles/<int:tid>", ["PUT"])
    def turtles_modify(tid):
        """ Modify a turtle entry. """
        db = request.db
        Turtle = db.tables.Turtle
        turtle = Turtle.query.filter_by(id=tid).first_or_404()
        data = Turtle.from_json(request.data)
        if data:
            turtle.name = data.name
        db.session.commit()
        return turtle.json()

    @staticmethod
    @export
    def get_token():
        """ Issue a token to the client. """
        token = request.token_svc.issue("Hello")
        return jsonify(token)

    @staticmethod
    @export
    def verify_token():
        """ Return whether a client token is valid. """
        if request.token_ok:
            res = "Token OK! (%s)" % request.token
        else:
            res = "Token Missing!"
        return jsonify(res)
