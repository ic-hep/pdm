#!/usr/bin/env python
""" Starting point for all things WebPage related """

import flask
from flask import request, flash
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
from pdm.userservicedesk.HRClient import HRClient
from pdm.endpoint.EndpointClient import EndpointClient

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
    
        flask.current_app.epclient = EndpointClient()

    # checks if user is logged in    
    @staticmethod
    def check_session():
        if "token" in flask.session:
            # TODO: check if token is still valid
            return
        # TODO: Flash message about not being logged in
        flask.abort(flask.redirect("/web/datamover"))    



    @staticmethod
    @export_ext("/")
    def web_entry():
        """ Redirect clients to the turtles page. """
        return flask.redirect("/web/datamover")

    @staticmethod
    @export_ext("datamover")
    def website():
        status = "In Development"
        return flask.render_template("datamover.html", status=status)
    
    @staticmethod
    @export_ext("datamover", methods=["POST"])
    def website_post():
        # check if login is correct
        username = request.form['uname']
        password = request.form['pswd']
        try:
            token = flask.current_app.hrclient.login(username, password)
            flask.session["token"] = token
        except Exception as err:
            flash('Could not login user (%s)' % err)
            return flask.render_template("datamover.html")

        return flask.redirect("/web/dashboard")    

    @staticmethod
    @export_ext("logout")
    def logout():
        flask.session.pop("token")
        flash('You have been logged out.')
        return flask.redirect("/web/datamover")

    @staticmethod
    @export_ext("dashboard")
    def dashboard():
        # will abort of user is not logged in
        WebPageService.check_session()
        return flask.render_template("dashboard.html")

    @staticmethod
    @export_ext("listings", methods=["GET", "POST"])
    def listings():
        WebPageService.check_session()
        sites = flask.current_app.epclient.get_sites()
        return str(sites)
        # return flask.render_template("listings.html")



    @staticmethod
    @export_ext("about")
    def aboutpage():
        return flask.render_template("about.html")

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


