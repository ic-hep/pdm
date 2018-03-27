#!/usr/bin/env python
""" Test the Decorators module. """

import json
import unittest
from flask import Flask

from pdm.framework.Decorators import *

class DecoratorTests(unittest.TestCase):
    """ Test all of the decorator functions. """

    def test_export(self):
        """ Test export decorator. """
        def dummy_obj():
            pass
        fcn = export(dummy_obj)
        self.assertTrue(fcn.is_exported)
        exp_export = [('dummy_obj', ["GET"], None)]
        self.assertEqual(fcn.exportables, exp_export)
    
    def test_export_ext(self):
        """ Test export_ext decorator. """
        def dummy_obj():
            pass
        fcn = export_ext("/hello", ["GET"], "/redir")(dummy_obj)
        fcn = export_ext("/hello2", ["POST", "PUT"])(fcn)
        fcn = export_ext("/hello3")(fcn)
        self.assertTrue(fcn.is_exported)
        exp_export = [
            ('/hello', ['GET'], '/redir'),
            ('/hello2', ['POST', 'PUT'], None),
            ('/hello3', ['GET'], None),
        ]
        self.assertEqual(fcn.exportables, exp_export)

    def test_startup(self):
        """ Test startup decorator. """
        def dummy_obj():
            pass
        fcn = startup(dummy_obj)
        self.assertTrue(fcn.is_startup)

    def test_startup_test(self):
        """ Test startup_test decorator. """
        def dummy_obj():
            pass
        fcn = startup_test(dummy_obj)
        self.assertTrue(fcn.is_test_func)

    def test_db_model(self):
        """ Test db_model decorator. """
        def dummy_obj():
            pass
        fcn = db_model("db.model.test1")(dummy_obj)
        self.assertEqual(fcn.db_model, ["db.model.test1"])
        # Check multiple models add to the list
        fcn = db_model("db.model.test2")(fcn)
        self.assertEqual(fcn.db_model,
                         ["db.model.test1", "db.model.test2"])

    def test_decode_json_data(self):
        """ Test the decode_json_data decorator. """
        app = Flask("TestApp")
        # Test with a plain JSON object, also check that
        # positional and named arguments are passed through.
        TEST_OBJ = {"a":1, "b": "test"}
        def test_fcn(arg1, arg2):
            self.assertEqual(arg1, 123)
            self.assertEqual(arg2, 567)
            self.assertEqual(request.data, TEST_OBJ)
        with app.test_request_context(path="/test"):
            request.data = json.dumps(TEST_OBJ)
            fcn = decode_json_data(test_fcn)(123, arg2=567)
        # Same as above, but with dict in request.data (which shouldn't
        # be decoded.
        def test_fcn2():
            self.assertEqual(request.data, TEST_OBJ)
        with app.test_request_context(path="/test"):
            request.data = TEST_OBJ
            fcn = decode_json_data(test_fcn2)()
