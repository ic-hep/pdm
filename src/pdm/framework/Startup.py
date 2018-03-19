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

    # The section name for the default app configuration
    DEF_APP_CONF = "server/DEFAULT"

    def __init__(self):
        """ Prepares the argument parser. """
        self.__wsgi_server = None
        self.__conf_base = ""
        self.__debug = False
        self.__test = False
        self.__parser = ArgumentParser()
        self.__parser.add_argument("conf", help="Server config file")
        self.__parser.add_argument("--debug", "-d", action='store_true',
                                   help="Debug mode: Don't fork")
        self.__parser.add_argument("--test", "-t", action='store_true',
                                   help="Start the service with test data")
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
        auth_groups = config.get_section("groups")
        auth_rules = config.get_section("auth/%s" % app_name)
        print "AUTH RULES for %s: %s" % (app_name, auth_rules)
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
        """ Creates instances of all WSGI apps defined in the config. """
        auth_conf = self.__fix_path(config.pop("auth"))
        auth_pol = self.__load_auth(app_name, auth_conf)
        app_server.add_auth_rules(auth_pol)
        app_class = config.pop("class")
        try:
            app_inst = pydoc.locate(app_class)()
            app_server.attach_obj(app_inst)
        except pydoc.ErrorDuringImport as err:
            # We failed to import the client app, we need to raise the inner
            # exception to make debugging easier
            raise err.exc, err.value, err.tb
        app_server.build_db()
        app_server.before_startup(config, with_test=self.__test)
        # Test if there are any unused keys in the dictionary
        if config:
            # There are => Unused items = typos?
            keys = ', '.join(config.keys())
            raise ValueError("Unused config params: '%s'" % keys)

    def __init_wsgi(self, wsgi_name, config):
        """ Creates an instance of FlaskServer, opens a port and configures
            the base server to run requests on the FlaskServer using WSGI.
            wsgi_name - the config name of the WSGI server.
            config - The main application config object.
            Returns None.
        """
        wsgi_config = config.get_section(self.DEF_APP_CONF)
        wsgi_config.update(config.get_section(wsgi_name))
        port = wsgi_config.pop("port")
        cafile = self.__fix_path(wsgi_config.pop("cafile"))
        cert = self.__fix_path(wsgi_config.pop("cert"))
        key = self.__fix_path(wsgi_config.pop("key"))
        secret = wsgi_config.pop("secret")
        # Create Flask server & config basics
        logger = logging.getLogger()
        log_file = wsgi_config.pop("log")
        # TODO: Write log to log_file in non-debug mode
        server_name = wsgi_config.pop("static", wsgi_name)
        app_server = FlaskServer(server_name, logger, self.__debug, secret)
        db_uri = wsgi_config.pop("db", None)
        if db_uri:
            app_server.enable_db(db_uri)
        # Create child app instance
        app_name = wsgi_name.split("/")[1]
        self.__init_app(app_server, app_name, wsgi_config)
        self.__wsgi_server.add_server(port, app_server, cert, key, cafile)

    def run(self):
        """ Process the command line arguments and start this server
            (optionally as a daemon).
            Returns None.
        """
        # Handle command-line args
        args = self.__parser.parse_args()
        self.__debug = args.debug
        self.__test = args.test
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
        # Make sure we don't treat defaults as an actual server
        if self.DEF_APP_CONF in wsgi_names:
            wsgi_names.remove(self.DEF_APP_CONF)
        for wsgi_name in wsgi_names:
            self.__init_wsgi(wsgi_name, config)
        # Actually start the service
        # TODO: Daemon this
        self.__wsgi_server.run()
