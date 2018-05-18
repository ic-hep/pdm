#!/usr/bin/env python
""" Test Worker module. """
import logging
import unittest
import mock

from pdm.framework.FlaskWrapper import FlaskServer, jsonify
from pdm.framework.RESTClient import RESTClientTest
from pdm.workqueue.WorkqueueService import WorkqueueService
from pdm.workqueue.Worker import Worker
from pdm.workqueue.WorkqueueDB import JobType, JobStatus, JobProtocol


class test_Worker(unittest.TestCase):

    def setUp(self):
        self._service = FlaskServer("pdm.workqueue.WorkqueueService")
        with mock.patch('pdm.workqueue.WorkqueueService.SiteClient'):
            self._service.test_mode(WorkqueueService, {}, with_test=False)
        self._service.fake_auth("ALL")
        self._test = self._service.test_client()

        # Daemon won't setup logger for us so need one in place.
        Worker._logger = logging.getLogger("Worker")
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
#            self._inst._logger = logging.getLogger("Worker")
        self._inst._n_shot = 1

    def tearDown(self):
        self._patcher.stop()

    def test_run(self):
        workload = [{'id': 1,
                     'user_id': 9,
                     'type': JobType.LIST,
                     'status': JobStatus.SUBMITTED,
                     'priority': 5,
                     'protocol': JobProtocol.DUMMY,
                     'src_siteid': 12,
                     'src_filepath': '/data/somefile',
                     'src_credentials': 'somesecret',
                     'dst_credentials': 'someothersecret',
                     'extra_opts': {},
                     'elements': [{"id": 0,
                                   "job_id": 1,
                                   "type": JobType.LIST,
                                   "src_filepath": "/some/file",
                                   "token": 'secret_token'}]}]
        getjobmock = mock.MagicMock()
        outputmock = mock.MagicMock()
        getjobmock.return_value = jsonify(workload)
        outputmock.return_value = '', 200
        with mock.patch.dict(self._service.view_functions, {'WorkqueueService.get_next_job': getjobmock,
                                                            'WorkqueueService.return_output': outputmock}),\
             mock.patch.object(self._inst._site_client, 'get_endpoints') as mock_get_endpoints,\
                mock.patch('pdm.workqueue.Worker.X509Utils.add_ca_to_dir') as mock_ca2dir:
            mock_get_endpoints.return_value = {'endpoints': ['blah1', 'blah2', 'blah3'],
                                               'cas': ['blah blah', 'la la']}
            mock_ca2dir.return_value = '/tmp/somecadir'

            self._inst.run()
        self.assertTrue(getjobmock.called)
        self.assertTrue(outputmock.called)
        self.assertTrue(mock_get_endpoints.called)
        self.assertEqual(mock_get_endpoints.call_count, 1)
        self.assertTrue(mock_ca2dir.called)
