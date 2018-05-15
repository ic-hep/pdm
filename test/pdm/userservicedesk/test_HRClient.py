"""
RESTful test client API for the HRService service
"""

import json
import unittest
import mock
import datetime

from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.HRService import HRService
from pdm.cred.CredClient import MockCredClient
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest
from pdm.utils.hashing import hash_pass


class TestHRClient(unittest.TestCase):

    @mock.patch("pdm.userservicedesk.HRService.SiteClient")
    def setUp(self, site_mock):
        # Get an instance of HRService to test against
        conf = {}
        self.__future_date = (datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()
        self.__past_date = (-datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)
        self.__service.fake_auth("ALL")

        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        # the user in the db with a hashed password.
        self.__userdict = {
            'name': 'John', 'surname': 'Smith',
            'email': 'Johnny@example.com', 'state': 0,
            'password': hash_pass('very_secret')}
        self.__userjson = json.dumps(self.__userdict)

        new_user = db.tables.User.from_json(self.__userjson)
        db.session.add(new_user)
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup

        self.__test = self.__service.test_client()

        # Create an instance of HRClient connected to HRService
        patcher, inst = RESTClientTest.patch_client(HRClient,
                                                    self.__test,
                                                    '/users/api/v1.0')
        self.__patcher = patcher
        self.__client = inst

    def tearDown(self):
        self.__patcher.stop()

    def test_hello(self):
        assert (self.__client.hello() == 'User Service Desk at your service !\n')

    def test_login(self):
        res = self.__client.login('Johnny@example.com', 'very_secret')
        assert (isinstance(res, unicode))

        with self.assertRaises(Exception) as login_ex:
            res = self.__client.login('Johnny@example.com', 'very_secret1')

        the_exception = login_ex.exception
        assert (the_exception.code == 403)

    def test_add_user(self):
        userdict = {
            'name': 'Fred', 'surname': 'Smith',
            'email': 'fred@example.com', 'state': 0,
            'password': 'very_secret'}
        res = self.__client.add_user(userdict)
        # result is a list containing a user dict
        assert (res['email'] == userdict['email'])

        with self.assertRaises(Exception) as add_ex:
            res = self.__client.add_user(userdict)

        the_exception = add_ex.exception
        assert (the_exception.code == 403)

    def test_change_password(self):
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__future_date})
        # client takes plain passwords
        res = self.__client.change_password('very_secret', 'newpassword')
        print res
        assert (res['email'] == self.__userdict['email'])

        with self.assertRaises(Exception) as pwd_ex:
            res = self.__client.change_password('newpassword', None)

        the_exception = pwd_ex.exception
        assert (the_exception.code == 400)

        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__past_date})
        with self.assertRaises(Exception) as pwd_ex:
            res = self.__client.change_password('newpassword', 'evennewerpasword')

        the_exception = pwd_ex.exception
        assert (the_exception.code == 403)

    def test_get_user(self):
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__future_date})
        res = self.__client.get_user()
        assert (res['email'] == self.__userdict['email'])

        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__past_date})
        with self.assertRaises(Exception) as pwd_ex:
            res = self.__client.get_user()
        the_exception = pwd_ex.exception
        assert (the_exception.code == 403)

    #@mock.patch('pdm.cred.CredClient.MockCredClient.del_user')

    def test_del_user(self):
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__future_date})
        res = self.__client.del_user()
        assert ('message' in res[0])

        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':self.__past_date})
        with self.assertRaises(Exception) as pwd_ex:
            res = self.__client.del_user()
        the_exception = pwd_ex.exception
        assert (the_exception.code == 403)