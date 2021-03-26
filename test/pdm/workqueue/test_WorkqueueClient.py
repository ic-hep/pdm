#!/usr/bin/env python
""" Test WorkqueueClient module. """
import unittest
import unittest.mock as mock

from pdm.framework.FlaskWrapper import FlaskServer, jsonify
from pdm.framework.RESTClient import RESTClientTest
from pdm.workqueue.WorkqueueService import WorkqueueService
from pdm.workqueue.WorkqueueClient import WorkqueueClient


class test_WorkqueueClient(unittest.TestCase):

    def setUp(self):
        self._service = FlaskServer("pdm.workqueue.WorkqueueService")
        with mock.patch('pdm.workqueue.WorkqueueService.SiteClient'):
            self._service.test_mode(WorkqueueService, {}, with_test=False)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client()
        self._patcher, self._inst = RESTClientTest.patch_client(WorkqueueClient,
                                                                self._test,
                                                                '/workqueue/api/v1.0')

    def tearDown(self):
        self._patcher.stop()

    def test_list(self):
        args = {'siteid': 12,
                'filepath': '/data/somefile'}
        listmock = mock.MagicMock()
        listmock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.list': listmock}):
            response = self._inst.list(**args)
        self.assertTrue(listmock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)

    def test_copy(self):
        args = {'src_siteid': 12,
                'src_filepath': '/data/somefile',
                'dst_siteid': 15,
                'dst_filepath': '/data/someotherfile'}
        copymock = mock.MagicMock()
        copymock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.copy': copymock}):
            response = self._inst.copy(**args)
        self.assertTrue(copymock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)

    def test_remove(self):
        args = {'siteid': 12,
                'filepath': '/data/somefile'}
        removemock = mock.MagicMock()
        removemock.return_value = jsonify(args)
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.remove': removemock}):
            response = self._inst.remove(**args)
        self.assertTrue(removemock.called)
        self.assertIsInstance(response, dict)
        self.assertEqual(response, args)

    def test_jobs(self):
        # check the token is passed
        methodmock = mock.MagicMock()
        methodmock.return_value = jsonify([])
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_jobs': methodmock}):
            response = self._inst.jobs()
        self.assertTrue(methodmock.called)
        self.assertEqual(response, [])

    def test_job(self):
        # check the token is passed
        methodmock = mock.MagicMock()
        methodmock.return_value = jsonify({})
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_job': methodmock}):
            response = self._inst.job(1)
        self.assertTrue(methodmock.called)
        self.assertEqual(response, {})

    def test_status(self):
        # check the token is passed
        methodmock = mock.MagicMock()
        methodmock.return_value = jsonify({})
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_job_status': methodmock}):
            response = self._inst.status(1)
        self.assertTrue(methodmock.called)
        self.assertEqual(response, {})
        methodmock.reset_mock()
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_element_status': methodmock}):
            response = self._inst.status(1, 0)
        self.assertTrue(methodmock.called)
        self.assertEqual(response, {})

    def test_output(self):
        # check the token is passed
        methodmock = mock.MagicMock()
        methodmock.return_value = jsonify({})
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_output': methodmock}):
            response = self._inst.output(1)
        self.assertTrue(methodmock.called)
        self.assertEqual(response, {})
