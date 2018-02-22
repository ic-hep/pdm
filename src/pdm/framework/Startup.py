#!/usr/bin/env python
""" Objects for server start-up.
    Starts a development WSGI server based on a config file.
"""
import os
import pydoc
import logging
from argparse import ArgumentParser

from pdm.utils.config import ConfigSystem
from pdm.framework.WSGIServer import WSGIServer
from pdm.framework.FlaskWrapper import FlaskServer


#pylint: disable=too-few-public-methods
class ExecutableServer(object):
    """ A base object for starting a WSGI+Flask debug server.
    """

    def __init__(self):
        """ Prepares the argument parser. """
        self.__wsgi_server = None
        self.__conf_base = ""
        self.__debug = False
        self.__parser = ArgumentParser()
        self.__parser.add_argument("conf", help="Server config file")
        self.__parser.add_argument("--debug", "-d", action='store_true',
                                   help="Debug mode: Don't fork")
        self.__parser.add_argument("--log", "-l",
                                   help="Log file name (defaults to stdout)")

    def __fix_path(self, path):
        """ Convert a relative path to be rooted from the config directory
            of this server.
        """
        return os.path.join(self.__conf_base, path)

    @staticmethod
    def __load_auth(app_name, auth_conf):
        """ Loads the authentication config for a given app.
            app_name - The config name of the app to load auth for.
            auth_conf - Path to the auth config file (may be relative to the
                        config dir).
            Returns a dictionary of paths => list(auth rule strings)
        """
        config = ConfigSystem.get_instance()
        config.setup(auth_conf)
        auth_groups = config.get_section("groups/%s" % app_name)
        auth_rules = config.get_section("auth/%s" % app_name)
        auth_policy = {}
        for uri, conf_rules in auth_rules.iteritems():
            auth_rules = []
            if isinstance(conf_rules, str):
                conf_rules = [conf_rules]
            for rule in conf_rules:
                if rule.startswith('@'):
                    # Rule is a group
                    auth_rules.extend(auth_groups[rule[1:]])
                else:
                    auth_rules.append(rule)
            auth_policy[uri] = auth_rules
        return auth_policy

    def __init_app(self, app_server, app_name, config):
        """ Initialise an end application from the config.
            app_server - An instance of FlaskServer to attach the loaded
                         application to.
            app_name - The config name of this server.
            config - Application config object.
            Returns None.
        """
        app_config = config.get_section("app/%s" % app_name)
        auth_conf = self.__fix_path(app_config.pop("auth"))
        auth_pol = self.__load_auth(app_name, auth_conf)
        app_server.add_auth_rules(auth_pol)
        app_class = app_config.pop("class")
        try:
            app_inst = pydoc.locate(app_class)()
            app_server.attach_obj(app_inst)
        except pydoc.ErrorDuringImport as err:
            # We failed to import the client app, we need to raise the inner
            # exception to make debugging easier
            raise err.exc, err.value, err.tb
        return app_inst

    def __config_app(self, app_server, app_name, config):
        app_config = config.get_section("app/%s" % app_name)
        # Remove sections used in __init_app.
        app_config.pop("auth", None)
        app_config.pop("class", None)
        app_server.before_startup(app_config)
        # Test if there are any unused keys in the dictionary
        if app_config:
            # There are => Unused items = typos?
            keys = ', '.join(app_config.keys())
            raise ValueError("Unused config params for %s: '%s'" % (app_name, keys))

    def __init_apps(self, app_server, app_names, config):
        """ Creates instances of all WSGI apps defined in the config. """
        all_config = {}
        for app_name in app_names:
            app_config = config.get_section("app/%s" % app_name)
            auth_conf = self.__fix_path(app_config.pop("auth"))
            auth_pol = self.__load_auth(app_name, auth_conf)
            app_server.add_auth_rules(auth_pol)
            app_class = app_config.pop("class")
            try:
                app_inst = pydoc.locate(app_class)()
                app_server.attach_obj(app_inst)
            except pydoc.ErrorDuringImport as err:
                # We failed to import the client app, we need to raise the inner
                # exception to make debugging easier
                raise err.exc, err.value, err.tb
            all_config.update(app_config)
        app_server.build_db()
        app_server.before_startup(all_config)
        # Test if there are any unused keys in the dictionary
        if all_config:
            # There are => Unused items = typos?
            keys = ', '.join(all_config.keys())
            raise ValueError("Unused config params for %s: '%s'" % (app_name, keys))

    def __init_wsgi(self, wsgi_name, config):
        """ Creates an instance of FlaskServer, opens a port and configures
            the base server to run requests on the FlaskServer using WSGI.
            wsgi_name - the config name of the WSGI server.
            config - The main application config object.
            Returns None.
        """
        wsgi_config = config.get_section(wsgi_name)
        port = wsgi_config["port"]
        cafile = self.__fix_path(wsgi_config.get("cafile", None))
        cert = self.__fix_path(wsgi_config.get("cert", None))
        key = self.__fix_path(wsgi_config.get("key", None))
        secret = wsgi_config.get("secret", None)
        # Create Flask server & config basics
        logger = logging.getLogger()
        server_name = wsgi_config.get("static", wsgi_name)
        app_server = FlaskServer(server_name, logger, self.__debug, secret)
        db_uri = wsgi_config.get("db", None)
        if db_uri:
            app_server.enable_db(db_uri)
        # Create child app instances
        app_names = wsgi_config.get("apps", [])
        self.__init_apps(app_server, app_names, config)
        self.__wsgi_server.add_server(port, app_server, cert, key, cafile)

    def run(self):
        """ Process the command line arguments and start this server
            (optionally as a daemon).
            Returns None.
        """
        # Handle command-line args
        args = self.__parser.parse_args()
        self.__debug = args.debug
        self.__conf_base = os.path.dirname(args.conf)
        # Enabling logging
        if self.__debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        # Load config file
        config = ConfigSystem.get_instance()
        config.setup(args.conf)
        # Create WSGI server instances
        self.__wsgi_server = WSGIServer()
        wsgi_names = [x for x in config.sections if x.startswith('server/')]
        for wsgi_name in wsgi_names:
            self.__init_wsgi(wsgi_name, config)
        # Actually start the service
        # TODO: Daemon this
        self.__wsgi_server.run()
