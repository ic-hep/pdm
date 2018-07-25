#!/usr/bin/env python
""" Starting point for all things WebPage related """

import os
import json
import hashlib
import stat
import time
from operator import itemgetter
import jinja2
import flask
from flask import request, flash, current_app, redirect, render_template, make_response, url_for, abort
from pdm.framework.Decorators import export, export_ext, startup, decode_json_data
from pdm.framework.ACLManager import set_session_state
from pdm.framework.RESTClient import RESTException
from pdm.userservicedesk.HRClient import HRClient
from pdm.site.SiteClient import SiteClient
from pdm.userservicedesk.TransferClient import TransferClient


def gravitar_hash(email_add):
    """
    Hash an email address.
    Generate a gravitar compatible hash from an email address.
    Args:
        email_add (str): The target email address
    Returns:
        str: The hash string
    """
    return hashlib.md5(email_add.strip().lower()).hexdigest()


jinja2.filters.FILTERS['gravitar_hash'] = gravitar_hash


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
        log = current_app.log
        log.info("Web interface starting")
        current_app.hrclient = HRClient()
        current_app.siteclient = SiteClient()


    @staticmethod
    def datamover_status():
        """returns the current status of the data mover"""
        status = "In development"
        return status


    @staticmethod
    @export_ext("/")
    def web_entry():
        """ Redirect clients to the turtles page. """
        return redirect("/web/datamover")

#    @staticmethod
#    @export_ext("about")
#    def aboutpage():
#        """renders the about page"""
#        return render_template("about.html")


    @staticmethod
    @export_ext("datamover")
    def website():
        """to render the datamover entry/login page"""
        status = WebPageService.datamover_status()
        return render_template("datamover.html", status=status,
                               accept_cookies=flask.session.get("accept_cookies", False))

    @staticmethod
    @export_ext("datamover", methods=["POST"])
    def website_post():
        """takes input fom login form and processes it"""
        # check if login is correct
        log = current_app.log
        username = request.form['username']
        password = request.form['password']
        try:
            token = current_app.hrclient.login(username, password)
            set_session_state(True)
            flask.session["token"] = token
            flask.session["accept_cookies"] = True
        except Exception as err:
            log.warning("Failed login: %s", err.message)
            flash('Could not login user (%s)' % err)
            return WebPageService.website()
        return redirect(url_for("WebPageService.dashboard"))


    @staticmethod
    @export_ext("logout")
    def logout():
        """logs the user out by removing the token"""
        flask.session.pop("token")
        set_session_state(False)
        flash('You have been logged out.')
        return redirect("/web/datamover")

    # *** registration ***
    @staticmethod
    # page and function have the same name, so 'export' is sufficient
    @export
    def registration():
        """renders the registration page"""
        return render_template("registration.html", accept_cookies=True)

    @staticmethod
    @export_ext("registration", methods=["POST"])
    def registration_post():
        """deals with the registration form"""
        if request.form['password'] != request.form['password_repeat']:
            # to do: make sure page does not come back blank
            return render_template("registration.html", accept_cookies=True)
        # create dictionary to match HRClient input
        hrdict = {
            "email": request.form['username'],
            "name": request.form['forename'],
            "surname": request.form['surname'],
            "password": request.form['password'],
        }

        try:
            current_app.hrclient.add_user(hrdict)
        except Exception as err:
            return render_template("registration.html", accept_cookies=True)
        return redirect("/web/datamover")

    @staticmethod
    @export_ext("js/jobs")
    def jobs():
        token = flask.session['token']
        tclient = TransferClient(token)
        return json.dumps(tclient.jobs())

    @staticmethod
    @export_ext("js/jobs/<int:job_id>/elements")
    def elements(job_id):
        token = flask.session['token']
        tclient = TransferClient(token)
        elements = tclient.elements(job_id)
        return json.dumps(elements)

    @staticmethod
    @export_ext("dashboard/joblist")
    def joblist():
        # will abort of user is not logged in
        user_token = flask.session['token']
        # unpacked_user_token = TokenService.unpack(user_token)
        current_app.hrclient.set_token(user_token)
        try:
            user = current_app.hrclient.get_user()
        except RESTException as err:
            return redirect(url_for('WebPageService.website'))
        return render_template("joblist.html", user=user)
    # *** The main page ***


    @staticmethod
    @export_ext("dashboard")
    def dashboard():
        """arrivals: what the user sees after logging in"""
        # will abort of user is not logged in
        user_token = flask.session['token']
        # unpacked_user_token = TokenService.unpack(user_token)
        current_app.hrclient.set_token(user_token)
        try:
            user = current_app.hrclient.get_user()
        except RESTException as err:
            return redirect(url_for('WebPageService.website'))
        #user_name = user_data['name']
        # returns a list of sites as dictionaries
        # want to sort on 'site_name'
