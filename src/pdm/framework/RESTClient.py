#!/usr/bin/env python

import requests

from pdm.utils.config import ConfigSystem


class RESTClient(object):
  """ A REST client base class. """

  def __locate(self, service):
    """ Returns the URL (endpoint) for a given service.
    """
    endpoints = self.__conf.get_section("endpoints")
    if not service in endpoints:
      raise KeyError("Failed to find endpoint for service '%s'" % service)
    return endpoints[service]

  def __get_ssl_opts(self, ssl_opts):
    """ Gets config file ssl_opts.
    """
    if not ssl_opts:
      # No SSL client options, try config file
      client_conf = self.__conf.get_section("client")
      cafile = client_conf.pop("cafile", None)
      cert = client_conf.pop("cert", None)
      key = client_conf.pop("key", None)
      ssl_opts = (cafile, cert, key)
    return ssl_opts

  def __init__(self, service, ssl_opts=None, token=None):
    """ Initialise a client for a given service.
        service - The common name of the service to contact.
        ssl_opts - Optional tuple of (cafile, cert, key)
                   For SSL with no client cert, leave cert & key
                   as None.
        token - Optional token to include in the requests.
    """
    self.__conf = ConfigSystem.get_instance()
    self.__url = self.__locate(service)
    self.__ssl_opts = self.__get_ssl_opts(ssl_opts)
    self.__token = token
    self.__session = requests.Session()

  def __do_request(self, uri, method, data=None):
    """ Run a request on te server
        Returns object from the server.
    """
    # TODO: Better way to join URLs?
    full_url = "%s/%s" % (self.__url, uri)
    cafile, cert, key = self.__ssl_opts
    if cert and key:
      client_cert = (cert,key)
    resp = requests.request(method, full_url, json=data,
                            verify=cafile, cert=client_cert)
    if resp.text:
      return resp.json()
    else:
      return None

  def get(self, uri):
    """ Perform a GET request on the given URI. """
    return self.__do_request(uri, 'GET')

  def post(self, uri, data):
    """ Perform a POST request on the given URI. """
    return self.__do_request(uri, 'POST', data)

  def delete(self, uri):
    """ Perform a DELETE request on the given URI. """
    return self.__do_request(uri, 'DELETE')
