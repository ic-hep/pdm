#!/usr/bin/env python
""" RESTful client tools.
"""

import json
import mock
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

    def set_token(self, token):
        """ Set the token to use for future requests.
            Returns None.
        """
        self.__token = token

    def __do_request(self, uri, method, data=None):
        """ Run a request on te server
            Returns object from the server.
        """
        # TODO: Better way to join URLs?
        full_url = "%s/%s" % (self.__url, uri)
        cafile, cert, key = self.__ssl_opts
        client_cert = None
        if cert and key:
            client_cert = (cert, key)
        # Handle headers
        headers = {}
        if self.__token:
            headers['X-Token'] = self.__token
        # Actually send the request
        resp = requests.request(method, full_url, json=data, headers=headers,
                                verify=cafile, cert=client_cert)
        if resp.status_code != requests.codes.ok:
            # TODO: Better excpetions here
            raise Exception("Request failed with code %u" % resp.status_code)
        if resp.text:
            return resp.json()
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


class RESTClientTest(object):
    """ A mock version of RESTClient which calls a local
        Flask test_client instance instead.
        Useful for doing unit testing, use patch_client to get
        a preconfigured instance.
    """

    @staticmethod
    def patch_client(target, test_client, base_uri='/'):
        """ Creates an instance of the given class, but replaces the
            RESTClient interface with RESTClientTest instead, which allows
            a local Flask test_client to be called directly.
            target - The target class to create an instance off (should 
                     inherit from only RESTClient).
            test_client - The test_client object from the Flask service.
            base_uri - The base_uri of the service.
            Returns a tuple of (patcher, client) -
                    patcher is a mock patch object, which should be stopped at
                            the end of testing with patcher.stop().
                    client is a patched instance of target class.
        """
        # We patch away the base class of the target, replacing it with
        # RESTClientTest instead.
        patcher = mock.patch.object(target, '__bases__', (RESTClientTest, ))
        patcher.start()
        # is_local is required to prevent mock from attempting to delete
        # __bases__ when stop is called (which would throw an exception)
        patcher.is_local = True
        client = target()
        client.set_test_info(test_client, base_uri)
        return (patcher, client)

    def __init__(self, service):
        """ Create a new instance of RESTClientTest, service parameter is
            ignored.
        """
        self.__tc = None
        self.__base = None

    def __do_call(self, call_fn, uri, data=None):
        """ Call a test_client function with the given parameters
            and process the result in a similar way to RESTClient.
        """
        full_uri = "%s/%s" % (self.__base, uri)
        res = call_fn(full_uri, data=json.dumps(data))
        if res.status_code != 200:
            raise Exception("Request failed with code %u" % res.status_code)
        if res.data:
            return json.loads(res.data)
        return None

    def get(self, uri):
        """ Get URI on test_client interface. """
        return self.__do_call(self.__tc.get, uri)

    def post(self, uri, data):
        """ Post data to URI on test_client interface. """
        return self.__do_call(self.__tc.post, uri, data)

    def delete(self, uri):
        """ Delete URI on test_client interface. """
        return self.__do_call(self.__tc.delete, uri)

    def set_test_info(self, test_client, base_uri):
        """ Set the test_client instance and base_uri
            to use when making calls via this object.
            Returns None.
        """
        self.__tc = test_client
        self.__base = base_uri
