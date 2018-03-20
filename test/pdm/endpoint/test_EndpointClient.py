#!/usr/bin/env python
""" Test EndpointService client classes. """

import unittest

from pdm.endpoint.EndpointService import EndpointService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest
from pdm.endpoint.EndpointClient import EndpointClient, MockEndpointClient

class test_EndpointClient(unittest.TestCase):

    def setUp(self):
        self._service = FlaskServer("pdm.endpoint.EndpointService")
        self._service.test_mode(EndpointService, {}, with_test=False)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client()
        patcher, inst = RESTClientTest.patch_client(EndpointClient,
                                                    self._test,
                                                    '/endpoint/api/v1.0')
        self._patcher = patcher
        self._inst = inst

    def tearDown(self):
        self._patcher.stop()

    def test_site(self):
        """ Check we can add, get and delete a site,
            including some endpoints.
        """
        SITE_NAME = "Test Site"
        SITE_DESC = "Lovely Test Site"
        SITE_EPS = ("https://localhost", "gsiftp://localhost")
        SITE_MAPPINGS = ((1234, "USER1"), (4321, "OTHER_USER"))
        site_id = self._inst.add_site(SITE_NAME, SITE_DESC)
        self.assertIsInstance(site_id, int)
        for ep_uri in SITE_EPS:
            ep_id = self._inst.add_endpoint(site_id, ep_uri)
            self.assertIsInstance(ep_id, int)
        # Now get the site info and check it matches
        site_list = self._inst.get_sites()
        self.assertEqual(len(site_list), 1)
        self.assertEqual(site_list[0]['site_id'], site_id)
        self.assertEqual(site_list[0]['site_name'], SITE_NAME)
        self.assertEqual(site_list[0]['site_desc'], SITE_DESC)
        # Get the full site info, including endpoints
        site_info = self._inst.get_site(site_id)
        self.assertEqual(site_info['site_id'], site_id)
        self.assertEqual(site_info['site_name'], SITE_NAME)
        self.assertEqual(site_info['site_desc'], SITE_DESC)
        endpoints = site_info['endpoints']
        self.assertEqual(len(endpoints), len(SITE_EPS))
        ep_uris = [x for x in endpoints.itervalues()]
        self.assertItemsEqual(SITE_EPS, ep_uris)
        # Try deleting one of the endpoints
        ep_id = endpoints.keys()[0]
        self._inst.del_endpoint(site_id, ep_id)
        site_info = self._inst.get_site(site_id)
        self.assertEqual(len(site_info['endpoints']), len(SITE_EPS) - 1)
        # Test the mappings, by adding two, getting them back
        for uid, uname in SITE_MAPPINGS:
          self._inst.add_mapping(site_id, uid, uname)
        mappings = self._inst.get_mappings(site_id)
        self.assertEqual(len(mappings), len(SITE_MAPPINGS))
        # Delete one of the mappings
        self._inst.del_mapping(site_id, SITE_MAPPINGS[0][0])
        mappings = self._inst.get_mappings(site_id)
        self.assertEqual(len(mappings), len(SITE_MAPPINGS) - 1)
        # Delete another one with the del user function
        self._inst.del_user(SITE_MAPPINGS[1][0])
        mappings = self._inst.get_mappings(site_id)
        self.assertEqual(len(mappings), len(SITE_MAPPINGS) - 2)
        # Try deleting the whole site
        self._inst.del_site(site_id)
        site_list = self._inst.get_sites()
        self.assertEqual(len(site_list), 0)


class test_MockEndpointClient(test_EndpointClient):
    """ Do the same tests as for EndpointClient,  but with the mock class.
    """

    def setUp(self):
        self._inst = MockEndpointClient()

    def tearDown(self):
        pass

    def test_mock_errors(self):
        """ Check that the mock client generates errors as expected. """
        # Duplicate site name
        site_id = self._inst.add_site("A", "B")
        self.assertRaises(RuntimeError, self._inst.add_site, "A", "B")
        # Missing site for various calls
        self.assertRaises(RuntimeError, self._inst.get_site, 999)
        self.assertRaises(RuntimeError, self._inst.del_site, 999)
        self.assertRaises(RuntimeError, self._inst.add_endpoint, 999, "")
        self.assertRaises(RuntimeError, self._inst.del_endpoint, 999, 1)
        self.assertRaises(RuntimeError, self._inst.get_mappings, 999)
        self.assertRaises(RuntimeError, self._inst.add_mapping, 999, 1, "")
        self.assertRaises(RuntimeError, self._inst.del_mapping, 999, 1)
        # Valid site, but missing item
        self.assertRaises(RuntimeError, self._inst.del_endpoint, site_id, 1)
        self.assertRaises(RuntimeError, self._inst.add_mapping, 999, 1, "")
        self.assertRaises(RuntimeError, self._inst.del_mapping, site_id, 1)
        # Mapping already exists
        self._inst.add_mapping(site_id, 1, "X")
        self.assertRaises(RuntimeError, self._inst.add_mapping, site_id, 1, "X")
