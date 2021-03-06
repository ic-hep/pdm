#!/usr/bin/env python
""" A wrapper around Flask that provides application specific
    authentication, logging and database services.
"""

import os
import json
import uuid
import logging

from pdm.framework.Tokens import TokenService
from pdm.framework.ACLManager import ACLManager
from pdm.framework.Database import MemSafeSQLAlchemy, JSONTableEncoder

from flask import Flask, Response, current_app, request
from flask.testing import FlaskClient


def jsonify(obj):
    """ Works just like Flask's jsonify method, but doesn't care about the
        input type.
        Returns a Flask response object.
    """
    return Response(json.dumps(obj, cls=JSONTableEncoder),
                    mimetype='application/json')

#pylint: disable=too-few-public-methods
class DBContainer(object):
    """ A container of DB Table models.
        References to the table objects are dynamitcally attached to an instance
        of this object at runtime.
    """
    pass

class FlaskClientWrapper(FlaskClient):
    """ A wrapper around FlaskClient used in testing, which json encodes the
        data input in the same manner as RESTClient for consistency across tests.
    """
    def __init__(self, *args, **kwargs):
        super(FlaskClientWrapper, self).__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        """ Call open on the super class but pre-encode the data arg (if
            present) into json.
        """
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        return FlaskClient.open(self, *args, **kwargs)

