#!/usr/bin/env
""" Framework database object tests. """

import mock
import json
import datetime
import unittest

from pdm.framework.Database import MemSafeSQLAlchemy
from pdm.framework.Database import JSONMixin, JSONTableEncoder


class TestMemSafeSQLAlchemy(unittest.TestCase):
    """ Tests the MemSafeSQLAlchemy driver. """

    def driver_test_helper(self, drivername, dbname):
        """ Calls the SQLAlchemy driver hacks with the given
            drivername and dbname, returns the configured options.
        """
        obj = MemSafeSQLAlchemy()
        app = mock.Mock()
        info = mock.Mock()
        info.drivername = drivername
        info.database = dbname
        options = {}
        ret = obj.apply_driver_hacks(app, info, options)
        self.assertEqual(app, ret)
        self.assertEqual(app, obj.app)
        self.assertEqual(info, obj.info)
        self.assertEqual(options, obj.options)
        return options

    def test_driver_hacks(self):
        """ Checks that the driver hacks
            are correctly applied.
        """
        class SQLAlchemyBase(object):
            def apply_driver_hacks(self, app, info, options):
                self.app = app
                self.info = info
                self.options = options
                return app
        patcher = mock.patch.object(MemSafeSQLAlchemy, '__bases__', 
                                    (SQLAlchemyBase,))
        patcher.start()
        # Check that options are patched if a memory SQLite DB is used
        opts = self.driver_test_helper('sqlite', None)
        self.assertIn('connect_args', opts)
        conn_args = opts['connect_args']
        self.assertIn('check_same_thread', conn_args)
        self.assertFalse(conn_args['check_same_thread'])
        self.assertIn('poolclass', opts)
        from sqlalchemy.pool import StaticPool
        self.assertEqual(opts['poolclass'], StaticPool)
        # Check that options are unchanged if conditions not met
        opts = self.driver_test_helper('sqlite', 'test.db')
        self.assertDictEqual(opts, {})
        opts = self.driver_test_helper('otherdb', None)
        self.assertDictEqual(opts, {})
        # Test complete, stop the patcher
        patcher.is_local = True
        patcher.stop()

class TestDBJson(unittest.TestCase):
    """ Test database JSON methods. """

    def test_plain(self):
        """ Test that JSONTableEncoder works on plain objects,
            including date-times.
        """
        test_dict = {'A': 1, 'B': 2}
        json_str = json.dumps(test_dict, cls=JSONTableEncoder)
        output_dict = json.loads(json_str)
        self.assertItemsEqual(test_dict.keys(), output_dict.keys())
        self.assertEqual(test_dict['A'], output_dict['A'])
        self.assertEqual(test_dict['B'], output_dict['B'])
        # Other objects should fall through to the default,
        # which causes a TypeError
        self.assertRaises(TypeError, json.dumps,
                          mock.Mock(), cls=JSONTableEncoder)

    def test_jsonFields(self):
        """ A class with a __excluded_fields__ attr should not
            export the fields listed.
        """
        class TestCls(JSONMixin):
            # Fake SQLAlchemy table structure
            __table__ = mock.Mock()
            __table__.columns = (mock.Mock(), mock.Mock(), mock.Mock())
            __table__.columns[0].name = 'A'
            __table__.columns[1].name = 'B'
            __table__.columns[2].name = 'C'
            # Try to exclude field B
            __excluded_fields__ = ('B')
            A = "TestA"
            B = "TestB"
            C = 123

        obj = TestCls()
        json_str = obj.json()
        # Convert the json back to an object and check the fields
        ret_obj = json.loads(json_str)
        self.assertEqual(len(obj), 2)
        self.assertDictEqual({'A': 'TestA',
                              'C': 123}, ret_obj)
    def test_jsonTable(self):
        """ Check that we can serialise an SQLAlchemy table class.
        """
        class TestCls(JSONMixin):
            __table__ = mock.Mock()
            __table__.columns = (mock.Mock(), mock.Mock())
            __table__.columns[0].name = 'A'
            __table__.columns[1].name = 'B'

            def __init__(self, A, B):
                self.A = A
                self.B = B

        obj = TestCls(A="Test123", B=321)
        json_str = obj.json()
        # Now do the reverse procedure
        ret_obj = TestCls.from_json(json_str)
        self.assertEqual("Test123", ret_obj.A)
        self.assertEqual(321, ret_obj.B)
