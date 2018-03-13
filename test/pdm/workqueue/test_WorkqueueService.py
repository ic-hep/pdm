import os
import json
import unittest
from textwrap import dedent
import mock

import pdm.userservicedesk.HRService as HRService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.workqueue.WorkqueueDB import JobType, JobStatus
from pdm.workqueue.WorkqueueService import WorkqueueService

class TestWorkqueueService(unittest.TestCase):
    def setUp(self):
        conf = {'workerlogs': '/tmp/workers'}
        self.__service = FlaskServer("pdm.workqueue.WorkqueueService")
        self.__service.test_mode(WorkqueueService, None)  # to skip DB auto build
        self.__service.fake_auth("ALL")
        self.__service.build_db()  # build manually

        db = self.__service.test_db()
        Job = db.tables.Job
        db.session.add(Job(user_id=1, src_siteid=13,
                           src_filepath='/data/somefile1', type=JobType.LIST))
        db.session.add(Job(user_id=2, src_siteid=14,
                           src_filepath='/data/somefile2', type=JobType.REMOVE))
        db.session.add(Job(user_id=3, src_siteid=15, src_filepath='/data/somefile3',
                           dst_siteid=16, dst_filepath='/data/newfile', type=JobType.COPY))
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup
        self.__test = self.__service.test_client()

    def test_get_next_job(self):
        """test worker get next job."""
        request = self.__test.post('/workqueue/api/v1.0/worker', data=json.dumps({'types': [JobType.LIST]}))
        self.assertEqual(request.status_code, 200, "Request to get worker job failed.")
        job, token = json.loads(request.data)
        self.assertIsInstance(token, basestring)
        self.assertDictContainsSubset({'user_id': 1,
                                       'src_siteid': 13,
                                       'src_filepath': '/data/somefile1',
                                       'type': JobType.LIST,
                                       'status': JobStatus.SUBMITTED}, job,  "Job not returned correctly.")
        Job = self.__service.test_db().tables.Job
        j = Job.query.filter_by(id=job['id']).one()
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.SUBMITTED, "Job status not updated in DB")

        request = self.__test.post('/workqueue/api/v1.0/worker', data=json.dumps({'types': [JobType.COPY, JobType.REMOVE]}))
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")

        request = self.__test.post('/workqueue/api/v1.0/worker', data=json.dumps({'types': [JobType.COPY, JobType.REMOVE]}))
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")
        request = self.__test.post('/workqueue/api/v1.0/worker', data=json.dumps({'types': [JobType.COPY, JobType.REMOVE]}))
        self.assertEqual(request.status_code, 404, "Trying to get a job that doesn't exist should return 404.")

    def test_return_output(self):
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data=json.dumps({'log': 'blah blah',
                                                    'returncode': 0,
                                                    'host': 'somehost.domain'}))
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "12")
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data=json.dumps({'log': 'blah blah',
                                                    'returncode': 0,
                                                    'host': 'somehost.domain'}))
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "100")
        request = self.__test.put('/workqueue/api/v1.0/worker/100',
                                   data=json.dumps({'log': 'blah blah',
                                                    'returncode': 0,
                                                    'host': 'somehost.domain'}))
        self.assertEqual(request.status_code, 404)

        self.__service.fake_auth("TOKEN", "1")
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data=json.dumps({'log': 'blah blah',
                                                    'returncode': 1,
                                                    'host': 'somehost.domain'}))
        self.assertEqual(request.status_code, 200)
        Job = self.__service.test_db().tables.Job
        j = Job.query.filter_by(id=1).one()
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.FAILED)
        logfile=os.path.join('/tmp/workers', j.log_uid[:2], j.log_uid, 'attempt1.log')
        self.assertTrue(os.path.isfile(logfile))

        expected_log = dedent("""
        Job run on host: somehost.domain
        blah blah
        """).strip()
        with open(logfile, 'rb') as log:
            self.assertEqual(log.read(), expected_log)

        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                  data=json.dumps({'log': 'blah blah',
                                                   'returncode': 0,
                                                   'host': 'somehost.domain'}))
        self.assertEqual(request.status_code, 200)
        j = Job.query.filter_by(id=1).one()
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.DONE)
        logfile=os.path.join('/tmp/workers', j.log_uid[:2], j.log_uid, 'attempt2.log')
        self.assertTrue(os.path.isfile(logfile))
        with open(logfile, 'rb') as log:
            self.assertEqual(log.read(), expected_log)

    @mock.patch.object(HRService.HRService, 'check_token')
    def test_post_job(self, mock_hrservice):
        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data=json.dumps({'blah': 12}))
        self.assertEqual(request.status_code, 400)

        mock_hrservice.return_value = 1
        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data=json.dumps({'type': JobType.LIST, 'src_siteid': 12, 'src_filepath': '/data/somefile', 'dst_siteid': 15}))
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)

        Job = self.__service.test_db().tables.Job
        j = Job.query.filter_by(user_id=1).one()
        self.assertIsNotNone(j)
        self.assertEqual(j, returned_job)
        self.assertEqual(j.status, JobStatus.NEW)
        self.assertEqual(j.type, JobType.LIST)
        self.assertEqual(j.src_siteid, 12)
        self.assertEqual(j.src_filepath, '/data/somefile')
        self.assertIsNone(j.dst_siteid)
