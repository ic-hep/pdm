#!/usr/bin/env python
""" Site/Endpoint service module. """

import json
from flask import current_app, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from pdm.framework.FlaskWrapper import (db_model, export_ext, jsonify, \
                                        startup_test)
from pdm.endpoint.EndpointDB import EndpointDBModel
from pdm.utils.db import managed_session

@export_ext('/endpoints/api/v1.0')
@db_model(EndpointDBModel)
class EndpointService(object):
    """ Endpoint service. """

    @staticmethod
    @startup_test
    def test_data():
        """ Adds test data to the database if it is empty.
        """
        db = current_app.db
        Site = db.tables.Site
        Endpoint = db.tables.Endpoint
        rows = Endpoint.query.count()
        if rows:
            return
        entries = [
            Site(site_id=1,
                 site_name='Site1',
                 site_desc='First Test Site'),
            Site(site_id=2,
                 site_name='Site2',
                 site_desc='Second Test Site'),
            Endpoint(ep_id=1,
                     site_id=1,
                     ep_uri='gsiftp://localhost/site1'),
            Endpoint(ep_id=2,
                     site_id=1,
                     ep_uri='ssh://localhost/site1'),
            Endpoint(ep_id=3,
                     site_id=2,
                     ep_uri='gsiftp://localhost/site2'),
            Endpoint(ep_id=4,
                     site_id=2,
                     ep_uri='ssh://localhost/site2'),
        ]
        for entry in entries:
            db.session.add(entry)
        db.session.commit()

    @staticmethod
    @export_ext("site")
    def get_site_list():
        """ Get a list of all sites. """
        db = request.db
        Site = db.tables.Site
        sites = Site.query.all()
        return jsonify(sites)

    @staticmethod
    @export_ext("site", ["POST"])
    def add_site():
        """ Add a site to the database. """
        db = request.db
        Site = db.tables.Site
        site_data = {}
        try:
            if not request.data:
                raise ValueError("Missing POST data")
            raw_site_data = json.loads(request.data)
            site_data["site_name"] = raw_site_data["site_name"]
            site_data["site_desc"] = raw_site_data["site_desc"]
        #pylint: disable=broad-except
        except Exception:
            return "Malformed POST data", 400
        # Add the new site
        site = Site(**site_data)
        try:
            with managed_session(request) as session:
                session.add(site)
        except IntegrityError:
            # site_name almost certainly already exists
            return "site_name is not unique", 409
        except Exception: #pylint: disable=broad-except
            # Some kind of other database error?
            return "Failed to add site to DB", 500
        return jsonify(site.site_id)

    @staticmethod
    @export_ext("site/<int:site_id>")
    def get_site(site_id):
        """ Get the details of a specific site. """
        db = request.db
        Site = db.tables.Site
        site = Site.query.filter_by(site_id=site_id).first_or_404()
        print site.endpoints
        # Manually build the repsonse object so we can combine
        # the endpoint list in the site object
        res = {}
        res['site_id'] = site.site_id
        res['site_name'] = site.site_name
        res['site_desc'] = site.site_desc
        eps = {}
        for ep_info in site.endpoints:
            eps[ep_info.ep_id] = ep_info.ep_uri
        res['endpoints'] = eps
        return jsonify(res)

    @staticmethod
    @export_ext("site/<int:site_id>", ["DELETE"])
    def del_site(site_id):
        """ Delete a site (including all endpoints & mappings). """
        db = request.db
        Site = db.tables.Site
        site = Site.query.filter_by(site_id=site_id).first_or_404()
        with managed_session(request,
                             message="Database error while deleting site",
                             http_error_code=500) as session:
            session.delete(site)
        return ""

    @staticmethod
    @export_ext("site/<int:site_id>", ["POST"])
    def add_endpoint(site_id):
        """ Add an endpoint to a specific site. """
        db = request.db
        Site = db.tables.Site
        Endpoint = db.tables.Endpoint
        try:
            if not request.data:
                raise ValueError("Missing POST data")
            raw_ep_data = json.loads(request.data)
            ep_uri = raw_ep_data["ep_uri"]
        #pylint: disable=broad-except
        except Exception:
            return "Malformed POST data", 400
        Site.query.filter_by(site_id=site_id).first_or_404()
        # TODO: Check ep_uri format?
        new_ep = Endpoint(ep_uri=ep_uri, site_id=site_id)
        with managed_session(request,
                             message="Failed to add endpoint to DB",
                             http_error_code=500) as session:
            session.add(new_ep)
        return jsonify(new_ep.ep_id)

    @staticmethod
    @export_ext("site/<int:site_id>/<int:ep_id>", ["DELETE"])
    def del_endpoint(site_id, ep_id):
        """ Delete an endpoint. """
        db = request.db
        Endpoint = db.tables.Endpoint
        endpoint = Endpoint.query.filter_by(site_id=site_id,
                                            ep_id=ep_id).first_or_404()
        with managed_session(request,
                             message="Failed to delete endpoint from DB",
                             http_error_code=500) as session:
            session.delete(endpoint)
        return ""

    @staticmethod
    @export_ext("sitemap/<int:site_id>")
    def get_sitemap(site_id):
        """ Get the sitemap for a specific site. """
        db = request.db
        UserMap = db.tables.UserMap
        mappings = UserMap.query.filter_by(site_id=site_id).all()
        res = {x.user_id: x.username for x in mappings}
        return jsonify(res)

    @staticmethod
    @export_ext("sitemap/<int:site_id>", ["POST"])
    def add_sitemap_entry(site_id):
        """ Add an entry to the sitemap. """
        db = request.db
        Site = db.tables.Site
        UserMap = db.tables.UserMap
        try:
            if not request.data:
                raise ValueError("Missing POST data")
            raw_map_data = json.loads(request.data)
            user_id = raw_map_data["user_id"]
            local_user = raw_map_data["local_user"]
        #pylint: disable=broad-except
        except Exception:
            return "Malformed POST data", 400
        # Check that site exists
        Site.query.filter_by(site_id=site_id).first_or_404()
        # Add the mapping
        new_map = UserMap(user_id=user_id,
                          site_id=site_id,
                          username=local_user)
        try:
            with managed_session(request) as session:
                session.add(new_map)
        except FlushError:
            return "Mapping for user_id already exists", 409
        except Exception: #pylint: disable=broad-except
            return "Failed to add sitemap to DB", 500
        return ""

    @staticmethod
    @export_ext("sitemap/<int:site_id>/<int:user_id>", ["DELETE"])
    def del_sitemap_entry(site_id, user_id):
        """ Delete an entry from the sitemap. """
        db = request.db
        UserMap = db.tables.UserMap
        entry = UserMap.query.filter_by(site_id=site_id,
                                        user_id=user_id).first_or_404()
        with managed_session(request,
                             message="Failed to del sitemap from DB",
                             http_error_code=500) as session:
            session.delete(entry)
        return ""

    @staticmethod
    @export_ext("sitemap/all/<int:user_id>", ["DELETE"])
    def del_sitemap_user(user_id):
        """ Delete a user from all site maps. """
        db = request.db
        UserMap = db.tables.UserMap
        # We do this the long way with managed_session to make testing
        # more easy, otherwise we could just do .delete() instead of
        # .all()
        with managed_session(request,
                             message="Failed to del user from sitemaps",
                             http_error_code=500) as session:
            mappings = UserMap.query.filter_by(user_id=user_id).all()
            for entry in mappings:
                session.delete(entry)
        return ""
