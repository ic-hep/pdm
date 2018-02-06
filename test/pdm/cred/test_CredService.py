#!/usr/bin/env python
""" Tests for the cred service module. """

import json
import unittest
from copy import deepcopy

from pdm.cred.CredService import CredService
from pdm.framework.FlaskWrapper import FlaskServer


class test_CredService(unittest.TestCase):
    """ Test the CredService service. """

    DEF_CONFIG = {'ca_dn': '/C=XX/OU=Test CA',
                  'ca_key': 'weakCAPass',
                  'user_dn_base': '/C=XX/OU=Test Users',
                  'user_cred_secret': 'weakUserPass'}

    def setUp(self):
        """ Configure the basic test service with some
            sensible default parameters.
        """
        self.__service = FlaskServer("pdm.cred.CredService")
        self.__service.test_mode(CredService,
                                 deepcopy(test_CredService.DEF_CONFIG))
        self.__service.fake_auth("ALL")
        self.__client = self.__service.test_client()

    def test_regen(self):
        """ Call the service initialisation a second time and check
            that the CA cert doesn't get regenerated (i.e. doesn't
            change in the DB).
        """
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        ca_info1 = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                          .first()
        # Re-run the start-up
        self.__service.before_startup(deepcopy(test_CredService.DEF_CONFIG))
        ca_info2 = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                          .first()
        self.assertEqual(ca_info1.pub_cert, ca_info2.pub_cert)

    def test_ca_config(self):
        """ Test that the CA was created as per the user configuration.
        """
        # TODO: Implement this test
        pass

    def test_ca(self):
        """ Test that we can access the CA cert with GET /ca.
        """
        res = self.__client.get('/cred/api/v1.0/ca')
        self.assertEqual(res.status_code, 200)
        self.assertItemsEqual
        json_obj = json.loads(res.data)
        # Check returned object matches the spec
        self.assertIsInstance(json_obj, dict)
        self.assertItemsEqual(['ca'], json_obj.keys())
        # Get the actual CA cert PEM
        ca_data = json_obj['ca']
        self.assertIn("BEGIN CERTIFICATE", ca_data)
        # Check that the ca_data matches the database entry
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                         .first()
        self.assertEqual(ca_data, ca_info.pub_cert)

    def test_add_user(self):
        """ Add a user and check that suitable credentials are created in
            the database.
        """
        TEST_USER_ID = 123
        TEST_USER_KEY = "weakUserKey"
        TEST_INPUT = {'user_id': TEST_USER_ID,
                      'user_key': TEST_USER_KEY}
        json_input = json.dumps(TEST_INPUT)
        res = self.__client.post('/cred/api/v1.0/user', data=json_input)
        self.assertEqual(res.status_code, 200, "Server returned: %s" % res.data)
        # TODO: Check response object matches spec
        # TODO: Check credentials in database
        # TODO: Check CA serial was stored correctly
