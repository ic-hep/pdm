#!/usr/bin/env python
""" Test CredService client classes. """

import datetime
import unittest

from pdm.cred.CredService import CredService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest
from pdm.cred.CredClient import CredClient, MockCredClient

class test_CredClient(unittest.TestCase):

    def setUp(self):
        conf = { 'ca_dn': 'C = XX, OU = Test CA',
                 'ca_key': 'testCAKey',
                 'user_dn_base': 'C = XX, OU = Test Users',
                 'user_cred_secret': 'testUserKey',
               }
        self._service = FlaskServer("pdm.cred.CredService")
        self._service.test_mode(CredService, conf)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client() 
        # Create a client test instance
        patcher, inst = RESTClientTest.patch_client(CredClient,
                                                    self._test,
                                                    '/cred/api/v1.0')
        self._patcher = patcher
        self._inst = inst

    def tearDown(self):
        self._patcher.stop()

    def test_ca(self):
        """ Just get the CA PEM. """
        ca_pem = self._inst.ca()
        self.assertIn('BEGIN CERTIFICATE', ca_pem)

    def test_workflow(self):
        """ Do a full test of adding a user + job cred. """
        TEST_USER_ID = 123
        TEST_USER_KEY = "mypass"
        TEST_USER_EMAIL = "test@test.test"
        TEST_CRED_TYPE = CredService.CRED_TYPE_SSH
        # Add entries
        self._inst.add_user(TEST_USER_ID, TEST_USER_KEY, TEST_USER_EMAIL)
        user_exp = self._inst.user_expiry(TEST_USER_ID)
        self.assertIsInstance(user_exp, datetime.datetime)
        token = self._inst.add_cred(TEST_USER_ID, TEST_USER_KEY,
                                     TEST_CRED_TYPE)
        # Try getting cred
        cred_pub, cred_priv = self._inst.get_cred(token)
        self.assertIsInstance(cred_pub, str)
        self.assertIsInstance(cred_priv, str)
        # Delete things
        self._inst.del_cred(token)
        self._inst.del_user(TEST_USER_ID)

class test_MockCredClient(test_CredClient):
    """ Exactly the same as testing CredClient,
        but use the mock class instead.
    """

    def setUp(self):
        """ Create a test instance of the mock class. """
        self._inst = MockCredClient()

    def tearDown(self):
        """ Do nothing (but override base class). """
        pass

    def test_mock_errors(self):
        """ The mock class generates extra errors that would
            normally come from the server.
            We have to check that those work as well.
        """
        # Delete invalid user
        self.assertRaises(RuntimeError, self._inst.del_user, 999)
        # Add cred to invalid user
        self.assertRaises(RuntimeError, self._inst.add_cred, 999, "X", 1)
        # User with invalid password
        self._inst.add_user(123, "pass1")
        self.assertRaises(RuntimeError, self._inst.add_cred, 123, "pass2", 1)
        # Bad token
        self.assertRaises(RuntimeError, self._inst.del_cred, "badtoken")
        self.assertRaises(RuntimeError, self._inst.get_cred, "badtoken")
