#!/usr/bin/env python

import unittest
import unittest.mock as mock

from pdm.demo.DemoClient import DemoClient
from pdm.demo.DemoService import DemoService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest

class TestDemoClient(unittest.TestCase):

    def setUp(self):
        # Get an instance of DemoService to test against
        conf = { 'test_param': 1111 }
        self.__service = FlaskServer("pdm.demo.DemoService")
        self.__service.test_mode(DemoService, conf, with_test=True)
        self.__service.fake_auth("ALL")
        self.__test = self.__service.test_client()

        # Create an instance of DemoClient connected to DemoService
        patcher, inst = RESTClientTest.patch_client(DemoClient,
                                                    self.__test,
                                                    '/demo/api/v1.0')
        self.__patcher = patcher
        self.__client = inst

    def tearDown(self):
        self.__patcher.stop()

    def test_hello(self):
        assert(self.__client.hello() == 'Hello World!\n')

    def test_getTurtles(self):
        turtles = self.__client.get_turtles()
        assert(len(turtles) == 3)
        assert(turtles['1'] == 'Timmy')

    def test_addTurtle(self):
        new_turtle = self.__client.add_turtle('Test Turtle')
        assert(new_turtle['id'] == 4)
        assert(new_turtle['name'] == 'Test Turtle')
        turtles = self.__client.get_turtles()
        assert(len(turtles) == 4)

    def test_delTurtle(self):
        self.__client.del_turtle(3)
        turtles = self.__client.get_turtles()
        assert(len(turtles) == 2)

    def test_modifyTurtle(self):
        tid=1
        modif_turtle = self.__client.modify_turtle(tid, 'TimmyBoy')
        assert(modif_turtle)['id'] == tid
        assert(modif_turtle)['name'] == 'TimmyBoy'
        turtles = self.__client.get_turtles()
        assert(turtles['1']) == 'TimmyBoy'
        assert(len(turtles) == 3)
