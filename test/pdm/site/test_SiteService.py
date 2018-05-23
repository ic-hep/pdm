#!/usr/bin/env python
""" Tests for the site/endpoint service module. """

import copy
import json
import mock
import logging
import datetime
import unittest

from flask import current_app
from pdm.site.SiteService import SiteService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.Tokens import TokenService

class test_SiteService(unittest.TestCase):
    """ Test the SiteService service. """

    TEST_SITE = {
      'site_name': 'TestSite',
      'site_desc': 'A test site.',
      'user_ca_cert': 'ABC',
      'service_ca_cert': '123',
      'auth_type': 0,
      'auth_uri': 'localhost:12345',
      'public': False,
      'def_path': '/root',
      'endpoints': ['localhost:12346', 'an.other.host:54321'],
    }

    @staticmethod
    def __db_error(mock_session):
        """ Replace a managed_session mock instance
            with one that throws an error (simulating
            a generic DB failure).
        """
        from flask import abort
        def run_session(request, message="Error",
                        logger=None, http_error_code=None):
            if http_error_code:
                abort(http_error_code, description=message)
            raise Exception("DB Error")
        mock_session.side_effect = run_session

    def set_user_token(self, user_id):
        token = {'id': user_id}
        self.__service.fake_auth("TOKEN", token)

    def setUp(self):
        """ Configure the basic service in test mode.
        """
        logging.basicConfig(level=logging.DEBUG)
        self.__service = FlaskServer("pdm.site.SiteService")
        self.__service.test_mode(SiteService, )
        self.set_user_token(1000)
        self.__client = self.__service.test_client()
        # This calls the startup_test functions a second time
        # To check it does nothing when the DB already contains entries
        self.__service.before_startup({}, with_test=True)

    def test_check_uri(self):
        """ Test the check_uri function correctly rejects URIs.
        """
        # OK
        self.assertTrue(SiteService.check_uri("localhost:12345"))
        self.assertTrue(SiteService.check_uri("www.google.com:12345"))
        # Missing Port
        self.assertFalse(SiteService.check_uri("localhost:"))
        # Missing seperator
        self.assertFalse(SiteService.check_uri("localhost"))
        self.assertFalse(SiteService.check_uri("localhost12345"))
        self.assertFalse(SiteService.check_uri("localhost@12345"))
        # Starts with invalid char
        self.assertFalse(SiteService.check_uri("_localhost:12345"))
        self.assertFalse(SiteService.check_uri("0localhost:12345"))
        self.assertFalse(SiteService.check_uri(".localhost:12345"))
        # Non-numeric port
        self.assertFalse(SiteService.check_uri("localhost:bah"))

    @mock.patch("pdm.site.SiteService.open", create=True)
    @mock.patch("pdm.site.SiteService.getConfig")
    def test_service_info(self, mock_conf, mock_open):
        """ Test the service info endpoint.
        """
        # Set-up mock conifg
        mock_conf.return_value = {'cafile': 'mytestfile',
                                  'users': 'https://localhost:1234'}
        # Set-up mock open
        fd = mock.MagicMock()
        mock_open.return_value.__enter__.return_value = fd
        fd.read.return_value = "---PEM---"
        # Actually run the test
        res = self.__client.get('/site/api/v1.0/service')
        self.assertEqual(res.status_code, 200)
        service_info = json.loads(res.data)
        self.assertIn('central_ca', service_info)
        self.assertEqual("---PEM---", service_info['central_ca'])
        self.assertIn('user_ep', service_info)
        self.assertEqual("https://localhost:1234", service_info['user_ep'])
        # Check the error case, where CA is unreadable
        fd.read.side_effect = IOError("Failed to read file.")
        res = self.__client.get('/site/api/v1.0/service')
        self.assertEqual(res.status_code, 200)
        service_info = json.loads(res.data)
        self.assertNotIn('central_ca', service_info)

    def test_basic_add_del(self):
        """ Try to add and then delete a site.
        """
        res = self.__client.post('/site/api/v1.0/site',
                                 data=test_SiteService.TEST_SITE)
        self.assertEqual(res.status_code, 200)
        # Check the returned item is an int (site_id)
        site_id = json.loads(res.data)
        self.assertIsInstance(site_id, int)
        # Check the new site appears in the list of all sites
        res = self.__client.get('/site/api/v1.0/site')
        self.assertEqual(res.status_code, 200)
        sites = json.loads(res.data)
        my_site = None
        for site in sites:
            if site['site_id'] == site_id:
                my_site = site
                break
        self.assertIsNotNone(my_site)
        self.assertTrue(my_site['is_owner'])
        # Now delete the site
        res = self.__client.delete('/site/api/v1.0/site/%u' % site_id)
        self.assertEqual(res.status_code, 200)

    def test_delete_acl(self):
        """ Check that the delete ACL works correctly. """
        # Site ID 1 is owned by user 1 in the test data.
        # Check that user 2 can't delete it.
        self.set_user_token(2)
        res = self.__client.delete('/site/api/v1.0/site/1')
        self.assertEqual(res.status_code, 404)
        # Double check that user 1 _can_ delete it
        self.set_user_token(1)
        res = self.__client.delete('/site/api/v1.0/site/1')
        self.assertEqual(res.status_code, 200)

    def test_get_site(self):
        """ Test that get site works, particularly that it respects the
            public flag.
        """
        # List of test (user_id, site_id, expected_return)
        TEST_MATRIX = [
          (1, 1, 200),  # Own site
          (1, 2, 200),  # Public site
          (2, 1, 404),  # Non-public and not owner
          (2, 2, 200),  # Own site 
        ]
        for user_id, site_id, exp_res in TEST_MATRIX:
            self.set_user_token(user_id)
            res = self.__client.get('/site/api/v1.0/site/%u' % site_id)
            self.assertEqual(res.status_code, exp_res)

    def test_add_site_errors(self):
        """ Test error cases for the add_site function.
        """
        # No POST data
        res = self.__client.post('/site/api/v1.0/site')
        self.assertEqual(res.status_code, 400)
        # Non-JSON POST data
        res = self.__client.post('/site/api/v1.0/site', data="HELLO")
        self.assertEqual(res.status_code, 400)
        # Missing Field(s)
        res = self.__client.post('/site/api/v1.0/site', data={'site_name':'bad'})
        self.assertEqual(res.status_code, 400)
        # Bad auth type
        bad_data = copy.deepcopy(self.TEST_SITE)
        bad_data["auth_type"] = 999
        res = self.__client.post('/site/api/v1.0/site', data=bad_data)
        self.assertEqual(res.status_code, 400)
        # Bad auth URI
        bad_data = copy.deepcopy(self.TEST_SITE)
        bad_data["auth_uri"] = "localhost:badport"
        res = self.__client.post('/site/api/v1.0/site', data=bad_data)
        self.assertEqual(res.status_code, 400)
        # Bad endpoint URI
        bad_data = copy.deepcopy(self.TEST_SITE)
        bad_data["endpoints"] = ["localhost:badport"]
        res = self.__client.post('/site/api/v1.0/site', data=bad_data)
        self.assertEqual(res.status_code, 400)
        # Duplicate Site Name
        bad_data = copy.deepcopy(self.TEST_SITE)
        bad_data["site_name"] = "Site1"
        res = self.__client.post('/site/api/v1.0/site', data=bad_data)
        self.assertEqual(res.status_code, 409)

    @mock.patch("pdm.site.SiteService.managed_session")
    def test_add_site_dberror(self, mock_session):
        """ Test a general DB is caught correctly in add_site.
        """
        self.__db_error(mock_session)
        res = self.__client.post('/site/api/v1.0/site', data=self.TEST_SITE)
        self.assertEqual(res.status_code, 500)

    def test_get_endpoints(self):
        """ Test the get endpoint function.
        """
        self.__service.fake_auth("CERT", "/CN=Any")
        res = self.__client.get('/site/api/v1.0/endpoint/1')
        self.assertEqual(res.status_code, 200)
        res = json.loads(res.data)
        self.assertIsInstance(res, dict)
        # Check we got a list of two endpoints
        self.assertIn('endpoints', res)
        self.assertIsInstance(res['endpoints'], list)
        self.assertEqual(len(res['endpoints']), 2)
        self.assertIn('cas', res)
        self.assertIsInstance(res['cas'], list)

    def test_del_user(self):
        """ Test deleting all sites belonging to a given user.
        """
        # First check we get a 404 if we use the wrong user_id
        res = self.__client.delete('/site/api/v1.0/user/1001')
        self.assertEqual(res.status_code, 404)
        # Now add some sites to delete
        test_data = copy.deepcopy(self.TEST_SITE)
        res = self.__client.post('/site/api/v1.0/site', data=test_data)
        self.assertEqual(res.status_code, 200)
        test_data['site_name'] = 'YetAnotherTestSite'
        res = self.__client.post('/site/api/v1.0/site', data=test_data)
        self.assertEqual(res.status_code, 200)
        # Check this user now has two sites
        res = self.__client.get('/site/api/v1.0/site')
        self.assertEqual(res.status_code, 200)
        my_sites = [x for x in json.loads(res.data) if x["is_owner"]]
        self.assertEqual(len(my_sites), 2)
        # We also need to add a credentials to test
        # Add this to the DB directly
        db = self.__service.test_db()
        Cred = db.tables.Cred
        db.session.add(Cred(cred_owner=1000,
                            site_id=1,
                            cred_username='mytest',
                            cred_expiry=datetime.datetime.utcnow(),
                            cred_value='secret'))
        db.session.commit()
        # Call the delete function
        res = self.__client.delete('/site/api/v1.0/user/1000')
        self.assertEqual(res.status_code, 200)
        # Now check user has 0 sites
        res = self.__client.get('/site/api/v1.0/site')
        self.assertEqual(res.status_code, 200)
        my_sites = [x for x in json.loads(res.data) if x["is_owner"]]
        self.assertEqual(len(my_sites), 0)
        # Check the cred has gone too
        cred = Cred.query.filter_by(cred_owner=1000).first()
        self.assertIsNone(cred)

    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_vomsdir(self, mp_utils):
        """ Test that the VO list is correctly loaded from the vomsdir
            if one is specified in the config.
        """
        TEST_VOS = ["vo1", "vo2.test.vo"]
        mp_utils.load_voms_list.return_value = TEST_VOS
        # Load in the conf with VOMS
        self.__service.before_startup({'vomses': '/myvoms'}, True)
        mp_utils.load_voms_list.assert_called_once_with('/myvoms')
        # Check that the service endpoint returns the correct list
        res = self.__client.get('/site/api/v1.0/service')
        self.assertEqual(res.status_code, 200)
        service_info = json.loads(res.data)
        self.assertIn('vos', service_info)
        self.assertItemsEqual(TEST_VOS, service_info['vos'])

    def test_session_basics(self):
        """ Manually add a credential to the DB and check that all of the 
            access functions (info, get_cred, delete) behave correctly.
        """
        # Create a test site
        res = self.__client.post('/site/api/v1.0/site', data=self.TEST_SITE)
        self.assertEqual(res.status_code, 200)
        site_id = json.loads(res.data)
        # Manually register a cred in the DB
        db = self.__service.test_db()
        Cred = db.tables.Cred
        future_time = datetime.datetime.utcnow()
        future_time += datetime.timedelta(minutes=5)
        db.session.add(Cred(cred_owner=1000,
                            site_id=site_id,
                            cred_username='myuser',
                            cred_expiry=future_time,
                            cred_value='secretcred'))
        db.session.commit()
        # Now check the details
        res = self.__client.get('/site/api/v1.0/session/%u' % site_id)
        self.assertEqual(res.status_code, 200)
        cred_info = json.loads(res.data)
        self.assertTrue(cred_info['ok'])
        self.assertEqual(cred_info['username'], 'myuser')
        # Try getting the cred secret
        res = self.__client.get('site/api/v1.0/cred/%u/1000' % site_id)
        self.assertEqual(res.status_code, 200)
        cred_secret = json.loads(res.data)
        self.assertEqual(cred_secret, 'secretcred')
        # Now test deletion
        res = self.__client.delete('/site/api/v1.0/session/%u' % site_id)
        self.assertEqual(res.status_code, 200)
        cred_count = Cred.query.filter_by(cred_owner=1000, site_id=site_id).count()
        self.assertEqual(cred_count, 0)

    @mock.patch("pdm.site.SiteService.X509Utils")
    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_logon(self, mp_mock, x509_mock):
        """ Check the basic functionality of the logon function. """
        mp_mock.logon.return_value = "PROXY"
        x509_mock.get_cert_expiry.return_value = datetime.datetime.utcnow()
        AUTH_DATA = {'username': "testuser",
                     'password': "usersecret",
                     'lifetime': 36}
        # Basic test again public site 2.
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 200)
        # Check that the cred was put in the DB
        res = self.__client.get('/site/api/v1.0/cred/2/1000')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), "PROXY")
        # Check the myproxy logon parameters
        self.assertEqual(mp_mock.logon.call_args[0][0], 'localhost:49998')
        self.assertEqual(mp_mock.logon.call_args[0][1], 'testuser')
        self.assertEqual(mp_mock.logon.call_args[0][2], 'usersecret')
        self.assertIsNone(mp_mock.logon.call_args[0][4])
        self.assertEqual(mp_mock.logon.call_args[0][5], 36)

    @mock.patch("pdm.site.SiteService.X509Utils")
    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_double_logon(self, mp_mock, x509_mock):
        """ Check that running logon twice with same params
            correctly overwrites the old proxy a second time.
        """
        mp_mock.logon.return_value = "PROXY"
        x509_mock.get_cert_expiry.return_value = datetime.datetime.utcnow()
        AUTH_DATA = {'username': "testuser",
                     'password': "usersecret",
                     'lifetime': 36}
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 200)
        # Try it a second time, different proxy
        mp_mock.logon.return_value = "PROXY2"
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 200)
        # Check that the cred was overwritten
        res = self.__client.get('/site/api/v1.0/cred/2/1000')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), "PROXY2")

    @mock.patch("pdm.site.SiteService.X509Utils")
    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_logon_grid(self, mp_mock, x509_mock):
        """ Check the logon function for obtaining grid creds. """
        TEST_VOS = ["vo1", "vo2.test.vo"]
        mp_mock.load_voms_list.return_value = TEST_VOS
        mp_mock.logon.return_value = "PROXY"
        x509_mock.get_cert_expiry.return_value = datetime.datetime.utcnow()
        CA_DIR = "/etc/grid-security/certificates"
        CONF_DATA = {
            'vomses': '/myvoms',
            'cadir': CA_DIR,
        }
        self.__service.before_startup(CONF_DATA, True)
        SITE_ID = 5 # ID of grid site in test data
        AUTH_DATA = {'username': "testuser",
                     'password': "usersecret",
                     'vo': "vo2.test.vo",
                     'lifetime': 36}
        # Check basic auth with voms
        res = self.__client.post('/site/api/v1.0/session/%u' % SITE_ID,
                                 data=copy.deepcopy(AUTH_DATA))
        self.assertEqual(res.status_code, 200)
        # Check call params
        self.assertEqual(mp_mock.logon.call_args[0][3], CA_DIR)
        self.assertEqual(mp_mock.logon.call_args[0][4], "vo2.test.vo")
        # Same again with missing VO name
        del AUTH_DATA['vo']
        res = self.__client.post('/site/api/v1.0/session/%u' % SITE_ID,
                                 data=copy.deepcopy(AUTH_DATA))
        self.assertEqual(res.status_code, 400)
        # Same again with bad VO name
        AUTH_DATA['vo'] = "bad.vo"
        res = self.__client.post('/site/api/v1.0/session/%u' % SITE_ID,
                                 data=copy.deepcopy(AUTH_DATA))
        self.assertEqual(res.status_code, 400)
        

    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_logon_errors(self, mp_mock):
        """ Check the error handling of the logon function. """
        # Missing post data
        res = self.__client.post('/site/api/v1.0/session/2')
        self.assertEqual(res.status_code, 400)
        # Missing field
        AUTH_DATA = {'username': 'testuser'}
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 400)
        # User not allowed at site
        AUTH_DATA = {'username': "testuser",
                     'password': "usersecret",
                     'lifetime': 36}
        res = self.__client.post('/site/api/v1.0/session/1', data=AUTH_DATA)
        self.assertEqual(res.status_code, 404)
        # MyProxy error
        MSG = "MP failed for some reason"
        mp_mock.logon.side_effect = Exception(MSG)
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 400)
        self.assertIn(MSG, res.data)

    @mock.patch("pdm.site.SiteService.managed_session")
    @mock.patch("pdm.site.SiteService.X509Utils")
    @mock.patch("pdm.site.SiteService.MyProxyUtils")
    def test_logon_dberror(self, mp_mock, x509_mock, mock_session):
        """ Checks that a general DB error is caught correctly. """
        mp_mock.logon.return_value = "PROXY"
        x509_mock.get_cert_expiry.return_value = datetime.datetime.utcnow()
        self.__db_error(mock_session)
        AUTH_DATA = {'username': "testuser",
                     'password': "usersecret",
                     'lifetime': 36}
        res = self.__client.post('/site/api/v1.0/session/2', data=AUTH_DATA)
        self.assertEqual(res.status_code, 500)
