import json
import os
import time
import unittest
import mock
import copy
import datetime
import smtplib

from pdm.userservicedesk.HRService import HRService
from pdm.userservicedesk.HRService import HRServiceUserState
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.utils.hashing import hash_pass, check_hash
from pdm.framework.Tokens import TokenService


class HRServiceTestConfig:
    def __init__(self, config={}):
        self._config = config

    def set_config(self, config):
        self._config = config

    def get_config(self):
        return self._config


class TestHRService(unittest.TestCase):
    @mock.patch("pdm.userservicedesk.HRService.SiteClient")
    def setUp(self, site_mock):
        self.__site_mock = site_mock
        conf = {'token_validity': '01:00:00', 'SMTP_server': 'localhost',
                'verification_url': 'https://pdm.grid.hep.ph.ic.ac.uk:5443/web/verify',
                'SMTP_server_login': 'centos@localhost', 'SMTP_startTLS': 'OPTIONAL',
                'SMTP_login_req': 'OPTIONAL',
                'display_from_address': 'PDM mailer <centos@localhost>',
                'mail_subject': 'PDM registration - please verify your email address.',
                'mail_expiry': '12:00:00', 'mail_token_secret': 'somemailsecretstring'}
        self._conf = copy.deepcopy(conf)
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)  # to skip DB auto build
        self.__service.fake_auth("ALL")
        self.__future_date = (datetime.timedelta(0, 600) + datetime.datetime.utcnow()).isoformat()
        self.__past_date = (-datetime.timedelta(0, 60) + datetime.datetime.utcnow()).isoformat()
        # database
        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        new_user = db.tables.User(
            name='John', surname='Smith',
            email='Johnny@example.com', state=HRServiceUserState.VERIFIED,
            password=hash_pass('very_secret'))
        db.session.add(new_user)
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup
        #
        self.__test = self.__service.test_client()
        # mail token
        time_struct = time.strptime("12:00:00", "%H:%M:%S")
        self.token_duration = datetime.timedelta(hours=time_struct.tm_hour,
                                            minutes=time_struct.tm_min,
                                            seconds=time_struct.tm_sec)
        self.token_service = TokenService(self._conf['mail_token_secret'])

    def test_getUserSelf(self):
        """
        GET operation on users/self
        :return:
        """

        self.__service.fake_auth("TOKEN", {'id': 1})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 500)

        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__past_date})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 403)  # token expired

        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__future_date, 'key': 'unused'})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 200)
        user = json.loads(res.data)

        assert ('id' not in user)
        assert (user['name'] == 'John')
        assert (user['surname'] == 'Smith')
        assert (user['email'] == 'Johnny@example.com')
        assert (user['state'] == HRServiceUserState.VERIFIED)
        assert ('password' not in user)
        #
        self.__service.fake_auth("TOKEN", {'id': 2, 'expiry': self.__future_date})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 404)

    @mock.patch("pdm.userservicedesk.HRService.HRService.email_user")
    def test_addUser(self, email_user_mock):
        """
        Testinf user registration. Ignore emailer at this stage.
        :return:
        """
        self.__service.fake_auth("ALL")
        fred = {
            'surname': 'Flintstone',
            'name': 'Fred',
            'email': 'fred@flintstones.com',
            'state': 0, 'password': 'Wilma007'}

        barney = {
            'surname': 'Rubble',
            'name': 'Barney',
            'email': 'barney@rubbles.com',
            'state': 0, 'password': 'Betty'}

        res = self.__test.post('/users/api/v1.0/users', data=fred)

        assert (res.status_code == 201)
        # db
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email=fred['email']).first()
        assert (dbuser.name == fred['name'])
        assert (check_hash(dbuser.password, fred['password']))
        assert (dbuser.email == fred['email'])
        response = json.loads(res.data)
        assert (response['name'] == fred['name'])
        assert (response['surname'] == fred['surname'])
        assert (response['email'] == fred['email'])
        assert (response['state'] == fred['state'])
        assert ('password' not in response)
        # try to duplicate the user:
        res = self.__test.post('/users/api/v1.0/users', data=fred)
        assert (res.status_code == 403)

        # password too short !
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)
        # barney OK, but verification email sending fails:
        barney['password'] = 'Betty007'
        email_user_mock.side_effect = RuntimeError
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 500)
        #
        b_email = barney.pop('email')
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)

        barney['email'] = b_email
        password = barney.pop('password')
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)

    def test_change_password(self):
        """
        Test the password changing operation
        :return:
        """

        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__past_date})
        new_pass_data = {'passwd': 'very_secret', 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 403)

        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__future_date})
        # fake auth John, which is id=1
        new_pass_data = {'passwd': 'very_secret', 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 200)
        # check if the password was actually modified:
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert (dbuser.name == "John")
        assert (check_hash(dbuser.password, 'even_more_secret'))
        #
        response = json.loads(res.data)
        assert ('password' not in response)
        # TODO check last login timestamp later than the time before changing the password.
        # wrong password
        wrong_pass_data = {'passwd': 'very_sercet', 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=wrong_pass_data)
        assert (res.status_code == 403)
        # same pass
        same_pass_data = {'passwd': 'even_more_secret', 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=same_pass_data)
        assert (res.status_code == 400)
        # no pass
        no_pass = {'passwd': None, 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 400)
        no_pass = {'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 400)
        no_pass = {'passwd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 400)
        #
        no_npass = {'passwd': 'even_more_secret', 'newpasswd': None}
        res = self.__test.put('/users/api/v1.0/passwd', data=no_npass)
        assert (res.status_code == 400)
        # weak pass
        weak_pass = {'passwd': 'even_more_secret', 'newpasswd': 'test'}
        res = self.__test.put('/users/api/v1.0/passwd', data=weak_pass)
        assert (res.status_code == 400)
        # non existing user
        self.__service.fake_auth("TOKEN", {'id': 7, 'expiry': self.__future_date})
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 403)

    # @mock.patch('pdm.userservicedesk.HRService.SiteClient')

    def test_delete_user(self):
        """
        Test deleting user data
        :return:
        """
        # not existing user:
        self.__service.fake_auth("TOKEN", {'id': 7, 'expiry': self.__future_date})
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 404)
        assert not self.__site_mock().del_user.called
        # attempt to delete Johnny with an expired token
        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__past_date,
                                           'key': 'unused'})  # fake auth John, which is id=1
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 403)
        assert not self.__site_mock().del_user.called
        # delete poor Johnny ;-(
        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__future_date,
                                           'key': 'unused'})  # fake auth John, which is id=1
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 200)
        assert self.__site_mock().del_user.called

    def test_deleteUser_SiteService_fail(self):
        """
        Test if the user is put back when SiteService fails
        :param mock_del_user:
        :return:
        """
        # delete poor Johnny ;-(
        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__future_date})
        # fake auth John, which is id=1
        self.__site_mock().del_user.side_effect = Exception()
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 500)
        assert self.__site_mock().del_user.called
        # check if we rolled John  back !
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert (dbuser is not None)

    @mock.patch('sqlalchemy.orm.scoping.scoped_session.delete')
    def test_deleteUser_HR_fail(self, mock_del):
        self.__service.fake_auth("TOKEN", {'id': 1, 'expiry': self.__future_date})
        # fake auth John, which is id=1
        mock_del.side_effect = Exception()
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 500)
        assert not self.__site_mock().del_user.called

    def test_loginUser(self):
        """
        Test the user login procedure
        :return:
        """

        res = self.__test.post('/users/api/v1.0/login')  # empty req.
        assert (res.status_code == 400)

        res = self.__test.post('/users/api/v1.0/login', data=('hulagula'))
        assert (res.status_code == 400)

        login_creds = {'email': 'Johnny@example.com', 'passwd': 'very_secret'}
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
        assert (res.status_code == 200)
        #
        token_data = self.__service.token_svc.check(json.loads(res.data))
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert token_data['id'] == 1

        isoformat = '%Y-%m-%dT%H:%M:%S.%f'
        expiry_date = datetime.datetime.strptime(token_data['expiry'], isoformat)
        # conf gives 1h token validity. Check if we are within 10s
        assert abs((expiry_date - (datetime.datetime.utcnow() + datetime.timedelta(0, 3600))).total_seconds()) < 10

        login_creds_b = {'email': 'Johnny@example.com'}
        res = self.__test.post('/users/api/v1.0/login', data=login_creds_b)
        assert (res.status_code == 400)
        res = self.__test.post('/users/api/v1.0/login',
                               data={'email': 'Johnny@example.com', 'passwd': 'very_seCret'})
        assert (res.status_code == 403)
        res = self.__test.post('/users/api/v1.0/login',
                               data={'email': 'johnny@example.com', 'passwd': 'very_secret'})
        assert (res.status_code == 403)
        res = self.__test.post('/users/api/v1.0/login',
                               data={'email': 'johnny@example.com', 'passwd': None})
        assert (res.status_code == 400)
        # make Johny unverified ;-(
        dbuser.state = HRServiceUserState.REGISTERED
        db.session.add(dbuser)
        db.session.commit()
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
        assert (res.status_code == 401)

    def test_email_user(self):
        pass

    def test_verify_user(self):
        # isssue a valid mail token
        expiry = datetime.datetime.utcnow() + self.token_duration
        plain = {'expiry': expiry.isoformat(), 'email': 'Johnny@example.com'}
        token = self.token_service.issue(plain)
        #body = os.path.join(self._conf['verification_url'],token)
        # verify takes a token only, not the whole email body at the moment
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        dbuser.state = HRServiceUserState.REGISTERED # unverify !
        db.session.add(dbuser)
        db.session.commit()

        #token tempered with:
        res = self.__test.post('/users/api/v1.0/verify', data={'mailtoken': token[1:]})
        assert res.status_code == 400

        # success ?
        res = self.__test.post('/users/api/v1.0/verify', data={'mailtoken': token})
        assert res.status_code == 201

        #repeat a verification attempt
        dbuser.state = HRServiceUserState.VERIFIED
        db.session.add(dbuser)
        db.session.commit()
        res = self.__test.post('/users/api/v1.0/verify', data={'mailtoken': token})
        assert res.status_code == 400

        # expired token
        dbuser.state = HRServiceUserState.REGISTERED # unverify !
        db.session.add(dbuser)
        db.session.commit()
        expired = datetime.datetime.utcnow() - self.token_duration
        e_plain = {'expiry': expired.isoformat(), 'email': 'Johnny@example.com'}
        e_token = self.token_service.issue(e_plain)
        res = self.__test.post('/users/api/v1.0/verify', data={'mailtoken': e_token})
        assert res.status_code == 400

        # non existent user:
        plain = {'expiry': expiry.isoformat(), 'email': 'Fred@example.com'}
        token = self.token_service.issue(plain)
        res = self.__test.post('/users/api/v1.0/verify', data={'mailtoken': token})
        assert res.status_code == 400


    @mock.patch('email.MIMEMultipart.MIMEMultipart')
    @mock.patch.object(smtplib.SMTP, 'connect')
    @mock.patch.object(smtplib.SMTP, 'close')
    def test_compose_and_send(self, close_mock, connect_mock, mail_mock):
        with self.__service.test_request_context(path="/test"):
            # force connect to raise the SMTPException derived class. HRService wraps it into
            # RuntimeError
            connect_mock.return_value = (400, 'cannot connect message')  # 220 is the success code
            with self.assertRaises(RuntimeError):
                HRService.compose_and_send("centos@localhost", 'mytoken_abc')
            connect_mock.assert_called_with('localhost', None)  # from conf{}

            # now allow for connect() to raise a socket.error
            import socket
            connect_mock.side_effect = socket.error
            with self.assertRaises(RuntimeError):
                HRService.compose_and_send("centos@localhost", 'mytoken_abc')

    @mock.patch('email.MIMEMultipart.MIMEMultipart')
    @mock.patch('smtplib.SMTP')
    def test_compose_and_send_sendmail(self, smtp_mock, mail_mock):
        with self.__service.test_request_context(path="/test"):
            # sendmail errors
            mytoken = 'mytoken_abc'
            toaddr = "user@remotehost"
            body = os.path.join(self._conf['verification_url'], mytoken)
            smtp_mock.return_value.sendmail.side_effect = smtplib.SMTPException
            with self.assertRaises(RuntimeError):
                HRService.compose_and_send(toaddr, mytoken)
            args = smtp_mock.return_value.sendmail.call_args
            assert args[0][0] == self._conf['SMTP_server_login']
            assert args[0][1] == toaddr
            assert body in args[0][2]  # check the important part of the email

    def test_hello(self):
        res = self.__test.get('/users/api/v1.0/hello')
        assert (res.status_code == 200)
        res_str = json.loads(res.data)
        assert (res_str == 'User Service Desk at your service !\n')
