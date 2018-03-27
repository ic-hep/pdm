#!/usr/bin/env python
""" Starting point for all things WebPage related """

import json
import flask
from flask import request, flash
from pdm.framework.FlaskWrapper import jsonify
from pdm.framework.Decorators import export, export_ext, startup, db_model
from pdm.framework.ACLManager import set_session_state
from pdm.userservicedesk.HRClient import HRClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.userservicedesk.TransferClient import TransferClient


@export_ext("/web", redir="/web/datamover?return_to=%(return_to)s")
class WebPageService(object):
    """ The main endpoint container class for DemoService. """

    @staticmethod
    @startup
    #pylint: disable=unused-argument
    def startup_web(config):
        """ Configure the turtles application.
            Creates an example database if DB is entry.
            Prints valud of "test_param" from the config.
        """
        log = flask.current_app.log
        log.info("Web interface starting")
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
        """takes input fom login form and processes it"""
        # check if login is correct
        username = request.form['uname']
        password = request.form['pswd']
        try:
            token = flask.current_app.hrclient.login(username, password)
            set_session_state(True)
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
        """logs the user out by removing the token"""
        flask.session.pop("token")
        set_session_state(False)
        flash('You have been logged out.')
        return flask.redirect("/web/datamover")

    @staticmethod
    @export_ext("dashboard")
    def dashboard():
        """arrivals: what the user sees after logging in"""
        # will abort of user is not logged in
        sites = flask.current_app.epclient.get_sites()
        return flask.render_template("dashboard.html", sites=sites)

    @staticmethod
    @export_ext("listings", methods=["GET"])
    def listings():
        """renders the listing page with a list of all sites"""
        sites = flask.current_app.epclient.get_sites()
        return flask.render_template("listings.html", sites=sites)

    @staticmethod
    @export_ext("listings", methods=["POST"])
    def listings_post():
        """processes input to listings form"""
        WebPageService.check_session()
        siteid = request.form['Endpoints']
        # temp hack:
        site = flask.current_app.epclient.get_site(int(siteid))['site_name']
        user_token = flask.session['token']
        tclient = TransferClient(user_token)
        sitelist = tclient.list(site, "/")
        return str(sitelist)
        # return flask.redirect("/web/dashboard", siteid=siteid)



    @staticmethod
    @export_ext("about")
    def aboutpage():
        """renders the about page"""
        return flask.render_template("about.html")

    @staticmethod
    @export_ext("hello")
    # TODO: clashing filenames
    # at the moment all functions must have different names
    # just 'hello' clashes with Janusz' code
    def hello_web():
        """ Returns a test string. """
        return jsonify("Hello World!\n")


    # *** registration ***
    @staticmethod
    # page and function have the same name, so 'export' is sufficient
    @export
    def registration():
        """renders the registration page"""
        return flask.render_template("registration.html")


    @staticmethod
    @export_ext("registration", methods=["POST"])
    def registration_post():
        """deals with the registration form"""
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
        res = tclient.status(jobid)
        if res['status'] in ('DONE','FAILED'):
            res.update(tclient.output(jobid))
#        res = tclient.status(jobid)
        """
        res = {'status' : 'DONE', 'listings' :
               [{'permissions' : '-rw-r--r--',
                 'nlinks' : '1',
                 'userid' : '1234',
                 'groupid' : '5678',
                 'size' : '12345678',
                 'datestamp' : 'Mar  2 11:15',
                 'name' : 'file1',
                 'is_directory' : False},
                {'permissions' : '-rw-rw-r--',
                 'nlinks' : '2',
                 'userid' : '2234',
                 'groupid' : '2678',
                 'size' : '22345678',
                 'datestamp' : 'Mar  3 11:15',
                 'name' : 'file2',
                 'is_directory' : False},
                {'permissions' : 'drwxr-xr-x',
                 'nlinks' : '2',
                 'userid' : '2234',
                 'groupid' : '2678',
                 'size' : '4096',
                 'datestamp' : 'Mar  3 12:15',
                 'name' : 'dir1',
                 'is_directory' : True}]}
        """
        return json.dumps(res)
