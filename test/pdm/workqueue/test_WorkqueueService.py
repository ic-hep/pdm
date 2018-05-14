import os
import json
import unittest
from textwrap import dedent
import mock

from pdm.framework.FlaskWrapper import FlaskServer
from pdm.workqueue.WorkqueueDB import JobType, JobStatus, JobProtocol
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
        JobElement = db.tables.JobElement
        db.session.add(Job(user_id=1, src_siteid=13,
                           src_filepath='/data/somefile1', type=JobType.LIST))
        job = Job(user_id=2, src_siteid=14,
                  src_filepath='/data/somefile2', type=JobType.REMOVE)
        for i in xrange(1, 6):
            job.elements.append(JobElement(id=i, job_id=2, src_siteid=12,
                                           src_filepath='/data/somefile2.%d' % i,
                                           type=JobType.REMOVE, size=10**i))
        db.session.add(job)
        db.session.add(Job(user_id=3, src_siteid=15, src_filepath='/data/somefile3',
                           dst_siteid=16, dst_filepath='/data/newfile', type=JobType.COPY))
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup
        self.__test = self.__service.test_client()

    def test_get_next_job(self):
        """test worker get next job."""
        request = self.__test.post('/workqueue/api/v1.0/worker/jobs', data={'test': 12})
        self.assertEqual(request.status_code, 400, "Expected job with incorrect attrs to fail.")
        request = self.__test.post('/workqueue/api/v1.0/worker/jobs', data={'types': [JobType.LIST]})
        self.assertEqual(request.status_code, 200, "Request to get worker job failed.")
        work = json.loads(request.data)
        self.assertEqual(len(work), 1)
        job = work[0]
        self.assertEqual(len(job['elements']), 1)
        self.assertDictContainsSubset({'status': JobStatus.SUBMITTED,
                                       'dst_credentials': None,
                                       'user_id': 1,
                                       'src_filepath': '/data/somefile1',
                                       'priority': 5,
                                       'dst_siteid': None,
                                       'src_siteid': 13,
                                       'extra_opts': None,
                                       'protocol': 0,
                                       'type': JobType.LIST,
                                       'id': 1,
                                       'src_credentials': None,
                                       'dst_filepath': None}, job)#,  "Job not returned correctly.")

        element = job['elements'][0]
        self.assertIsInstance(element['token'], basestring)
        self.assertDictContainsSubset({'status': JobStatus.SUBMITTED,
                                       'job_id': 1,
                                       'attempts': 0,
                                       'src_filepath': '/data/somefile1',
                                       'listing': None,
                                       'max_tries': 2,
                                       'type': JobType.LIST,
                                       'id': 0,
                                       'dst_filepath': None}, element)
        Job = self.__service.test_db().tables.Job
        JobElement = self.__service.test_db().tables.JobElement
        #j = Job.query.filter_by(id=job['id']).one()
        j = Job.query.filter_by(id=job['id']).one()
        je = JobElement.query.filter_by(id=element['id'], job_id=element['job_id']).one()
        self.assertIsNotNone(j)
        self.assertIsNotNone(je)
        self.assertEqual(j.status, JobStatus.SUBMITTED, "Job status not updated in DB")
        self.assertEqual(je.status, JobStatus.SUBMITTED, "Job status not updated in DB")

        request = self.__test.post('/workqueue/api/v1.0/worker/jobs', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")
        work = json.loads(request.data)
        self.assertEqual(len(work), 2)
        self.assertEqual(work[0]['type'], JobType.REMOVE)
        self.assertEqual(len(work[0]['elements']), 6)
        self.assertEqual(work[0]['elements'][0]['type'], JobType.LIST)
        for i in xrange(1, 6):
            self.assertEqual(work[0]['elements'][i]['type'], JobType.REMOVE)
        self.assertEqual(work[1]['type'], JobType.COPY)
        self.assertEqual(len(work[1]['elements']), 1)
        # up to 10 loaded now at once
        #request = self.__test.post('/workqueue/api/v1.0/worker/jobs', data={'types': [JobType.COPY, JobType.REMOVE]})
        #self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")
        request = self.__test.post('/workqueue/api/v1.0/worker/jobs', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 404, "Trying to get a job that doesn't exist should return 404.")

    def test_return_output(self):
        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/2',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "12")
        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/2',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "1.2")
        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/2',
                                   data={'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 400)

        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/2',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 404)

        self.__service.fake_auth("TOKEN", "1.0")
        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/0',
                                   data={'log': 'blah blah',
                                         'returncode': 1,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 400)
        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/0',
                                   data={'log': 'blah blah',
                                         'returncode': 1,
                                         'host': 'somehost.domain',
                                         'listing': {'root': []}})
        self.assertEqual(request.status_code, 200)
        Job = self.__service.test_db().tables.Job
        JobElement = self.__service.test_db().tables.JobElement
        je = JobElement.query.filter_by(job_id=1, id=0).one()
        j = Job.query.filter_by(id=1).one()
        self.assertIsNotNone(je)
        self.assertEqual(je.status, JobStatus.FAILED)
        self.assertEqual(je.job.status, JobStatus.FAILED)
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.FAILED)
        logfile = os.path.join('/tmp/workers', j.log_uid[:2], j.log_uid, str(je.id), 'attempt1.log')
        self.assertTrue(os.path.isfile(logfile))

        expected_log = dedent("""
        Job run on host: somehost.domain
        blah blah
        """).strip()
        with open(logfile, 'rb') as log:
            self.assertEqual(log.read(), expected_log)

        request = self.__test.put('/workqueue/api/v1.0/worker/jobs/1/elements/0',
                                  data={'log': 'blah blah',
                                        'returncode': 0,
                                        'host': 'somehost.domain',
                                        'listing': {'root': []}})
        self.assertEqual(request.status_code, 200)
        je = JobElement.query.filter_by(job_id=1, id=0).one()
        j = Job.query.filter_by(id=1).one()
        self.assertIsNotNone(je)
        self.assertEqual(je.status, JobStatus.DONE)
        self.assertEqual(je.job.status, JobStatus.DONE)
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.DONE)
        logfile = os.path.join('/tmp/workers', j.log_uid[:2], j.log_uid, str(je.id), 'attempt2.log')
        self.assertTrue(os.path.isfile(logfile))
        with open(logfile, 'rb') as log:
            self.assertEqual(log.read(), expected_log)
        self.assertEqual(je.listing, {'root': []})

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_post_job(self, mock_hrservice):
        Job = self.__service.test_db().tables.Job

        mock_hrservice.return_value = 10
        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data={'blah': 12})
        self.assertEqual(request.status_code, 400)

        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data={'type': JobType.LIST,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile',
                                         'dst_siteid': 15})
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        job = Job.query.filter_by(user_id=10).one()
        self.assertIsNotNone(job)
        self.assertEqual(returned_job, json.loads(job.json()))
        self.assertEqual(job.status, JobStatus.NEW)
        self.assertEqual(returned_job['status'], 'NEW')
        self.assertEqual(job.type, JobType.LIST)
        self.assertEqual(returned_job['type'], 'LIST')
        self.assertEqual(job.priority, 5)
        self.assertEqual(job.protocol, JobProtocol.GRIDFTP)
        self.assertEqual(returned_job['protocol'], 'GRIDFTP')
        self.assertIsInstance(job.log_uid, basestring)
        self.assertEqual(len(job.elements), 1)
        element = job.elements[0]
        self.assertEqual(element.type, JobType.LIST)
        self.assertEqual(element.src_filepath, '/data/somefile')
        self.assertIsNone(element.dst_filepath)
        self.assertEqual(element.attempts, 0)
        self.assertEqual(element.max_tries, 2)

        mock_hrservice.return_value = 12
        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data={'type': JobType.COPY,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile',
                                         'dst_siteid': 15})
        self.assertEqual(request.status_code, 400)

        request = self.__test.post('/workqueue/api/v1.0/jobs',
                                   data={'type': JobType.COPY,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile',
                                         'src_credentials': 'somesecret',
                                         'dst_siteid': 15,
                                         'dst_filepath': '/data/someotherfile',
                                         'dst_credentials': 'someothersecret',
                                         'extra_opts': 'blah',
                                         'attempts': 30,
                                         'max_tries': 3,
                                         'priority': 2,
                                         'protocol': JobProtocol.SSH,
                                         'log_uid': 'my_log_uid'})
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        job = Job.query.filter_by(user_id=12).one()
        self.assertIsNotNone(job)
        self.assertEqual(returned_job, json.loads(job.json()))
        self.assertEqual(job.status, JobStatus.NEW)
        self.assertEqual(returned_job['status'], 'NEW')
        self.assertEqual(job.type, JobType.COPY)
        self.assertEqual(returned_job['type'], 'COPY')
        self.assertEqual(job.priority, 2)
        self.assertEqual(job.protocol, JobProtocol.SSH)
        self.assertEqual(returned_job['protocol'], 'SSH')
        self.assertIsInstance(job.log_uid, basestring)
        self.assertNotEqual(job.log_uid, 'my_log_uid')
        self.assertEqual(len(job.elements), 1)
        element = job.elements[0]
        self.assertEqual(element.type, JobType.LIST)
        self.assertEqual(element.src_filepath, '/data/somefile')
        self.assertEqual(element.dst_filepath, '/data/someotherfile')
        self.assertEqual(element.attempts, 0)
        self.assertEqual(element.max_tries, 3)

