__author__ = 'martynia'

import json
import unittest

from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.HRService import HRService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest


class TestHRClient(unittest.TestCase):
    def setUp(self):
        # Get an instance of HRService to test against
        conf = {}
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)
        self.__service.fake_auth("ALL")

        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        self.__userdict = {'username': 'guest',
                           'name': 'John', 'surname': 'Smith',
                           'email': 'Johnny@example.com', 'state': 0,
                           'password': 'very_secret'}
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
        print the_exception
        assert (the_exception[0] == 'Request failed with code 403')

    def test_add_user(self):
        userdict = {'username': 'fred',
                    'name': 'Fred', 'surname': 'Smith',
                    'email': 'fred@example.com', 'state': 0,
                    'password': 'very_secret'}
        res = self.__client.add_user(userdict)
        #assert (res.status_code == 201)