#pylint: disable=too-many-instance-attributes
class FlaskServer(Flask):
    """ A wrapper around a flask application server providing additional
        configuration & runtime helpers.
    """

    @staticmethod
    def __extend_request():
        """ Adds a few extra items into request from current_app for
            convenience. Particularly request.db, log & token_svc.
        """
        request.token_svc = current_app.token_svc
        request.db = current_app.db
        request.log = current_app.log

    @staticmethod
    def __init_handler():
        """ This function is registered as a "before_request" callback and
            handles checking the request authentication. It also posts various
            parts of the app context into the request proxy object for ease of
            use.
        """
        req_uuid = uuid.uuid4()
        request.uuid = req_uuid
        req_ip = request.remote_addr
        current_app.log.debug("New request with UUID: %s (%s)",
                              req_uuid, req_ip)
        # Requests for static content don't have authentication
        if request.path.startswith('/static/'):
            return # Allow access
        # Fast handling of 404 errors (also avoids 403 default code if page
        # is not found.
        if not request.url_rule:
            return "404 Not Found", 404
        # Process all other requests with ACL manager
        current_app.acl_manager.check_request()
        FlaskServer.__extend_request()

    @staticmethod
    def __access_log(resp):
        """ This function writes to the access log, to log the request details
            and the return code.
        """
        req_ip = request.remote_addr
        req_uuid = request.uuid
        method = request.method
        uri = request.url
        status_code = resp.status_code
        resp_len = resp.content_length
        current_app.log.info("%s: %s %s %s %s %u", req_uuid, req_ip,
                             method, uri, status_code, resp_len)
        return resp

    def __update_dbctx(self, dbobj):
        """ Updates this objects database object within the application context.
            dbobj - The new database object (should be an instance of SQLAlchemy()
            Returns None.
        """
        self.__db = dbobj
        with self.app_context():
            current_app.db = dbobj

    def __add_tables(self):
        """ Creates a new DBContainer within the database object
            (as db.tables) and attaches all currently pending tables to it.
            Returns None.
        """
        self.__db.tables = DBContainer()
        #pylint: disable=protected-access
        registry = self.__db.Model._decl_class_registry
        for tbl_name, tbl_inst in registry.iteritems():
            if hasattr(tbl_inst, '__tablename__'):
                setattr(self.__db.tables, tbl_name, tbl_inst)

    def __init__(self, server_name, logger=logging.getLogger(),
                 debug=False, token_key=None):
        """ Constructs the server.
            logger - The main logger to use.
            debug - If set to true, enable flask debug mode
                    (Which includes far more details in returned errors, etc...)
        """
        Flask.__init__(self, server_name)
        self.debug = debug
        self.before_request(self.__init_handler)
        self.after_request(self.__access_log)
        self.__acl_manager = ACLManager(logger)
        self.__update_dbctx(None)
        self.__db_classes = []
        self.__db_insts = []
        self.__startup_funcs = []
        self.__test_funcs = []
        self.__logger = logger
        if not token_key:
            token_key = os.urandom(16)
        self.secret_key = token_key + "flask"
        self.token_svc = TokenService(token_key, "pdmwebsvc")
        # We override the test client class from Flask with our
        # custom one which is more similar to RESTClient
        self.test_client_class = FlaskClientWrapper
        with self.app_context():
            current_app.log = logger
            current_app.acl_manager = self.__acl_manager
            current_app.token_svc = self.token_svc

    def enable_db(self, db_uri):
        """ Enables a database connection pool for this server.
            db_uri - An SQLAlchemy compliant Db conection string.
            Should be called before any calls to attach_obj.
            Returns None.
        """
        self.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        database = MemSafeSQLAlchemy(self)
        self.__update_dbctx(database)

    def build_db(self):
        """ Creates a database using all registered db_models.
            Returns None.
        """
        with self.app_context():
            if self.__db:
                for cls in self.__db_classes:
                    self.__db_insts.append(cls(self.__db.Model))
                    # We have to add the tables class-by-class
                    # Some versions of Flask-SQLalchemy clear the
                    # _decl_class_registry every time a new model class is
                    # loaded (which causes tables to go missing otherwise).
                    self.__add_tables()
                self.__db.create_all()

    def before_startup(self, config, with_test=False):
        """ This function calls any functions registered with the @startup
            constructor. This should be called immediately before starting
            the main request loop. The config parmemter is passed through
            to the registered functions, it should be a dictionary of
            config parameters.
            with_test is a boolean, if true @startup_test functions will
            also be run. These are for populating the DB with test data.
            Returns None.
        """
        with self.app_context():
            for func in self.__startup_funcs:
                func(config)
            if with_test:
                for func in self.__test_funcs:
                    func()

    def attach_obj(self, obj_inst, root_path='/',
                   parent_name=None, parent_redir=None):
        """ Attaches an object tree to this web service.
            For each exported object, it is attached to the path tree and
            then all of its children are checked for the exported flag.
            obj_inst - The root object to start scanning.
            root_path - The base path to start attaching relative paths from.
            parent_name - Optinal prefix to give registered endpoints.
                          (Used to prevent duplicate entries between classes).
            parent_redir - Optional URL to use for 403 redirects (auth denied)
                           to inherit from parent.
            Returns None.
        """
        if hasattr(obj_inst, 'is_exported'):
            for ename, methods, redir in obj_inst.exportables:
                if not redir:
                    redir = parent_redir
                obj_path = os.path.join(root_path, ename)
                if not callable(obj_inst):
                    self.__logger.debug("Class %s at %s", obj_inst, obj_path)
                    if hasattr(obj_inst, 'db_model'):
                        self.__logger.debug("Extending DB model: %s",
                                            obj_inst.db_model)
                        self.__db_classes.extend(obj_inst.db_model)
                    items = [x for x in dir(obj_inst) if not x.startswith('_')]
                    for obj_item in [getattr(obj_inst, x) for x in items]:
                        cls_name = type(obj_inst).__name__
                        self.attach_obj(obj_item, obj_path, cls_name, redir)
                else:
                    self.__logger.debug("Attaching %s at %s", obj_inst, obj_path)
                    endpoint = obj_inst.__name__
                    if parent_name:
                        endpoint = "%s.%s" % (parent_name, endpoint)
                    obj_inst.export_redir = redir
                    self.add_url_rule(obj_path, endpoint, obj_inst,
                                      methods=methods)
        elif hasattr(obj_inst, 'is_startup'):
            if obj_inst.is_startup:
                self.__startup_funcs.append(obj_inst)
        elif hasattr(obj_inst, 'is_test_func'):
            if obj_inst.is_test_func:
                self.__test_funcs.append(obj_inst)

    def add_auth_groups(self, groups):
        """ Adds groups to the web server.
            groups - A dictionary of groups, key is the group
                     name, value is a list of auth entries.
            Returns None
        """
        for group, entries in groups.iteritems():
            for entry in entries:
                self.__acl_manager.add_group_entry(group, entry)

    def add_auth_rules(self, auth_rules):
        """ Adds authentication rules to the web server.
            auth_rules - A dictionary of rules, keys are URI paths,
                         values are a rule statement:
                          - "CERT" - Any valid client cert is allowed.
                          - "CERT:/some/dn" - Allow a specific CERT.
                          - "TOKEN" - Any valid token is allowed.
                          - "SESSION" - Requests a logged_in web session.
                          - "ALL" - All requests are allowed.
            By default no-one can call any function.
            Returns None.
        """
        for path, rule in auth_rules.iteritems():
            self.__acl_manager.add_rule(path, rule)

    def test_mode(self, main_cls, conf="", with_test=True):
        """ Configures this app instance in test mode.
            An in-memory Sqlite database is used for the DB.
            main_cls is the class to use for endpoints.
            conf is a dictionary to pass as config for startup methods.
            If all parameters in conf arne't used an assertion error is
            thrown.
            If conf is set to None, the build_db and before_startup functions
            are not called (and should be called manually).
            The with_test flag sets whether to call the service @startup_test
            functions or not.
            Returns None.
        """
        if not conf and conf is not None:
            # Specfiying conf={} as default parameter is unsafe
            # Instead we use a string and change it to a dict here.
            conf = {}
        inst = main_cls()
        self.enable_db("sqlite:///")
        self.attach_obj(inst)
        # Put flask into test mode
        # This causes exceptions to pass to the client directly
        self.testing = True
        if conf is not None:
            self.build_db()
            self.before_startup(conf, with_test=with_test)
            # Config should have been completely consumed
            assert not conf

    def test_db(self):
        """ Gets an instance to the internal DB object.
            This allows a test instance to modify the database directly.
            Should not be used outside of test cases.
        """
        return self.__db

    def fake_auth(self, auth_mode, auth_data=None):
        """ Sets the auth mode for all endpoints.
            auth_mode is the mode to pretend was used.
            auth_data is mode specific.

            auth_mode should be one of the following:
            None - No auth data (auth_data must = None)
            "CERT" - auth_data should be a DN.
            "TOKEN" - auth_data should be a json encoded token.
            "SESSION" - auth_data should be none.
            "ALL" - No auth, all request anyway.
        """
        if not auth_mode:
            self.__acl_manager.test_mode(ACLManager.AUTH_MODE_NONE)
            return
        if auth_mode == "CERT":
            self.__acl_manager.test_mode(ACLManager.AUTH_MODE_X509, auth_data)
        elif auth_mode == "TOKEN":
            self.__acl_manager.test_mode(ACLManager.AUTH_MODE_TOKEN, auth_data)
        elif auth_mode == "SESSION":
            self.__acl_manager.test_mode(ACLManager.AUTH_MODE_SESSION, None)
        else:
            self.__acl_manager.test_mode(ACLManager.AUTH_MODE_ALLOW_ALL)
