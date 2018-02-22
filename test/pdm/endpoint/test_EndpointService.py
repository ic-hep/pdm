#!/usr/bin/env python
""" Tests for the site/endpoint service module. """

import json
import mock
import unittest

from pdm.endpoint.EndpointService import EndpointService
from pdm.framework.FlaskWrapper import FlaskServer

# Test data, prepopulated into the DB in setUp
TEST_SITES = [
    { 'site_id': 10, 'site_name': 'Test1', 'site_desc': 'Test Site 1' },
    { 'site_id': 20, 'site_name': 'Test2', 'site_desc': 'Test Site 2' },
    { 'site_id': 30, 'site_name': 'TestC', 'site_desc': 'Test Site C' },
    { 'site_id': 40, 'site_name': 'Test4', 'site_desc': 'Test Site, No EPs' },
]
TEST_EPS = [
    { 'ep_id': 10, 'site_id': 10, 'ep_uri': 'https://localhost/1' },
    { 'ep_id': 20, 'site_id': 10, 'ep_uri': 'https://localhost/1' },
    { 'ep_id': 30, 'site_id': 10, 'ep_uri': 'https://localhost/blah' },
    { 'ep_id': 40, 'site_id': 20, 'ep_uri': 'https://localhost/2' },
    { 'ep_id': 50, 'site_id': 20, 'ep_uri': 'https://localhost/2' },
    { 'ep_id': 60, 'site_id': 30, 'ep_uri': 'https://localhost/../' },
    { 'ep_id': 70, 'site_id': 30, 'ep_uri': 'http://localhost/insecure' },
]
TEST_MAPPINGS = [
    { 'site_id': 10, 'user_id': 10, 'username': 'user001' },
    { 'site_id': 10, 'user_id': 20, 'username': 'turtle' },
    { 'site_id': 20, 'user_id': 30, 'username': 'timmy' },
    { 'site_id': 20, 'user_id': 40, 'username': 'jimmy' },
    { 'site_id': 40, 'user_id': 50, 'username': 'longusername' },
    { 'site_id': 40, 'user_id': 60, 'username': 'bill' },
    { 'site_id': 40, 'user_id':  4, 'username': 'gates' },
]

