#!/usr/bin/env python
""" Test RESTClient framework module. """

import json
import mock
import unittest
import functools

from pdm.framework.RESTClient import RESTClient, RESTClientTest

class TestRESTClient(unittest.TestCase):
    """ Test the RESTClient class. """

    def __get_inst(self, base_url="", client_conf={}, broken=False, **kwargs):
        """ Gets an instance of RESTClient preconfigured with the provided
            base_url.
            client_conf allows a client config to be configured.
            If broken=True, then the wrong service name is provied to the
            constructor.
        """
        def mock_get_section(section_name):
            if section_name == 'endpoints':
                return {'testsvc': base_url}
            if section_name == 'client':
                return client_conf
            raise KeyError("Unknown key: %s" % section_name)
        with mock.patch("pdm.framework.RESTClient.ConfigSystem") as mock_conf:
            mock_conf_inst = mock.MagicMock()
            mock_conf.get_instance.return_value = mock_conf_inst
            mock_conf_inst.get_section.side_effect = mock_get_section
            if broken:
                # Deliberately get the wrong client name, so config isn't found
                # for testing that error code path
                return RESTClient('wrongsvc', **kwargs)
            else:
                return RESTClient('testsvc', **kwargs)

    def __mock_req(self, mock_req, ret_code, ret_value, is_obj=True):
        """ Configures mocked requests library (mock_req)
            to pretent the request returned ret_code status with
            ret_text data.
            If is_obj is true, the object will be serialised to JSON.
            otherwise the value is used as-is.
        """
        def ret_json(input_text):
            return json.loads(input_text)
        mock_resp = mock.MagicMock()
        mock_resp.status_code = ret_code
        if is_obj:
            mock_resp.text = json.dumps(ret_value)
            mock_resp.json.return_value = ret_value
        else:
            mock_resp.text = ret_value
            mock_resp.json.side_effect = functools.partial(ret_json,
                                                           ret_value)
        mock_req.request.return_value = mock_resp
        mock_req.codes = mock.Mock()
        mock_req.codes.ok = 200
        pass

    def test_config_not_found(self):
        """ Test an error is raised if config section missing. """
        self.assertRaises(KeyError, self.__get_inst, broken=True)

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_get(self, mock_req):
        """ Test HTTP GET verb. """
        client = self.__get_inst()
        client.get("/test_url")
        mock_req.assert_called_with("/test_url", "GET")

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_put(self, mock_req):
        """ Test HTTP PUT verb. """
        client = self.__get_inst()
        client.put("/test_url", "POSTDATA")
        mock_req.assert_called_with("/test_url", "PUT", "POSTDATA")

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_post(self, mock_req):
        """ Test HTTP POST verb. """
        client = self.__get_inst()
        client.post("/test_url", "POSTDATA")
        mock_req.assert_called_with("/test_url", "POST", "POSTDATA")

    @mock.patch.object(RESTClient, "_RESTClient__do_request")
    def test_delete(self, mock_req):
        """ Test HTTP DELETE verb. """
        client = self.__get_inst()
        client.delete("/test_url")
        mock_req.assert_called_with("/test_url", "DELETE")

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_basic(self, mock_req):
        """ Do a simple request an check the result returned matches
            what was returned by requests.
        """
        BASE_URL = "https://localhost:12345/testsvc"
        URI = 'test_url'
        client = self.__get_inst(BASE_URL)
        ret_obj = "TESTSTR"
        self.__mock_req(mock_req, 200, ret_obj)
        res = client.delete(URI)
        self.assertEqual(res, ret_obj)
        # Check basic request args (method + URL)
        args = mock_req.request.call_args[0]
        self.assertSequenceEqual(args, ("DELETE", BASE_URL + "/" + URI))

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_error(self, mock_req):
        """ Check that a server error converts to an exception.
        """
        client = self.__get_inst()
        self.__mock_req(mock_req, 500, "")
        self.assertRaises(RuntimeError, client.get, '/test_url')

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_token(self, mock_req):
        """ Check that requests contain the correct token header.
        """
        # No Token
        client = self.__get_inst()
        self.__mock_req(mock_req, 200, "")
        client.get('test_url')
        self.assertNotIn('X-Token', mock_req.request.call_args[1]['headers'])
        # Token in constructor
        mock_req.reset_mock()
        client = self.__get_inst(token="TESTTOKEN1")
        self.__mock_req(mock_req, 200, "")
        client.get('test_url')
        headers = mock_req.request.call_args[1]['headers']
        self.assertIn('X-Token', headers)
        self.assertEqual('TESTTOKEN1', headers['X-Token'])
        # Token set function (using same client as previous test)
        mock_req.reset_mock()
        client.set_token("TESTTOKEN2")
        self.__mock_req(mock_req, 200, "")
        client.get('test_url')
        headers = mock_req.request.call_args[1]['headers']
        self.assertIn('X-Token', headers)
        self.assertEqual('TESTTOKEN2', headers['X-Token'])
        self.assertEqual(client.get_token(),"TESTTOKEN2")

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_conf_ssl(self, mock_req):
        """ Test that configuring SSL works as expected via the config.
        """
        TEST_CA, TEST_CERT, TEST_KEY = ('/TESTCA', '/TESTCERT', '/TESTKEY')
        ssl_conf = {
            'cafile': TEST_CA,
            'cert': TEST_CERT,
            'key': TEST_KEY,
        }
        client = self.__get_inst(client_conf=ssl_conf)
        self.__mock_req(mock_req, 200, "")
        client.get('test_ssl')
        verify = mock_req.request.call_args[1]['verify']
        self.assertEqual(verify, TEST_CA)
        cert = mock_req.request.call_args[1]['cert']
        self.assertSequenceEqual(cert, (TEST_CERT, TEST_KEY))

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_conf_timeout(self, mock_req):
        """ Test that timeout config works.
        """
        TEST_TIMEOUT = 33
        client = self.__get_inst(client_conf={'timeout': TEST_TIMEOUT})
        self.__mock_req(mock_req, 200, "")
        client.get('test_timeout')
        real_timeout = mock_req.request.call_args[1]['timeout']
        self.assertEqual(real_timeout, TEST_TIMEOUT)

    def test_bad_option(self):
        """ Check that an exception is thrown if the client config has an
            unrecognised option.
        """
        TEST_CA, TEST_CERT, TEST_KEY = ('/TESTCA', '/TESTCERT', '/TESTKEY')
        ssl_conf = {
            'cafile': TEST_CA,
            'cert': TEST_CERT,
            'key': TEST_KEY,
            'badoption': 'yes',
        }
        self.assertRaises(ValueError, self.__get_inst, client_conf=ssl_conf)

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_constr_ssl(self, mock_req):
        """ Test that configuring SSL via the constructor works and
            overrides the config.
        """
        TEST_CA1, TEST_CERT1, TEST_KEY1 = ('/CONFCA', '/CONFCERT', '/CONFKEY')
        TEST_CA2, TEST_CERT2, TEST_KEY2 = ('/TESTCA', '/TESTCERT', '/TESTKEY')
        ssl_conf = {
            'cafile': TEST_CA1,
            'cert': TEST_CERT1,
            'key': TEST_KEY1,
        }
        ssl_opts = (TEST_CA2, TEST_CERT2, TEST_KEY2)
        client = self.__get_inst(client_conf=ssl_conf, ssl_opts=ssl_opts)
        self.__mock_req(mock_req, 200, "")
        client.get('test_ssl')
        verify = mock_req.request.call_args[1]['verify']
        self.assertEqual(verify, TEST_CA2)
        cert = mock_req.request.call_args[1]['cert']
        self.assertSequenceEqual(cert, (TEST_CERT2, TEST_KEY2))

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_data_arg(self, mock_req):
        """ Check that POST data is correctly copied through to the library.
        """
        client = self.__get_inst()
        self.__mock_req(mock_req, 200, "")
        post_data_in = {'POST': 'DATA'}
        client.post('test_post', data=post_data_in)
        post_data_out = mock_req.request.call_args[1]['json']
        self.assertEqual(post_data_out, post_data_in)

    @mock.patch("pdm.framework.RESTClient.requests")
    def test_no_text(self, mock_req):
        """ Test that None is returned if the server returns an empty
            200 repsonse code.
        """
        client = self.__get_inst()
        self.__mock_req(mock_req, 200, "", is_obj=False)
        res = client.get('test_url')
        self.assertIsNone(res)

