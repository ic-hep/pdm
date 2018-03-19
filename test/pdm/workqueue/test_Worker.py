#!/usr/bin/env python
""" Test WorkqueueClient class. """
import logging
import unittest
import mock

from pdm.framework.FlaskWrapper import FlaskServer, jsonify
from pdm.framework.RESTClient import RESTClientTest
from pdm.workqueue.WorkqueueService import WorkqueueService
from pdm.workqueue.Worker import Worker
from pdm.workqueue.WorkqueueDB import JobType, JobStatus, JobProtocol

class test_Worker(unittest.TestCase):

#    @mock.patch('pdm.workqueue.WorkqueueService.WorkqueueService')
    def setUp(self):
        self._service = FlaskServer("pdm.workqueue.WorkqueueService")
        self._service.test_mode(WorkqueueService, {}, with_test=False)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client()

        with mock.patch('pdm.workqueue.Worker.RESTClient.__init__'),\
             mock.patch('pdm.workqueue.Worker.Daemon.__init__'):

            self._patcher, self._inst = RESTClientTest.patch_client(Worker,
                                                                    self._test,
                                                                    '/workqueue/api/v1.0')
            # Setup test base class as we don't call super in Worker.__init__ so
            # mock away the call to RESTClient.__init__, hence the test base class is
            # never initialised. Actually don't need this as __init__ in RESTClientTest
            # only sets two variables to none which are set properly above in the patch_client
            # call which calls set_test_info so we actually dont want to set them None again.
#            RESTClientTest.__init__(self._inst, 'workqueue')
            self._inst._logger = logging.getLogger("Worker")

    def tearDown(self):
        self._patcher.stop()

    @unittest.expectedFailure
    @mock.patch('pdm.workqueue.Worker.EndpointClient')
    def test_run(self, endpointclient_mock):
        job = {'id': 1,
               'user_id': 9,
               'type': JobType.LIST,
               'status': JobStatus.SUBMITTED,
               'priority': 5,
               'protocol': JobProtocol.GRIDFTP,
               'src_siteid': 12,
               'src_filepath': '/data/somefile',
               'credentials': 'somesecret'}
        getjobmock = mock.MagicMock()
        outputmock = mock.MagicMock()
        getjobmock.return_value = jsonify((job, str(job['id'])))
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_next_job': getjobmock,
                                                            'WorkqueueService.return_output': outputmock}):

            self._inst.run()
        self.assertTrue(getjobmock.called)
        self.assertTrue(outputmock.called)