__author__ = 'martynia'

import json
import unittest

from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.HRService import HRService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest

class TestDemoClient(unittest.TestCase):

    def setUp(self):
        # Get an instance of HRService to test against
        conf = {}
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)
        self.__service.fake_auth("ALL")

        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        new_user = db.tables.User(username='guest',
                                  name='John', surname='Smith',
                                  email='Johnny@example.com', state=0,
                                  password='very_secret')
        db.session.add(new_user)
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup

        self.__test = self.__service.test_client()

        # Create an instance of DemoClient connected to DemoService
        patcher, inst = RESTClientTest.patch_client(HRClient,
                                                    self.__test,
                                                    '/users/api/v1.0')
        self.__patcher = patcher
        self.__client = inst

    def tearDown(self):
        self.__patcher.stop()

    def test_hello(self):
        assert(self.__client.hello() == 'Hello World!\n')
