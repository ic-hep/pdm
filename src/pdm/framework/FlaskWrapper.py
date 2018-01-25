#!/usr/bin/env python
""" A wrapper around Flask that provides application specific
    authentication, logging and database services.
"""

import os
import json
import functools

from pdm.framework.Tokens import TokenService

from flask import Flask, Response, current_app, request

# This has to be imported last or database tables aren't found
# TODO: Work out why this happens.
from pdm.framework.Database import MemSafeSQAlchemy


def export_inner(obj, ename, methods=None):
    """ Inner function for export decorators.
        Obj is the object to export,
        See the export_ext function for further more details on the other
        parameters.
    """
    if not methods:
        methods = ["GET"]
    obj.is_exported = True
    obj.export_name = ename
    obj.export_methods = methods
    obj.export_auth = []
    return obj

def export(obj):
    """ Class/Function decorator.
        Export a class or function via the GET method on the web-server.
        The export name will be the __name__ value of the object.
    """
    return export_inner(obj, obj.__name__)

def export_ext(ename, methods=None):
    """ Class/Function decorator.
        Export a class or function via the web-server with extra options.
        ename - Export name of the item. This may be a relative name to inherit
                from the parent object, or absolute for an absolute path on the
                webserver.
        methods - A list of flask-style method names, i.e. ["GET", "POST"]
                  to allow access to this object. Defaults to GET only if set
                  to None.
    """
    return functools.partial(export_inner, ename=ename, methods=methods)

def startup(obj):
    """ Funciton decorator.
        Marks a function to be called at start-up on the webserver.
        The function will be called at the end of daemonisation before
        requests are accepted. The function is run in the application context
        (so flask.current_app is available, but not flask.request).
        The function should take a single parameter, which will recieve a
        dictionary of config options from the config file. If the application
        uses any keys, they should be removed from the dictionary.
    """
    obj.is_startup = True
    return obj

def db_model(db_obj):
    """ Attaches a non-instantiated class as the database model for this class.
        The annotated class should be exported with the export decorator.
        The database class should have an __init__ which takes a single model
        parameter. All database classes should be defined within __init__ and
        use the model parameter as the base class.
    """
    def attach_db(obj):
        """ Attches the db_obj to the db_model parameter of obj.
            Returns obj.
        """
        obj.db_model = db_obj
        return obj
    return attach_db

def jsonify(obj):
    """ Works just like Flask's jsonify method, but doesn't care about the
        input type.
        Returns a Flask response object.
    """
    return Response(json.dumps(obj), mimetype='application/json')

#pylint: disable=too-few-public-methods
class DBContainer(object):
    """ A container of DB Table models.
        References to the table objects are dynamitcally attached to an instance
        of this object at runtime.
    """
    pass

