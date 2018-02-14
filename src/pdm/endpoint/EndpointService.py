#!/usr/bin/env python
""" Site/Endpoint service module. """

import json
from flask import request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from pdm.framework.FlaskWrapper import db_model, export_ext, jsonify
from pdm.endpoint.EndpointDB import EndpointDBModel
from pdm.utils.db import managed_session

@export_ext('/endpoints/api/v1.0')
@db_model(EndpointDBModel)
class EndpointService(object):
    """ Endpoint service. """

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
        # TODO: Check for duplicate site_name
        try:
            with managed_session(db) as session:
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
        try:
            with managed_session(db) as session:
                session.delete(site)
        #pylint: disable=broad-except
        except Exception:
            return "Failed to remote site from DB", 500
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
        try:
            with managed_session(db) as session:
                session.add(new_ep)
        #pylint: disable=broad-except
        except Exception:
            return "Failed to add endpoint to DB", 500
        return jsonify(new_ep.ep_id)

    @staticmethod
    @export_ext("site/<int:site_id>/<int:ep_id>", ["DELETE"])
    def del_endpoint(site_id, ep_id):
        """ Delete an endpoint. """
        db = request.db
        Endpoint = db.tables.Endpoint
        endpoint = Endpoint.query.filter_by(site_id=site_id,
                                            ep_id=ep_id).first_or_404()
        try:
            with managed_session(db) as session:
                session.delete(endpoint)
        #pylint: disable=broad-except
        except Exception:
            return "Failed to delete endpoint from DB", 500
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
            with managed_session(db) as session:
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
        try:
            with managed_session(db) as session:
                session.delete(entry)
        #pylint: disable=broad-except
        except Exception:
            return "Failed to del sitemap from DB", 500
        return ""

    @staticmethod
    @export_ext("sitemap/all/<int:user_id>", ["DELETE"])
    def del_sitemap_user(user_id):
        """ Delete a user from all site maps. """
        db = request.db
        UserMap = db.tables.UserMap
        try:
            # We do this the long way with managed_session to make testing
            # more easy, otherwise we could just do .delete() instead of
            # .all()
            with managed_session(db) as session:
                mappings = UserMap.query.filter_by(user_id=user_id).all()
                for entry in mappings:
                    session.delete(entry)
        #pylint: disable=broad-except
        except Exception:
            return "Failed to del user from sitemaps", 500
        return ""
