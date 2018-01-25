#!/usr/bin/env python

import unittest

from pdm.demo.DemoService import DemoService
from pdm.framework.FlaskWrapper import FlaskServer


class TestConfigSystem(unittest.TestCase):

    def setUp(self):
        conf = { 'test_param': 1111 }
        self.__service = FlaskServer(self.__name__)
        self.__service.test_mode(DemoService, conf)
        self.__test = self.__service.test_client()

    def tearDown(self):
        pass

#    def test_hello(self):
#        res = self.__test.get('/demo/api/v1.0/hello')
#        #assert(res.data == 'Bah')

    def test_getToken(self):
        res = self.__test.get('/demo/api/v1.0/get_token')
        assert(res.data == "abc")
        assert(len(res.data) > 10)
