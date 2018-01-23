#!/usr/bin/env python
""" Objects for server start-up.
    Starts a development WSGI server based on a config file.
"""
from __future__ import print_function

import os
import sys
from argparse import ArgumentParser
from pydoc import locate

from pdm.utils.daemon import Daemon
from pdm.utils.config import ConfigSystem
from pdm.framework.WSGIServer import WSGIServer
from pdm.framework.FlaskWrapper import FlaskServer


class ExecutableServer(object):
  """ A base object for starting a WSGI+Flask debug server.
  """

  def __init__(self):
    self.__parser = ArgumentParser()
    self.__parser.add_argument("conf", help="Server config file")
    self.__parser.add_argument("--debug", "-d", action='store_true',
                               help="Debug mode: Don't fork")
    self.__parser.add_argument("--log", "-l",
                               help="Log file name (defaults to stdout)")

  def __fix_path(self, path):
    return os.path.join(self.__conf_base, path)

  def __init_app(self, app_server, app_name, config):
    app_config = config.get_section("app/%s" % app_name)
    if "db" in app_config:
      app_server.enable_db(app_config['db'])
    # TODO: locate doesn't generate easy-to-find exceptions on import errors
    app_inst = locate(app_config["class"])()
    app_server.attach_obj(app_inst)
    app_server.before_startup()

  def __init_wsgi(self, wsgi_name, config):
    wsgi_config = config.get_section(wsgi_name)
    port = wsgi_config["port"]
    cafile = self.__fix_path(wsgi_config.get("cafile", None))
    cert = self.__fix_path(wsgi_config.get("cert", None))
    key = self.__fix_path(wsgi_config.get("key", None))
    app_names = wsgi_config.get("apps", [])
    # Create child flask instances
    app_server = FlaskServer()
    for app_name in app_names:
      self.__init_app(app_server, app_name, config)
    self.__wsgi_server.add_server(port, app_server, cert, key, cafile)

  def run(self):
    # Handle command-line args
    args = self.__parser.parse_args()
    self.__conf_base = os.path.dirname(args.conf)
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