#    @mock.patch.object(HRService.HRService, 'check_token')
    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_list(self, mock_hrservice):
        Job = self.__service.test_db().tables.Job

        mock_hrservice.return_value = 10
        request = self.__test.post('/workqueue/api/v1.0/list',
                                   data={'type': JobType.COPY,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile'})
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        job = Job.query.filter_by(user_id=10).one()
        self.assertIsNotNone(job)
        self.assertEqual(returned_job, json.loads(job.json()))
        self.assertEqual(job.type, JobType.LIST)
        self.assertEqual(returned_job['type'], 'LIST')

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_copy(self, mock_hrservice):
        Job = self.__service.test_db().tables.Job

        mock_hrservice.return_value = 10
        request = self.__test.post('/workqueue/api/v1.0/copy',
                                   data={'type': JobType.LIST,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile',
                                         'dst_siteid': 15,
                                         'dst_filepath': '/data/someotherfile'})
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        job = Job.query.filter_by(user_id=10).one()
        self.assertIsNotNone(job)
        self.assertEqual(returned_job, json.loads(job.json()))
        self.assertEqual(job.type, JobType.COPY)
        self.assertEqual(returned_job['type'], 'COPY')

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_remove(self, mock_hrservice):
        Job = self.__service.test_db().tables.Job

        mock_hrservice.return_value = 10
        request = self.__test.post('/workqueue/api/v1.0/remove',
                                   data={'type': JobType.COPY,
                                         'src_siteid': 12,
                                         'src_filepath': '/data/somefile'})
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        job = Job.query.filter_by(user_id=10).one()
        self.assertIsNotNone(job)
        self.assertEqual(returned_job, json.loads(job.json()))
        self.assertEqual(job.type, JobType.REMOVE)
        self.assertEqual(returned_job['type'], 'REMOVE')

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_jobs(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs')
        self.assertEqual(request.status_code, 200)
        returned_jobs = json.loads(request.data)
        self.assertEqual(returned_jobs, [])

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs')
        self.assertEqual(request.status_code, 200)
        returned_jobs = json.loads(request.data)
        self.assertEqual(len(returned_jobs), 1)
        self.assertDictContainsSubset({'user_id': 1,
                                       'type': 'LIST',
                                       'status': 'NEW'}, returned_jobs[0])

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_job(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/2')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/1')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/2')
        self.assertEqual(request.status_code, 200)
        returned_job = json.loads(request.data)
        self.assertDictContainsSubset({'user_id': 2,
                                       'type': 'REMOVE',
                                       'status': 'NEW'}, returned_job)

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_elements(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements')
        self.assertEqual(request.status_code, 200)
        returned_elements = json.loads(request.data)
        self.assertEqual(returned_elements, [])

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements')
        self.assertEqual(request.status_code, 200)
        returned_elements = json.loads(request.data)
        self.assertEqual(len(returned_elements), 1)
        self.assertDictContainsSubset({'job_id': 1,
                                       'type': 'LIST',
                                       'status': 'NEW'}, returned_elements[0])

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_element(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/0')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/33')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/0')
        self.assertEqual(request.status_code, 200)
        returned_element = json.loads(request.data)
        self.assertDictContainsSubset({'job_id': 2,
                                       'type': 'LIST',
                                       'status': 'NEW'}, returned_element)

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_job_status(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/3/status')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 3
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/status')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 3
        request = self.__test.get('/workqueue/api/v1.0/jobs/3/status')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 3,
                                         'status': 'NEW'})

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_element_status(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0/status')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/17/status')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/12/elements/0/status')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 3
        request = self.__test.get('/workqueue/api/v1.0/jobs/3/elements/0/status')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 3,
                                         'elementid': 0,
                                         'status': 'NEW',
                                         'attempts': 0})

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_output(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 404, "invalid userid should give 404")

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/output')
        self.assertEqual(request.status_code, 404, "userid not matching job id should give 404")

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/10/output')
        self.assertEqual(request.status_code, 404, "Unknown element id should give 404")

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0/output')
        self.assertEqual(request.status_code, 404, "Status other than DONE or FAILED gives 404")

        db = self.__service.test_db()
        session = db.session
        list_job = db.tables.Job.query.filter_by(user_id=1).one()
        remove_job = db.tables.Job.query.filter_by(user_id=2).one()
        self.assertIsNotNone(list_job)
        self.assertIsNotNone(remove_job)

        list_job.status = JobStatus.DONE
        remove_job.status = JobStatus.FAILED
        list_job.elements[0].status = JobStatus.DONE
        remove_job.elements[0].status = JobStatus.FAILED
        remove_job.elements[1].status = JobStatus.FAILED
        session.merge(list_job)
        session.merge(remove_job)
        session.expunge(list_job)
        session.expunge(remove_job)
        session.commit()

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0/output')
        self.assertEqual(request.status_code, 404, "Element with 0 attempts is not yet ready, should give 404")

        list_job.elements[0].attempts = 1
        remove_job.elements[0].attempts = 1
        remove_job.elements[1].attempts = 1
        list_job.elements[0].listing = {'root': [{'name': 'somefile'}]}
        remove_job.elements[0].listing = {'root': [{'name': 'somefile'}]}
        session.merge(list_job)
        session.merge(remove_job)
        session.commit()

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0/output/9')
        self.assertEqual(request.status_code, 400, "Invalid attempt should give 400")

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/elements/0/output/1')
        self.assertEqual(request.status_code, 500, "Failure to find logfile should give 500")

        list_job_dir = os.path.join('/tmp/workers',
                                    list_job.log_uid[:2],
                                    list_job.log_uid,
                                    '0')
        remove_job_dir = os.path.join('/tmp/workers',
                                      remove_job.log_uid[:2],
                                      remove_job.log_uid)
        remove_job0_dir = os.path.join(remove_job_dir, '0')
        remove_job1_dir = os.path.join(remove_job_dir, '1')
        list_job_filename = os.path.join(list_job_dir, "attempt1.log")
        remove_job0_filename = os.path.join(remove_job0_dir, "attempt1.log")
        remove_job1_filename = os.path.join(remove_job1_dir, "attempt1.log")
        if not os.path.exists(list_job_dir):
            os.makedirs(list_job_dir)
        if not os.path.exists(remove_job0_dir):
            os.makedirs(remove_job0_dir)
        if not os.path.exists(remove_job1_dir):
            os.makedirs(remove_job1_dir)
        with open(list_job_filename, 'wb') as listlog,\
                open(remove_job0_filename, 'wb') as removelog0,\
                open(remove_job1_filename, 'wb') as removelog1:
            listlog.write('la la la\n')
            removelog0.write('blah blah\n')
            removelog1.write('tralala\n')

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'elementid': 0, 'type': 'LIST',
                                         'log': 'blah blah\n', 'listing': {'root': [{'name': 'somefile'}]}})

        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/0/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'elementid': 0, 'type': 'LIST',
                                         'log': 'blah blah\n', 'listing': {'root': [{'name': 'somefile'}]}})

        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/0/output/1')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'elementid': 0, 'type': 'LIST',
                                         'log': 'blah blah\n', 'listing': {'root': [{'name': 'somefile'}]}})

        request = self.__test.get('/workqueue/api/v1.0/jobs/2/elements/1/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'elementid': 1, 'type': 'REMOVE',
                                         'log': 'tralala\n'})

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 1, 'elementid': 0, 'type': 'LIST',
                                         'log': 'la la la\n',
                                         'listing': {'root': [{'name': 'somefile'}]}})

## check jobs in status
## check check_token is called
## dont hardcode /tmp/workerslogs get it from self.config
