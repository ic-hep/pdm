import os
import json
import unittest
from textwrap import dedent
import mock

from pdm.framework.FlaskWrapper import FlaskServer
from pdm.workqueue.WorkqueueDB import JobType, JobStatus, JobProtocol, WorkqueueJobEncoder
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
        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.LIST]})
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

        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")

        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 200, "Failed to get copy or remove job.")
        request = self.__test.post('/workqueue/api/v1.0/worker', data={'types': [JobType.COPY, JobType.REMOVE]})
        self.assertEqual(request.status_code, 404, "Trying to get a job that doesn't exist should return 404.")

    def test_return_output(self):
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "12")
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 403)

        self.__service.fake_auth("TOKEN", "100")
        request = self.__test.put('/workqueue/api/v1.0/worker/100',
                                   data={'log': 'blah blah',
                                         'returncode': 0,
                                         'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 404)

        self.__service.fake_auth("TOKEN", "1")
        request = self.__test.put('/workqueue/api/v1.0/worker/1',
                                   data={'log': 'blah blah',
                                         'returncode': 1,
                                         'host': 'somehost.domain'})
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
                                  data={'log': 'blah blah',
                                        'returncode': 0,
                                        'host': 'somehost.domain'})
        self.assertEqual(request.status_code, 200)
        j = Job.query.filter_by(id=1).one()
        self.assertIsNotNone(j)
        self.assertEqual(j.status, JobStatus.DONE)
        logfile=os.path.join('/tmp/workers', j.log_uid[:2], j.log_uid, 'attempt2.log')
        self.assertTrue(os.path.isfile(logfile))
        with open(logfile, 'rb') as log:
            self.assertEqual(log.read(), expected_log)

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
        self.assertEqual(returned_job, json.loads(json.dumps(job, cls=WorkqueueJobEncoder)))
        self.assertEqual(job.status, JobStatus.NEW)
        self.assertEqual(returned_job['status'], 'NEW')
        self.assertEqual(job.type, JobType.LIST)
        self.assertEqual(returned_job['type'], 'LIST')
        self.assertEqual(job.src_siteid, 12)
        self.assertEqual(job.src_filepath, '/data/somefile')
        self.assertIsNone(job.dst_siteid)
        self.assertIsNone(job.dst_filepath)
        self.assertIsNone(job.credentials)
        self.assertIsNone(job.extra_opts)
        self.assertEqual(job.attempts, 0)
        self.assertEqual(job.max_tries, 2)
        self.assertEqual(job.priority, 5)
        self.assertEqual(job.protocol, JobProtocol.GRIDFTP)
        self.assertEqual(returned_job['protocol'], 'GRIDFTP')
        self.assertIsInstance(job.log_uid, basestring)

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
                                         'dst_siteid': 15,
                                         'dst_filepath': '/data/someotherfile',
                                         'credentials': 'somesecret',
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
        self.assertEqual(returned_job, json.loads(json.dumps(job, cls=WorkqueueJobEncoder)))
        self.assertEqual(job.status, JobStatus.NEW)
        self.assertEqual(returned_job['status'], 'NEW')
        self.assertEqual(job.type, JobType.COPY)
        self.assertEqual(returned_job['type'], 'COPY')
        self.assertEqual(job.src_siteid, 12)
        self.assertEqual(job.src_filepath, '/data/somefile')
        self.assertEqual(job.dst_siteid, 15)
        self.assertEqual(job.dst_filepath, '/data/someotherfile')
        self.assertEqual(job.credentials, 'somesecret')
        self.assertEqual(job.extra_opts, 'blah')
        self.assertEqual(job.attempts, 0)
        self.assertEqual(job.max_tries, 3)
        self.assertEqual(job.priority, 2)
        self.assertEqual(job.protocol, JobProtocol.SSH)
        self.assertEqual(returned_job['protocol'], 'SSH')
        self.assertIsInstance(job.log_uid, basestring)
        self.assertNotEqual(job.log_uid, 'my_log_uid')

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
        self.assertEqual(returned_job, json.loads(json.dumps(job, cls=WorkqueueJobEncoder)))
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
        self.assertEqual(returned_job, json.loads(json.dumps(job, cls=WorkqueueJobEncoder)))
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
        self.assertEqual(returned_job, json.loads(json.dumps(job, cls=WorkqueueJobEncoder)))
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
                                       'src_siteid': 13,
                                       'src_filepath': '/data/somefile1',
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
                                       'src_siteid': 14,
                                       'src_filepath': '/data/somefile2',
                                       'type': 'REMOVE',
                                       'status': 'NEW'}, returned_job)

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_status(self, mock_hrservice):
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
                                         'status': 'NEW',
                                         'attempts': 0})

    @mock.patch('pdm.userservicedesk.HRService.HRService.check_token')
    def test_get_output(self, mock_hrservice):
        mock_hrservice.return_value = 10
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/output')
        self.assertEqual(request.status_code, 404)

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 404)

        db = self.__service.test_db()
        session = db.session
        list_job = db.tables.Job.query.filter_by(user_id=1).one()
        remove_job = db.tables.Job.query.filter_by(user_id=2).one()
        self.assertIsNotNone(list_job)
        self.assertIsNotNone(remove_job)
        list_job_dir = os.path.join('/tmp/workers',
                                    list_job.log_uid[:2],
                                    list_job.log_uid)
        remove_job_dir = os.path.join('/tmp/workers',
                                      remove_job.log_uid[:2],
                                      remove_job.log_uid)
        list_job_filename = os.path.join(list_job_dir, "attempt1.log")
        remove_job_filename = os.path.join(remove_job_dir, "attempt1.log")
        session.merge(list_job).status = JobStatus.DONE
        session.merge(remove_job).status = JobStatus.FAILED
        session.commit()

        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 404)
        session.merge(list_job).attempts = 1
        session.merge(remove_job).attempts = 1
        session.commit()

        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output/13')
        self.assertEqual(request.status_code, 400)

        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 500)

        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output/1')
        self.assertEqual(request.status_code, 500)

        if not os.path.exists(list_job_dir):
            os.makedirs(list_job_dir)
        if not os.path.exists(remove_job_dir):
            os.makedirs(remove_job_dir)

        listoutput = dedent('''
        drwx------. 3 arichard res0 4020 Mar 12 16:15 bin/
        drwx------. 4 arichard res0 4001 Feb 14 10:08 test/
        -rw-------. 1 arichard res0  871 Mar  7 15:38 testdata.txt
        -rw-------. 1 arichard res0  604 Mar  7 17:09 test.py
        ''').strip()
        with open(list_job_filename, 'wb') as listlog,\
             open(remove_job_filename, 'wb') as removelog:
            listlog.write(listoutput)
            removelog.write('blah blah\n')

        mock_hrservice.return_value = 2
        request = self.__test.get('/workqueue/api/v1.0/jobs/2/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'log': 'blah blah\n'})

        request = self.__test.get('/workqueue/api/v1.0/jobs/2/output/1')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 2, 'log': 'blah blah\n'})

        mock_hrservice.return_value = 1
        request = self.__test.get('/workqueue/api/v1.0/jobs/1/output')
        self.assertEqual(request.status_code, 200)
        returned_dict = json.loads(request.data)
        self.assertEqual(returned_dict, {'jobid': 1, 'log': listoutput,
                                         'listing': [{'datestamp': 1520871300.0,
                                                      'groupid': 'res0',
                                                      'is_directory': True,
                                                      'name': 'bin/',
                                                      'nlinks': 3,
                                                      'permissions': 'drwx------.',
                                                      'size': 4020,
                                                      'userid': 'arichard'},
                                                     {'datestamp': 1518602880.0,
                                                      'groupid': 'res0',
                                                      'is_directory': True,
                                                      'name': 'test/',
                                                      'nlinks': 4,
                                                      'permissions': 'drwx------.',
                                                      'size': 4001,
                                                      'userid': 'arichard'},
                                                     {'datestamp': 1520437080.0,
                                                      'groupid': 'res0',
                                                      'is_directory': False,
                                                      'name': 'testdata.txt',
                                                      'nlinks': 1,
                                                      'permissions': '-rw-------.',
                                                      'size': 871,
                                                      'userid': 'arichard'},
                                                     {'datestamp': 1520442540.0,
                                                      'groupid': 'res0',
                                                      'is_directory': False,
                                                      'name': 'test.py',
                                                      'nlinks': 1,
                                                      'permissions': '-rw-------.',
                                                      'size': 604,
                                                      'userid': 'arichard'}]})

## check jobs in status
## check check_token is called
## dont hardcode /tmp/workerslogs get it from self.config
