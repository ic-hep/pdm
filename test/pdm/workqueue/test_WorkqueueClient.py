#!/usr/bin/env python
""" Test WorkqueueClient class. """

import unittest
import mock

from pdm.framework.FlaskWrapper import FlaskServer
from pdm.framework.RESTClient import RESTClientTest
from pdm.workqueue.WorkqueueService import WorkqueueService
from pdm.workqueue.WorkqueueClient import WorkqueueClient


class test_WorkqueueClient(unittest.TestCase):

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
        #Job = self._service.test_db().tables.Job
        with mock.patch.object(self._service, 'list') as list_mock:
            self._inst.list(12, '/data/somefile', 'somesecret')
        self.assertTrue(list_mock.called)
