#!/usr/bin/env python

import unittest
import unittest.mock as mock

from pdm.web.WebPageService import WebPageService
from pdm.framework.FlaskWrapper import FlaskServer

class TestWebPageService(unittest.TestCase):
    
    @mock.patch("pdm.web.WebPageService.HRClient")
    @mock.patch("pdm.web.WebPageService.SiteClient")
    def setUp(self, hr_mock, ep_mock):
        hr_mock.return_value = object() # no MockHRClient available
        ep_mock.return_value = object() # no MockSiteClient available
        conf = { }
        self.__service = FlaskServer("pdm.web.WebPageService")
        self.__service.test_mode(WebPageService, conf, with_test=True)
        self.__service.fake_auth("ALL")
        self.__test = self.__service.test_client()


    def test_web(self):
        """ Check that the basic website redirect + index page work. """
        res = self.__test.get('/')
        # 302 == redirect, assertEqual is from unittest
        self.assertEqual(res.status_code, 302)
        self.assertIn('/web/datamover', res.location)
        res = self.__test.get('/web/datamover')
        self.assertEqual(res.status_code, 200)
        self.assertIn("<!doctype html>", res.get_data(as_text=True))
    
    def test_about(self):
        """ Check that the about page is returned at the correct location. """
        res = self.__test.get('/static/about.html')
        # check its existence
        self.assertEqual(res.status_code, 200)
        self.assertIn("About the datamover", res.get_data(as_text=True))



