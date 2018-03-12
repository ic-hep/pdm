import json
import unittest
import mock

from pdm.framework.FlaskWrapper import FlaskServer
from pdm.workqueue.WorkqueueDB import JobType, JobStatus

class TestWorkqueueService(unittest.TestCase):
    def setUp(self):
        conf = {}
        self.__service = FlaskServer("pdm.workqueue.WorkqueueService")
#        self.__service.test_mode(HRService, None)  # to skip DB auto build
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
#        self.__service.fake_auth("TOKEN", "User_1")
        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.LIST]})
        self.assertEqual(request.status_code, 200, "Request to get worker job failed.")
        job, token = json.loads(request.data)
        self.assertEqual(job.user_id, 1, "User id is not correct.")
        self.assertEqual(job.src_siteid, 13, "Src_siteid is wrong.")
        self.assertEqual(job.src_filepath, '/data/somefile1', "src_filepath is wrong")
        self.assertEqual(job.type, JobType.LIST, "Job type is wrong")
        self.assertEqual(job.status, JobStatus.SUBMITTED, "Job status not changed to submitted in returned job")
        self.assertEqual(token, str(job.id), "Token and job.id do not match.")
        Job = self.__service.test_db().tables.Job
        j = Job.query().filter_by(id=job.id).one_or_none()
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.SUBMITTED, "Job status not updated in DB")

        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")

        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")
        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 404, "Trying to get a job that doesn't exist should return 404.")

