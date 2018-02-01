#!/usr/bin/env python
""" Test RESTClient framework module. """

import mock
import unittest

from pdm.framework.RESTClient import RESTClient

class TestRESTClient(unittest.TestCase):
    """ Test the RESTClient class. """

    @mock.patch("pdm.framework.RESTClient.ConfigSystem")
    def __get_inst(self, conf_dict, mock_conf, **kwargs):
        """ Gets an instance of RESTClient preconfigured with the provided
            conf_dict.
        """
        mock_conf_inst = mock.MagicMock()
        mock_conf.get_instance.return_value = mock_conf_inst
        real_conf = {'testsvc': conf_dict}
        mock_conf_inst.get_section.return_value = real_conf
        return RESTClient('testsvc', **kwargs)

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_get(self, mock_req):
        """ Test HTTP GET verb. """
        client = self.__get_inst({})
        client.get("/test_url")
        mock_req.assert_called_with("/test_url", "GET")

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_post(self, mock_req):
        """ Test HTTP POST verb. """
        client = self.__get_inst({})
        client.post("/test_url", "POSTDATA")
        mock_req.assert_called_with("/test_url", "POST", "POSTDATA")

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_delete(self, mock_req):
        """ Test HTTP DELETE verb. """
        client = self.__get_inst({})
        client.delete("/test_url")
        mock_req.assert_called_with("/test_url", "DELETE")

    # TODO: Test all calls of __do_request

# TODO: Test Test Class!
