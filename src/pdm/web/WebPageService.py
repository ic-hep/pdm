#!/usr/bin/env python
""" Starting point for all things WebPage related """

import flask
from flask import request, flash
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
from pdm.userservicedesk.HRClient import HRClient

@export_ext("/web")
class WebPageService(object):
    """ The main endpoint container class for DemoService. """

    #pylint disable=invalid-name
    @staticmethod
    @startup
    def preload_turtles(config):
        """ Configure the turtles application.
            Creates an example database if DB is entry.
            Prints valud of "test_param" from the config.
        """
        # TODO: this should come from the framework
        flask.current_app.secret_key = 'muhahaha'
        log = flask.current_app.log
        log.info("Hello Real Turtles")
        flask.current_app.hrclient = HRClient()

    @staticmethod
    @export_ext("/")
    def web_entry():
        """ Redirect clients to the turtles page. """
        return flask.redirect("/web/datamover")

    @staticmethod
    @export_ext("/web/datamover")
    def website():
        """ Render the turtles page. """
        return flask.render_template("datamover.html")

    @staticmethod
    @export_ext("hello")
    # TODO: clashing filenames
    # at the moment all functions must have different names
    # just 'hello' clashes with Janusz' code
    def hello_web():
        """ Return a test string. """
        return jsonify("Hello World!\n")


    # *** registration ***
    @staticmethod
    # page and function have the same name, so 'export' is sufficient
    @export
    def registration():
        return flask.render_template("registration.html")


    @staticmethod
    @export_ext("registration", methods=["POST"])
    def registration_post():
        if request.form['password'] != request.form['cpassword']:
            flash('The two passords do not match.')
            # to do: make sure page does not come back blank
            return flask.render_template("registration.html")
        # create dictionary to match HRClient input
        hrdict = {
            "email" : request.form['email'], 
            "name" : request.form['firstname'],
            "surname" : request.form['lastname'],
            "password" : request.form['password'],
        }    

        try:
            flask.current_app.hrclient.add_user(hrdict)
        except Exception as err:
            raise
            flash('Could not add user (%s)' % err)
            return flask.render_template("registration.html")
            
        return '%s' % request.form


