#!/usr/bin/env python
""" Test WorkqueueClient class. """
import unittest
import mock

from pdm.framework.FlaskWrapper import FlaskServer, jsonify
from pdm.framework.RESTClient import RESTClientTest
from pdm.workqueue.WorkqueueService import WorkqueueService
from pdm.workqueue.WorkqueueClient import WorkqueueClient


class test_WorkqueueClient(unittest.TestCase):

#    @mock.patch('pdm.workqueue.WorkqueueService.WorkqueueService')
    def setUp(self):
        self._service = FlaskServer("pdm.workqueue.WorkqueueService")
        self._service.test_mode(WorkqueueService, {}, with_test=False)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client()
        self._patcher, self._inst = RESTClientTest.patch_client(WorkqueueClient,
                                                    self._test,
                                                    '/workqueue/api/v1.0')

    def tearDown(self):
        self._patcher.stop()

    def test_list(self):
        args = {'src_siteid': 12,
                'src_filepath': '/data/somefile',
                'credentials': 'somesecret'}
        listmock = mock.MagicMock()
        listmock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'list': listmock}):
            response = self._inst.list(**args)
        self.assertTrue(listmock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)

    def test_copy(self):
        args = {'src_siteid': 12,
                'src_filepath': '/data/somefile',
                'dst_siteid': 15,
                'dst_filepath': '/data/someotherfile',
                'credentials': 'somesecret'}
        copymock = mock.MagicMock()
        copymock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'copy': copymock}):
            response = self._inst.copy(**args)
        self.assertTrue(copymock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)

    def test_remove(self):
        args = {'src_siteid': 12,
                'src_filepath': '/data/somefile',
                'credentials': 'somesecret'}
        removemock = mock.MagicMock()
        removemock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'remove': removemock}):
            response = self._inst.remove(**args)
        self.assertTrue(removemock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)
