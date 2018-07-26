#!/usr/bin/env python
"""Datamover's Web Service."""

import json
import hashlib
import stat
import time
from operator import itemgetter

import jinja2
import flask
from flask import request, flash, current_app, redirect, render_template, url_for, abort

from pdm.framework.Decorators import export_ext, startup, decode_json_data
from pdm.framework.ACLManager import set_session_state
from pdm.framework.RESTClient import RESTException
from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.HRUtils import HRUtils
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
    """The Datamover's web page service."""

    @staticmethod
    @startup
    # pylint: disable=unused-argument
    def startup_web(config):
        """Configure the web service."""
        current_app.log.info("Web interface starting")
        current_app.hrclient = HRClient()
        current_app.hrutils = HRUtils()
        current_app.siteclient = SiteClient()
        current_app.site_map = {}

    @staticmethod
    @export_ext("/")
    def web_entry():
        """Redirect to default entry point."""
        return redirect(url_for("WebPageService.front_portal"))

    @staticmethod
    @export_ext("datamover", methods=["GET"])
    def front_portal():
        """Render the Datamover's front portal."""
        username = ''
        user_token = flask.session.get('token', None)
        if user_token is not None:
            username = current_app.hrutils.get_token_username_insecure(user_token)
        return render_template("datamover.html", status="In development", username=username,
                               accept_cookies=flask.session.get("accept_cookies", False))

    @staticmethod
    @export_ext("datamover", methods=["POST"])
    def pdm_login():
        """Log a client into the Datamover."""
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
            return WebPageService.front_portal()
        return redirect(url_for("WebPageService.dashboard"))

    @staticmethod
    @export_ext("logout")
    def pdm_logout():
        """Log a client out of the Datamover"""
        flask.session.pop("token")
        set_session_state(False)
        flash('You have been logged out.')
        return redirect(url_for("WebPageService.front_portal"))

    @staticmethod
    @export_ext("registration", methods=["GET"])
    def registration_portal():
        """Render the Datamover's registration page."""
        return render_template("registration.html", accept_cookies=True)

    @staticmethod
    @export_ext("registration", methods=["POST"])
    def sign_up():
        """Sign a client up for Datamover access."""
        forename = request.form['forename']
        surname = request.form['surname']
        username = request.form['username']
        password = request.form['password']
        password_repeat = request.form['password_repeat']
        if password != password_repeat:
            # to do: make sure page does not come back blank
            return render_template("registration.html", username=username, forename=forename,
                                   surname=surname, password=password,
                                   password_repeat=password_repeat, accept_cookies=True)
        hrdict = {"email": username,
                  "name": forename,
                  "surname": surname,
                  "password": password}
        try:
            current_app.hrclient.add_user(hrdict)
        except RESTException:
            current_app.log.exception("Error registering user")
            return render_template("registration.html", username=username, forename=forename,
                                   surname=surname, password=password,
                                   password_repeat=password_repeat, accept_cookies=True)
        return redirect(url_for("WebPageSevice.front_portal"))

    @staticmethod
    @export_ext("dashboard/joblist")
    def joblist():
        """Return the Datamover's job listing page."""
        # will abort of user is not logged in (if getting token raises keyerror)
        user_token = flask.session['token']
        current_app.hrclient.set_token(user_token)
        try:
            user = current_app.hrclient.get_user()
        except RESTException:
            current_app.log.exception("Error getting jobs list")
            return redirect(url_for('WebPageService.front_portal'))
        return render_template("joblist.html", user=user)

    @staticmethod
    @export_ext("dashboard")
    def dashboard():
        """Render the Datamover's main dashboard page."""
        # will abort of user is not logged in (if getting token raises keyerror)
        user_token = flask.session['token']
        current_app.hrclient.set_token(user_token)
        try:
            user = current_app.hrclient.get_user()
        except RESTException:
            current_app.log.exception("Error getting dashboard")
            return redirect(url_for('WebPageService.front_portal'))
        return render_template("newjob.html", user=user)

    @staticmethod
    @export_ext("sitelogin/<site_name>", ['POST'])
    @decode_json_data
    def site_login(site_name):
        """Log client in to given site."""
        site = current_app.site_map.get(site_name)
        if site is None:
            abort(404, "Site not found")

        username = request.data.get('username')
        password = request.data.get('password')
        if username is None:
            abort(400, "username required but missing.")
        if password is None:
            abort(400, "password required but missing.")

        token = flask.session['token']
        current_app.siteclient.set_token(token)
        session_info = current_app.siteclient.get_session_info(site['site_id'])
        if not session_info['ok']:
            try:
                current_app.siteclient.logon(site['site_id'], username, password)
            except RESTException as err:
                current_app.log.exception("Error logging into site %s(id: %s)",
                                          site_name, site['site_id'])
                if err.code == 403:
                    err.code = 401  # dont trigger login page loading again.
                abort(err.code, description="Login failure.")
        return '', 200

    @staticmethod
    @export_ext("js/jobs")
    def jobs():
        """List a user's jobs."""
        token = flask.session['token']
        tclient = TransferClient(token)
        return json.dumps(tclient.jobs())

    @staticmethod
    @export_ext("js/jobs/<int:job_id>/elements")
    def elements(job_id):
        """List elements for a given user's job."""
        token = flask.session['token']
        tclient = TransferClient(token)
        elements = tclient.elements(job_id)
        return json.dumps(elements)

    @staticmethod
    @export_ext("js/sites")
    def js_sites():
        """lists all registered sites."""
        token = flask.session['token']
        current_app.siteclient.set_token(token)
        current_app.site_map = {site['site_name']: site
                                for site in current_app.siteclient.get_sites()}
        return json.dumps(sorted(current_app.site_map.values(), key=itemgetter('site_name')))

    @staticmethod
    @export_ext("js/copy", ['POST'])
    @decode_json_data
    def js_copy():
        """Resister a COPY job."""
        src_site = request.data['src_sitename']
        if src_site not in current_app.site_map:
            abort(404, description="Source site not known.")
        dst_site = request.data['dst_sitename']
        if dst_site not in current_app.site_map:
            abort(404, description="Destination site not known.")
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
        """Register a REMOVE job."""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(404, description="Site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.remove(site, request.data['filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/mkdir", ['POST'])
    @decode_json_data
    def js_mkdir():
        """Register a MKDIR job."""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(404, description="Site not known.")
        token = flask.session['token']
        tclient = TransferClient(token)
        tclient.mkdir(site, request.data['dst_filepath'])
        return '', 200

    @staticmethod
    @export_ext("js/rename", ['POST'])
    @decode_json_data
    def js_rename():
        """Register a RENAME job."""
        site = request.data['sitename']
        if site not in current_app.site_map:
            abort(404, description="Site not known.")
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

        tclient = TransferClient(token)
        jobinfo = tclient.list(sitename, filepath, depth=1)

        listing_output = []
        if jobinfo:
            time.sleep(1)
            status = tclient.status(jobinfo['id'])
            while status['status'] not in ('DONE', 'FAILED'):
                time.sleep(1)  # seconds
                status = tclient.status(jobinfo['id'])

            if status['status'] == 'DONE':
                listing_output = [dict(f, is_dir=stat.S_ISDIR(f['st_mode'])) for f in
                                  tclient.output(jobinfo['id'])[0]['listing'].values()[0]]
            elif jobinfo['status'] == 'FAILED':
                current_app.log.error("Failed to obtain a listing for job %d", jobinfo['id'])
            else:
                current_app.log.warning("Timeout. Last status is %s for job id %d",
                                        status['status'], jobinfo['id'])

        return json.dumps(listing_output)