class TestRESTClientTest(unittest.TestCase):
    """ A test case for RESTClientTest class. """

    TEST_BASE = '/base/test'

    class TestClient(RESTClient):
        """ A test class, based on RESTClient to be patched. """
        def __init__(self):
            super(self.__class__,  self).__init__("service_name")

    def setUp(self):
        """ Create a patched instance of the TestClient. """
        self.__tc = mock.MagicMock()
        self.__patcher, self.__client = \
            RESTClientTest.patch_client(TestRESTClientTest.TestClient,
                                        self.__tc,
                                        TestRESTClientTest.TEST_BASE)

    def tearDown(self):
        """ Stop patching the TestClient instance. """
        self.__patcher.stop()

    def test_get(self):
        """ Try a plain get and check the correct function was called. """
        res_obj = mock.Mock()
        res_obj.status_code = 200
        res_obj.data = ""
        self.__tc.get.return_value = res_obj
        self.__client.get('file')
        self.__tc.get.assert_called_with(TestRESTClientTest.TEST_BASE + \
                                         "/file", data=None)

    def test_put(self):
        """ Test put call, includes data """
        POST_DATA = {'test': 'yes'}
        res_obj = mock.Mock()
        res_obj.status_code = 200
        res_obj.data = ""
        self.__tc.put.return_value = res_obj
        self.__client.put('file', data=POST_DATA)
        self.__tc.put.assert_called_with(TestRESTClientTest.TEST_BASE + \
                                         "/file", data=POST_DATA)

    def test_delete(self):
        """ Test the delete call. """
        res_obj = mock.Mock()
        res_obj.status_code = 200
        res_obj.data = ""
        self.__tc.delete.return_value = res_obj
        self.__client.delete('file')
        self.__tc.delete.assert_called_with(TestRESTClientTest.TEST_BASE + \
                                            "/file", data=None)

    def test_post(self):
        """ Test post call, with data. """
        POST_DATA = {'test': 'yes'}
        res_obj = mock.Mock()
        res_obj.status_code = 200
        res_obj.data = ""
        self.__tc.post.return_value = res_obj
        self.__client.post('file', data=POST_DATA)
        self.__tc.post.assert_called_with(TestRESTClientTest.TEST_BASE + \
                                          "/file", data=POST_DATA)

    def test_return_data(self):
        """ Check that reutrn data is actually returned. """
        RET_DATA = {'res': "OUTPUT DATA"}
        res_obj = mock.Mock()
        res_obj.status_code = 200
        res_obj.data = json.dumps(RET_DATA)
        self.__tc.get.return_value = res_obj
        ret = self.__client.get('file')
        self.assertDictEqual(ret, RET_DATA)

    def test_no_errors(self):
        """ Check that codes 200 and 201 don't cause an exception. """
        for code in (200, 201):
            res_obj = mock.Mock()
            res_obj.status_code = code
            res_obj.data = ""
            self.__tc.get.return_value = res_obj
            self.__client.get('file')

    def test_errors(self):
        """ Check that error codes raise exceptions. """
        res_obj = mock.Mock()
        res_obj.status_code = 500
        res_obj.data = ""
        self.__tc.get.return_value = res_obj
        self.assertRaises(RuntimeError, self.__client.get, 'file')