#        current_app.epclient.set_token(user_token)
#        sites = current_app.epclient.get_sites()
#        sorted_sites = sorted(sites, key=lambda k: k['site_name'])
#        return render_template("dashboard.html", sites=sorted_sites, username=user_name)
        return render_template("newjob.html", user=user)

    @staticmethod
    @export_ext("sitelogin/<site_name>", ['POST'])
    @decode_json_data
    def site_login(site_name):
        site = current_app.site_map.get(site_name)
        if site is None:
            return "EEP!"
        username = request.data.get('username')
        password = request.data.get('password')

        if username is None:
            return "EEP!"
        if password is None:
            return "EEP!"
        token = flask.session['token']
        current_app.siteclient.set_token(token)
        session_info = current_app.siteclient.get_session_info(site['site_id'])
        if not session_info['ok']:
            try:
                current_app.siteclient.logon(site['site_id'], username, password)
            except RESTException as err:
                if err.code == 403:
                    err.code = 401  # dont trigger login page loading again.
                abort(err.code, description="Login failure.")
        return '', 200

    @staticmethod
    @export_ext("js/sites")
    def js_sites():
        """lists sites."""
        user_token = flask.session['token']
#        sites = TransferClient(user_token).list_sites()

        current_app.siteclient.set_token(flask.session['token'])
        current_app.site_map = {site['site_name']: site for site in current_app.siteclient.get_sites()}
        return json.dumps(sorted(current_app.site_map.values(), key=itemgetter('site_name')))

    @staticmethod
    @export_ext("js/copy", ['POST'])
    @decode_json_data
    def js_copy():
        """copy"""
        src_site = request.data['src_sitename']
        if src_site not in current_app.site_map:
            abort(400, description="Source site not known.")
        dst_site = request.data['dst_sitename']
        if dst_site not in current_app.site_map:
            abort(400, description="Destination site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.copy(src_site,
                     request.data['src_filepath'],
                     dst_site,
                     request.data['dst_filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/remove", ['POST'])
    @decode_json_data
    def js_remove():
        """copy"""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(400, description="Site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.remove(site, request.data['filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/mkdir", ['POST'])
    @decode_json_data
    def js_mkdir():
        """copy"""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(400, description="Site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.mkdir(site, request.data['dst_filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/rename", ['POST'])
    @decode_json_data
    def js_rename():
        """copy"""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(400, description="Site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.rename(site, request.data['src_filepath'], request.data['dst_filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/list", ['POST'])
    @decode_json_data
    def js_list():
        """lists a directory"""
        sitename = request.data['sitename']
        filepath = request.data['filepath']
        site = current_app.site_map.get(sitename)
        if site is None:
            abort(404, description="Site %s not found" % sitename)
        token = flask.session['token']
        current_app.siteclient.set_token(token)
        session_info = current_app.siteclient.get_session_info(site['site_id'])
        if not session_info['ok']:
            username = session_info.get('username', '')
            return render_template("loginform.html", username=username, sitename=sitename), 403
        # decode parameters
#        siteid = request.args.get('siteid', None)
#        sitepath = request.args.get('sitepath', None)
#        if (not siteid) or (not sitepath):
#            return "Missing request parameter", 400


        tclient = TransferClient(token)
        jobinfo = tclient.list(sitename, filepath, depth=1)

        if jobinfo:
            time.sleep(1)
            status = tclient.status(jobinfo['id'])
            while status['status'] not in ('DONE', 'FAILED'):
                time.sleep(1)  # seconds
                status = tclient.status(jobinfo['id'])

            if status['status'] == 'DONE':
                listing_output = [dict(f, is_dir=stat.S_ISDIR(f['st_mode'])) for f in tclient.output(jobinfo['id'])[0]['listing'].values()[0]]
            elif jobinfo['status'] == 'FAILED':
                print " Failed to obtain a listing for job %d " % (jobinfo['id'],)
            else:
                print "Timeout. Last status is %s for job id %d" % \
                      (status['status'], jobinfo['id'])


        return json.dumps(listing_output)

#    @staticmethod
#    @export_ext("js/list/<site_name>", ['GET'])
#    @export_ext("js/list/<site_name>/<path>", ['GET'])
#    def js_list(site_name, path='~'):
#        """lists a directory"""
#        site = current_app.site_map.get(site_name)
#        if site is None:
#            abort(404, description="Site %s not found" % site_name)
#        token = flask.session['token']
#        current_app.siteclient.set_token(token)
#        session_info = current_app.siteclient.get_session_info(site['site_id'])
#        if not session_info['ok']:
#            username = session_info.get('username', '')
#            return render_template("loginform.html", username=username), 403
#        # decode parameters
##        siteid = request.args.get('siteid', None)
##        sitepath = request.args.get('sitepath', None)
##        if (not siteid) or (not sitepath):
##            return "Missing request parameter", 400
#
#
#        tclient = TransferClient(token)
#        jobinfo = tclient.list(site_name, path, depth=1)
#
#        if jobinfo:
#            time.sleep(1)
#            status = tclient.status(jobinfo['id'])
#            while status['status'] not in ('DONE', 'FAILED'):
#                time.sleep(1)  # seconds
#                status = tclient.status(jobinfo['id'])
#
#            if status['status'] == 'DONE':
#                listing_output = [dict(f, is_dir=stat.S_ISDIR(f['st_mode'])) for f in tclient.output(jobinfo['id'])[0]['listing'].values()[0]]
#            elif jobinfo['status'] == 'FAILED':
#                print " Failed to obtain a listing for job %d " % (jobinfo['id'],)
#            else:
#                print "Timeout. Last status is %s for job id %d" % \
#                      (status['status'], jobinfo['id'])
#
#
#        return json.dumps(listing_output)


    @staticmethod
    @export_ext("js/status")
    def js_status():
        """returns the status for a given jobid"""
        jobid = request.args.get('jobid', None)
        if not jobid:
            return "No JOBID returned", 400
        user_token = flask.session['token']
        tclient = TransferClient(user_token)
        res = tclient.status(jobid)
        if res['status'] in ('DONE', 'FAILED'):
            res.update(tclient.output(jobid))
        return json.dumps(res)

#    @staticmethod
#    @export_ext("js/copy")
#    def js_copy():
#        """interface to the actual copy function"""
#        source_site = request.args.get('source_site', None)
#        source_path = request.args.get('source_path', None)
#        dest_site = request.args.get('dest_site', None)
#        dest_dir_path = request.args.get('dest_dir_path', None)
#        if (not source_site) or (not source_path):
#            return "Missing source parameter", 400
#        if (not dest_site) or (not dest_dir_path):
#            return "Missing destination parameter", 400
#        user_token = flask.session['token']
#        tclient = TransferClient(user_token)
#        jobinfo = tclient.copy(source_site, source_path,
#                               dest_site, dest_dir_path)
#        return json.dumps(jobinfo['id'])