class test_EndpointService(unittest.TestCase):
    """ Test the EndpointService service. """

    @staticmethod
    def __db_error(mock_session):
        """ Replace a managed_session mock instance
            with one that throws an error (simulating
            a generic DB failure).
        """
        session = mock.MagicMock()
        mock_session.return_value = session
        session.__exit__.side_effect = Exception("DB Error")

    def setUp(self):
        """ Configure the basic service in test mode.
        """
        self.__service = FlaskServer("pdm.endpoint.EndpointService")
        self.__service.test_mode(EndpointService, )
        self.__service.fake_auth("ALL")
        self.__client = self.__service.test_client()
        # Populate the database
        db = self.__service.test_db()
        test_objs = []
        test_objs.extend([db.tables.Site(**x) for x in TEST_SITES])
        test_objs.extend([db.tables.Endpoint(**x) for x in TEST_EPS])
        test_objs.extend([db.tables.UserMap(**x) for x in TEST_MAPPINGS])
        for obj in test_objs:
            db.session.add(obj)
        db.session.commit()

    def test_site_basic(self):
        """ Test adding & then deleting a site from the DB.
        """
        TEST_NAME = "TESTSITE"
        TEST_DESC = "A test site."
        # Add the test site
        data = {'site_name': TEST_NAME,
                'site_desc': TEST_DESC}
        json_data = json.dumps(data)
        res = self.__client.post('/endpoints/api/v1.0/site', data=json_data)
        self.assertEqual(res.status_code, 200)
        # Check we got an ID number back
        site_id = json.loads(res.data)
        self.assertIsInstance(site_id, int)
        # Now get the site list
        res = self.__client.get('/endpoints/api/v1.0/site')
        self.assertEqual(res.status_code, 200)
        site_list = json.loads(res.data)
        # Check length, but there may be other test data
        self.assertGreaterEqual(len(site_list), len(TEST_SITES) + 1)
        # Most recently added site should be the last one
        site_out = site_list[-1]
        self.assertIn('site_id', site_out)
        self.assertIsInstance(site_out['site_id'], int)
        self.assertEqual(site_out['site_name'], TEST_NAME)
        self.assertEqual(site_out['site_desc'], TEST_DESC)

    def test_site_missing_post(self):
        """ Check we get 400 on missing or bad POST data. """
        res = self.__client.post('/endpoints/api/v1.0/site')
        self.assertEqual(res.status_code, 400)
        data = {'bad_key': 'value'}
        json_data = json.dumps(data)
        res = self.__client.post('/endpoints/api/v1.0/site', data=json_data)
        self.assertEqual(res.status_code, 400)

    def test_duplicate_site_name(self):
        """ Check that we get a 409 code if the site name is already
            registered.
        """
        TEST_NAME = "TESTSITE"
        TEST_DESC = "A test site."
        data = {'site_name': TEST_NAME,
                'site_desc': TEST_DESC}
        json_data = json.dumps(data)
        res = self.__client.post('/endpoints/api/v1.0/site', data=json_data)
        self.assertEqual(res.status_code, 200)
        res = self.__client.post('/endpoints/api/v1.0/site', data=json_data)
        self.assertEqual(res.status_code, 409)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_add_site_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        TEST_NAME = "TESTSITE"
        TEST_DESC = "A test site."
        data = {'site_name': TEST_NAME,
                'site_desc': TEST_DESC}
        json_data = json.dumps(data)
        res = self.__client.post('/endpoints/api/v1.0/site', data=json_data)
        self.assertEqual(res.status_code, 500)

    def test_del_site(self):
        """ Try deleting a site and checking it's gone. """
        res = self.__client.delete('/endpoints/api/v1.0/site/1')
        self.assertEqual(res.status_code, 200)
        # Check site is really gone from DB
        db = self.__service.test_db()
        entry = db.tables.Site.query.filter_by(site_id=1).first()
        self.assertIsNone(entry)
        # We also have to check that it cascaeded into endpoints & mappings
        entry = db.tables.Endpoint.query.filter_by(site_id=1).first()
        self.assertIsNone(entry)
        entry = db.tables.UserMap.query.filter_by(site_id=1).first()
        self.assertIsNone(entry)
        # Do the delete again and check we get a 404 as site is gone
        res = self.__client.delete('/endpoints/api/v1.0/site/1')
        self.assertEqual(res.status_code, 404)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_del_site_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        res = self.__client.delete('/endpoints/api/v1.0/site/1')
        self.assertEqual(res.status_code, 500)

    def test_add_endpoint(self):
        """ Test adding endpoints to a site and getting them with the
            main site info.
        """
        TEST_URI = "gsiftp://test_host/test"
        data = {'ep_uri': TEST_URI}
        json_data = json.dumps(data)
        # Try adding another endpoint to site 10.
        res = self.__client.post('endpoints/api/v1.0/site/10', data=json_data)
        self.assertEqual(res.status_code, 200)
        # Check we got an ID number back
        ep_id = json.loads(res.data)
        self.assertIsInstance(ep_id, int)
        res = self.__client.get('endpoints/api/v1.0/site/10')
        self.assertEqual(res.status_code, 200)
        site_info = json.loads(res.data)
        # Check the site_info matches site 1 from the test data.
        self.assertDictContainsSubset(TEST_SITES[0], site_info)
        # Check the endpoints
        self.assertIn(TEST_URI, site_info['endpoints'].itervalues())

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_add_endpoint_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        TEST_URI = "gsiftp://test_host/test"
        data = {'ep_uri': TEST_URI}
        json_data = json.dumps(data)
        res = self.__client.post('endpoints/api/v1.0/site/1', data=json_data)
        self.assertEqual(res.status_code, 500)

    def test_add_endpoint_bad_post(self):
        """ Test add endpoint fails gracefully if POST data is missing
            or bad.
        """
        bad_data = {'bad_key': 'value'}
        bad_json = json.dumps(bad_data)
        res = self.__client.post('endpoints/api/v1.0/site/2', data=bad_json)
        self.assertEqual(res.status_code, 400)
        res = self.__client.post('endpoints/api/v1.0/site/3')
        self.assertEqual(res.status_code, 400)

    def test_del_endpoint(self):
        """ Test removing an endpoint from a site. """
        # Remove the first endpoint from the test data
        ep_id = TEST_EPS[0]['ep_id']
        site_id = TEST_EPS[0]['site_id']
        uri = 'endpoints/api/v1.0/site/%u/%u' % (site_id, ep_id)
        res = self.__client.delete(uri)
        self.assertEqual(res.status_code, 200)
        # Check entry is really gone from DB
        db = self.__service.test_db()
        entry = db.tables.Endpoint.query.filter_by(ep_id=ep_id).first()
        self.assertIsNone(entry)
        # Do it again and check we get 404 not found.
        res = self.__client.delete(uri)
        self.assertEqual(res.status_code, 404)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_del_endpoint_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        res = self.__client.delete('endpoints/api/v1.0/site/1/1')
        self.assertEqual(res.status_code, 500)

    def test_add_sitemap(self):
        """ Test adding entries to the site map. """
        TEST_UID = 1234
        TEST_UNAME = "attuser"
        data = {'user_id': TEST_UID,
                'local_user': TEST_UNAME}
        json_data = json.dumps(data)
        res = self.__client.post('endpoints/api/v1.0/sitemap/2',
                                 data=json_data)
        self.assertEqual(res.status_code, 200)
        # Check the entry is in the database
        db = self.__service.test_db()
        entry = db.tables.UserMap.query.filter_by(site_id=2, user_id=TEST_UID) \
                                       .first()
        self.assertEqual(entry.username, TEST_UNAME)
        # Check that adding the same mapping again triggers a 409 error
        res = self.__client.post('endpoints/api/v1.0/sitemap/2',
                                 data=json_data)
        self.assertEqual(res.status_code, 409)

    def test_add_sitemap_bad_post(self):
        """ Check that add sitemap entry fails gracefully if POST data is
            missing or wrong.
        """
        res = self.__client.post('endpoints/api/v1.0/sitemap/1')
        self.assertEqual(res.status_code, 400)
        json_data = json.dumps({'a': 'b'})
        res = self.__client.post('endpoints/api/v1.0/sitemap/1',
                                 data=json_data)
        self.assertEqual(res.status_code, 400)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_add_sitemap_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        TEST_UID = 1234
        TEST_UNAME = "attuser"
        data = {'user_id': TEST_UID,
                'local_user': TEST_UNAME}
        json_data = json.dumps(data)
        res = self.__client.post('endpoints/api/v1.0/sitemap/1',
                                 data=json_data)
        self.assertEqual(res.status_code, 500)

    def test_del_sitemap(self):
        """ Test removing an entry from the site map. """
        # Try to remove first entry from test data
        TEST_SITE = TEST_MAPPINGS[0]['site_id']
        TEST_UID = TEST_MAPPINGS[0]['user_id']
        test_uri = 'endpoints/api/v1.0/sitemap/%u/%u' % (TEST_SITE, TEST_UID)
        res = self.__client.delete(test_uri)
        self.assertEqual(res.status_code, 200)
        # Check DB
        db = self.__service.test_db()
        entry = db.tables.UserMap.query.filter_by(site_id=TEST_SITE,
                                                  user_id=TEST_UID).first()
        self.assertIsNone(entry)
        # Check we now get 404
        res = self.__client.delete(test_uri)
        self.assertEqual(res.status_code, 404)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_del_sitemap_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        TEST_SITE = TEST_MAPPINGS[0]['site_id']
        TEST_UID = TEST_MAPPINGS[0]['user_id']
        test_uri = 'endpoints/api/v1.0/sitemap/%u/%u' % (TEST_SITE, TEST_UID)
        self.__db_error(mock_session)
        res = self.__client.delete(test_uri)
        self.assertEqual(res.status_code, 500)

    def test_del_sitemap_user(self):
        """ Test deleting a user from the site map. """
        # Add a new user to all test sites in DB
        TEST_UID = 9999
        db = self.__service.test_db()
        Site = db.tables.Site
        UserMap = db.tables.UserMap
        for site in Site.query.all():
            new_map = UserMap(user_id=TEST_UID, site_id=site.site_id,
                              username="localuser")
            db.session.add(new_map)
        db.session.commit()
        # Now remove the user
        uri = 'endpoints/api/v1.0/sitemap/all/%u' % TEST_UID
        res = self.__client.delete(uri)
        self.assertEqual(res.status_code, 200)
        # Check that user is gone from mapping DB
        entry = UserMap.query.filter_by(user_id=TEST_UID).first()
        self.assertIsNone(entry)

    @mock.patch("pdm.endpoint.EndpointService.managed_session")
    def test_del_sitemap_user_dberror(self, mock_session):
        """ Check that HTTP 500 is returned on DB errors. """
        self.__db_error(mock_session)
        TEST_UID = TEST_MAPPINGS[0]['user_id']
        test_uri = 'endpoints/api/v1.0/sitemap/all/%u' % TEST_UID
        res = self.__client.delete(test_uri)
        self.assertEqual(res.status_code, 500)

    def test_get_sitemap(self):
        """ Test getting a sitemap for a specific site. """
        TEST_SITE = 1 # Use the first site from the test data
        res = self.__client.get('endpoints/api/v1.0/sitemap/%u' % TEST_SITE)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        # Now we have to build a dict of expected users from TEST_MAPPINGS
        # JSON dict keys are strings, so we have to emulate that.
        exp_data = {str(x['user_id']): x['username'] for x in TEST_MAPPINGS \
                    if x['site_id'] == TEST_SITE}
        self.assertDictEqual(data, exp_data)
