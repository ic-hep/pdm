#!/usr/bin/env python
""" Starting point for all things WebPage related """

import json
import flask
from flask import request, flash
from pdm.framework.FlaskWrapper import export, export_ext, startup, db_model, jsonify
from pdm.userservicedesk.HRClient import HRClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.userservicedesk.TransferClient import TransferClient


@export_ext("/web")
class WebPageService(object):
    """ The main endpoint container class for DemoService. """

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


    @staticmethod
    def datamover_status():
        """returns the current status of the data mover"""
        status = "In development"
        return status

    @staticmethod
    def check_session():
        """check if user is logged in"""
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
        """to render the datamover entry/login page"""
        status = WebPageService.datamover_status()
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
            status = WebPageService.datamover_status()
            return flask.render_template("datamover.html", status=status)

        resp = flask.make_response(flask.redirect("/web/dashboard"))
        resp.set_cookie('name', 'I am cookie')
        return resp       

        # return flask.redirect("/web/dashboard")    

    @staticmethod
    @export_ext("logout")
    def logout():
        flask.session.pop("token")
        flash('You have been logged out.')
        return flask.redirect("/web/datamover")

    @staticmethod
    @export_ext("dashboard")
    def dashboard():
        """arrivals: what the user sees after logging in"""
        # will abort of user is not logged in
        WebPageService.check_session()
        sites = flask.current_app.epclient.get_sites()
        return flask.render_template("dashboard.html", sites=sites)

    @staticmethod
    @export_ext("listings", methods=["GET"])
    def listings():
        WebPageService.check_session()
        sites = flask.current_app.epclient.get_sites()
        return flask.render_template("listings.html", sites=sites)

    @staticmethod
    @export_ext("listings", methods=["POST"])
    def listings_post():
        WebPageService.check_session()
        siteid = request.form['Endpoints']
        # temp hack:

        site=flask.current_app.epclient.get_site(int(siteid))['site_name']
        
        user_token = flask.session['token']
        tclient = TransferClient(user_token)
        sitelist = tclient.list(site, "/")
        return str(sitelist)
        # return flask.redirect("/web/dashboard", siteid=siteid)



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
            flash('The two passwords do not match.')
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
            flash('Could not add user (%s)' % err)
            return flask.render_template("registration.html")
            
        return '%s' % request.form



    @staticmethod
    @export_ext("js/list")
    def js_list():
        """lists a directory"""
        WebPageService.check_session()
        # decode parameters
        siteid = request.args.get('siteid', None)
        sitepath = request.args.get('sitepath', None)
        if (not siteid) or (not sitepath):
            return "Missing request parameter", 400
        
        user_token = flask.session['token']
        tclient = TransferClient(user_token)
        jobinfo = tclient.list(siteid, sitepath)
        return json.dumps(jobinfo['id'])

        

        # once done return status and results

    @staticmethod
    @export_ext("js/status")
    def js_status():
        """returns the status for a given jobid"""
        WebPageService.check_session()
        jobid = request.args.get('jobid', None)
        if not jobid:
            return "No JOBID returned", 400
        user_token = flask.session['token']
        tclient = TransferClient(user_token)
        # tclient.status(jobid) ... hopefully
        res = {'status' : 'DONE', 'files' : []}
        
        return json.dumps(res)

        
