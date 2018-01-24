#!/usr/bin/env python
""" Objects for server start-up.
    Starts a development WSGI server based on a config file.
"""
from __future__ import print_function

import os
import pydoc
import logging
from argparse import ArgumentParser

from pdm.utils.daemon import Daemon
from pdm.utils.config import ConfigSystem
from pdm.framework.WSGIServer import WSGIServer
from pdm.framework.FlaskWrapper import FlaskServer


class ExecutableServer(object):
  """ A base object for starting a WSGI+Flask debug server.
  """

  def __init__(self):
    """ Prepares the argument parser. """
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

  def __init_app(self, app_server, app_name, config):
    """ Initialise an end application from the config.
        app_server - An instance of FlaskServer to attach the loaded
                     application to.
        app_name - The config name of this server.
        config - Application config object.
        Returns None.
    """
    app_config = config.get_section("app/%s" % app_name)
    app_class = app_config.pop("class")
    try:
      app_inst = pydoc.locate(app_class)()
    except pydoc.ErrorDuringImport as err:
      # We failed to import the client app, we need to raise the inner
      # exception to make debugging easier
      raise err.exc, err.value, err.tb
    app_server.attach_obj(app_inst)
    app_server.before_startup(app_config)
    # Test if there are any unused keys in the dictionary
    if app_config:
      # There are => Unused items = typos?
      keys = ', '.join(app_config.keys())
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
    # Create Flask server & config basics
    logger = logging.getLogger()
    app_server = FlaskServer(logger, self.__debug)
    db_uri = wsgi_config.get("db", None)
    if db_uri:
      app_server.enable_db(db_uri)
    # Create child app instances
    app_names = wsgi_config.get("apps", [])
    for app_name in app_names:
      self.__init_app(app_server, app_name, config)
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
    logging.basicConfig()
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
    return