class FlaskServer(Flask):
    """ A wrapper around a flask application server providing additional
        configuration & runtime helpers.
    """

    @staticmethod
    def __check_req(resource, client_dn, client_token):
        """ Checks the request for resource against the current_app.policy.
            Returns True if the request should be allowed.
                    False if the request should be denied.
        """
        rules = current_app.policy.get(resource, [])
        for rule in rules:
            if rule == 'ALL':
                return True
            if rule == 'ANY' and (client_dn or client_token):
                return True
            if rule == 'TOKEN' and client_token:
                return True
            if rule == 'CERT' and client_dn:
                return True
            if rule.startswith('CERT:'):
                _, check_dn = rule.split(':', 1)
                if client_dn == check_dn:
                    return True
        # No rules matched => Access denied
        return False

    @staticmethod
    def __req_allowed(client_dn, client_token):
        if request.url_rule:
            real_path = request.url_rule.rule.split('<')[0]
        else:
            real_path = request.path
        if real_path.endswith('/'):
            real_path = real_path[:-1]
        resource = "%s%%%s" % (real_path, request.method)
        if not resource in current_app.policy:
            # No specific rule exists for this path + method
            # Try the "methodless" rule
            resource = real_path
        return FlaskServer.__check_req(resource, client_dn, client_token)

    @staticmethod
    def __init_handler():
        """ This function is registered as a "before_request" callback and
            handles checking the request authentication. It also posts various
            parts of the app context into the request proxy object for ease of
            use.
        """
        client_dn = None
        client_token = False
        token_value = None
        if 'Ssl-Client-Verify' in request.headers \
            and 'Ssl-Client-S-Dn' in request.headers:
            # Request has client cert
            if request.headers['Ssl-Client-Verify'] == 'SUCCESS':
                client_dn = request.headers['Ssl-Client-S-Dn']
        if 'X-Token' in request.headers:
            raw_token = request.headers['X-Token']
            res, token_value = current_app.token_svc.check(raw_token)
            if res:
                return "403 Invalid Token", 403
            client_token = True
        # Now check request against policy
        if not FlaskServer.__req_allowed(client_dn, client_token):
            return "403 Forbidden\n", 403
        # Finally, update request object
        request.dn = client_dn
        request.token_ok = client_token
        if client_token:
            request.token = token_value
        else:
            request.token = None
        request.token_svc = current_app.token_svc
        request.db = current_app.db
        request.log = current_app.log

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

    def __init__(self, server_name, logger, debug=False, token_key=None):
        """ Constructs the server.
            logger - The main logger to use.
            debug - If set to true, enable flask debug mode
                    (Which includes far more details in returned errors, etc...)
        """
        Flask.__init__(self, server_name)
        self.debug = debug
        self.before_request(self.__init_handler)
        self.__update_dbctx(None)
        self.__startup_funcs = []
        self.__logger = logger
        self.__token_svc = TokenService(token_key, server_name)
        with self.app_context():
            current_app.log = logger
            current_app.policy = {}
            current_app.token_svc = self.__token_svc

    def enable_db(self, db_uri):
        """ Enables a database connection pool for this server.
            db_uri - An SQLAlchemy compliant Db conection string.
            Should be called before any calls to attach_obj.
            Returns None.
        """
        self.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        self.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        database = MemSafeSQAlchemy(self)
        self.__update_dbctx(database)

    def before_startup(self, config):
        """ This function calls creates the database (if enabled) and calls
            any functions registered with the @startup constructor.
            This should be called immediately before starting the main request
            loop.
            The config parmemter is passed through to the registered functions,
            it should be a dictionary of config parameters.
            Returns None.
        """
        with self.app_context():
            if self.__db:
                self.__add_tables()
                self.__db.create_all()
            for func in self.__startup_funcs:
                func(config)

    def attach_obj(self, obj_inst, root_path='/'):
        """ Attaches an object tree to this web service.
            For each exported object, it is attached to the path tree and
            then all of its children are checked for the exported flag.
            obj_inst - The root object to start scanning.
            root_path - The base path to start attaching relative paths from.
            Returns None.
        """
        if hasattr(obj_inst, 'is_exported'):
            ename = obj_inst.export_name
            obj_path = os.path.join(root_path, ename)
            if not callable(obj_inst):
                self.__logger.debug("Class %s at %s", obj_inst, obj_path)
                if hasattr(obj_inst, 'db_model'):
                    self.__logger.debug("Extending DB model: %s",
                                        obj_inst.db_model)
                    obj_inst.db_model(self.__db.Model)
                items = [x for x in dir(obj_inst) if not x.startswith('_')]
                for obj_item in [getattr(obj_inst, x) for x in items]:
                    self.attach_obj(obj_item, obj_path)
            else:
                self.__logger.debug("Attaching %s at %s", obj_inst, obj_path)
                endpoint = obj_inst.__name__
                self.add_url_rule(obj_path, endpoint, obj_inst,
                                  methods=obj_inst.export_methods)
        elif hasattr(obj_inst, 'is_startup'):
            if obj_inst.is_startup:
                self.__startup_funcs.append(obj_inst)

    @staticmethod
    def __check_rule(auth_rule):
        """ Checks that an auth_rule is valid.
            (See valid rules in add_auth_rules function).
            Returns True if rule is valid, False otherwise.
        """
        if auth_rule in ('CERT', 'TOKEN', 'ALL', 'ANY'):
            return True
        if auth_rule.startswith('CERT:') and len(auth_rule) > 5:
            return True
        return False

    def add_auth_rules(self, auth_rules):
        """ Adds authentication rules to the web server.
            auth_rules - A dictionary of rules, keys are URI paths,
                         values are lists of rule statements:
                          - "CERT" - Any valid client cert is allowed.
                          - "CERT:/some/dn" - Allow a specific CERT.
                          - "TOKEN" - Any valid token is allowed.
                          - "ANY" - Any valid credential is allowed.
                          - "ALL" - All requests are allowed.
            By default no-one can call any function.
            Returns None.
        """
        for path, rules in auth_rules.iteritems():
            for rule in rules:
                if not self.__check_rule(rule):
                    raise ValueError("Rule '%s' for '%s' is invalid." % (rule, path))
        with self.app_context():
            current_app.policy.update(auth_rules)
