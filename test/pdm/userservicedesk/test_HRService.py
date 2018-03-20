import json
import unittest
import mock

from pdm.userservicedesk.HRService import HRService
from pdm.cred.CredClient import MockCredClient
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.utils.hashing import hash_pass, check_hash
from pdm.framework.Tokens import TokenService


class TestHRService(unittest.TestCase):

    @mock.patch("pdm.userservicedesk.HRService.CredClient")
    def setUp(self, cred_mock):
        cred_mock.return_value = MockCredClient()
        conf = {'CS_secret':'HJGnbfdsV'}
        self.__service = FlaskServer("pdm.userservicedesk.HRService")
        self.__service.test_mode(HRService, None)  # to skip DB auto build
        self.__service.fake_auth("ALL")
        # database
        # self.__service.test_mode(HRService, None)
        self.__service.build_db()  # build manually
        #
        db = self.__service.test_db()
        new_user = db.tables.User(
            name='John', surname='Smith',
            email='Johnny@example.com', state=0,
            password=hash_pass('very_secret'))
        db.session.add(new_user)
        db.session.commit()
        self.__service.before_startup(conf)  # to continue startup
        #
        self.__test = self.__service.test_client()

    def test_getUserSelf(self):
        """
        GET operation on users/self
        :return:
        """
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 200)
        user = json.loads(res.data)

        assert ('id' not in user)
        assert (user['name'] == 'John')
        assert (user['surname'] == 'Smith')
        assert (user['email'] == 'Johnny@example.com')
        assert (user['state'] == 0)
        assert ('password' not in user)
        #
        self.__service.fake_auth("TOKEN", {'id':2, 'expiry':None, 'key': 'unused'})
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 404)

    def test_addUser(self):
        """

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
        #
        b_email = barney.pop('email')
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)

        barney['email'] = b_email
        password = barney.pop('password')
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)

    @mock.patch('pdm.cred.CredClient.MockCredClient.add_user')
    def test_add_user_CS_OK(self, mock_add_user):
        fred = {
            'surname': 'Flintstone',
            'name': 'Fred',
            'email': 'fred@flintstones.com',
            'state': 0, 'password': 'Wilma007'}

        res = self.__test.post('/users/api/v1.0/users', data=fred)
        assert (res.status_code == 201)
        assert mock_add_user.called

    @mock.patch('pdm.cred.CredClient.MockCredClient.add_user')
    def test_add_user_HR_fail(self, mock_add_user):
        # now we fail the HRSErvice call (no password)
        barney = {
            'surname': 'Rubble',
            'name': 'Barney',
            'email': 'barney@rubbles.com',
            'state': 0,}
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 400)
        assert not mock_add_user.called

    @mock.patch('pdm.cred.CredClient.MockCredClient.add_user')
    def test_add_user_CS_fail(self, mock_add_user):
        # now we fail the CS SErvice call
        barney = {
            'surname': 'Rubble',
            'name': 'Barney',
            'email': 'barney@rubbles.com',
            'state': 0, 'password' : 'Wilma007'}
        mock_add_user.side_effect = Exception()
        res = self.__test.post('/users/api/v1.0/users', data=barney)
        assert (res.status_code == 403)
        assert mock_add_user.called # so the HR did not throw !
        # check if we rolled Barney back !
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email=barney['email']).first()
        assert (dbuser is None)

    def test_change_password(self):
        """
        Test the password changing operation
        :return:
        """
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
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
        self.__service.fake_auth("TOKEN", {'id':7, 'expiry':None, 'key': 'unused'})
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 403)

    @mock.patch('pdm.cred.CredClient.MockCredClient.add_user')
    def test_change_password_CS_OK(self, mock_add_user):
        """
        :param mock_add_user: Only test HR, CS transaction, not the password detail
        :return:
        """
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
        new_pass_data = {'passwd': 'very_secret', 'newpasswd': 'even_more_secret'}
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 200)
        assert mock_add_user.called


    @mock.patch('pdm.cred.CredClient.MockCredClient.add_user')
    def test_change_password_CS_fail(self, mock_add_user):
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
        new_pass_data = {'passwd': 'very_secret', 'newpasswd': 'even_more_secret'}
        mock_add_user.side_effect = Exception()
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 500)
        assert mock_add_user.called
        # check if the password was NOT modified:
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert (dbuser.name == "John")
        assert (check_hash(dbuser.password, 'very_secret'))

    @mock.patch('pdm.cred.CredClient.MockCredClient.del_user')
    def test_delete_user(self, mock_del_user):
        """
        Test deleting user data
        :return:
        """
        # not existing user:
        self.__service.fake_auth("TOKEN", {'id':7, 'expiry':None, 'key': 'unused'})
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 404)
        assert not mock_del_user.called

        # delete poor Johny ;-(
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 200)
        assert mock_del_user.called

    @mock.patch('pdm.cred.CredClient.MockCredClient.del_user')
    def test_deleteUser_CS_fail(self, mock_del_user):
        """
        Test if the user is put back when CS fails
        :param mock_del_user:
        :return:
        """

        # delete poor Johny ;-(
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
        mock_del_user.side_effect = Exception()
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 500)
        assert mock_del_user.called
        # check if we rolled John  back !
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert (dbuser is not None)

    #@mock.patch('sqlalchemy.orm.session.sessionmaker')
    @mock.patch('sqlalchemy.orm.scoping.scoped_session.delete')
    @mock.patch('pdm.cred.CredClient.MockCredClient.del_user')
    def test_deleteUser_HR_fail(self, mock_del_user, mock_del):
        self.__service.fake_auth("TOKEN", {'id':1, 'expiry':None, 'key': 'unused'})  # fake auth John, which is id=1
        mock_del.side_effect = Exception()
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 500)
        assert not mock_del_user.called

    def test_loginUser(self):
        """
        Test the user login procedure
        :return:
        """
        login_creds = {'email': 'Johnny@example.com', 'passwd': 'very_secret'}
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
        assert (res.status_code == 200)
        # TODO check the token content
        token_data = self.__service.token_svc.check(json.loads(res.data))
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        cs_hashed_key = hash_pass(dbuser.password, 'HJGnbfdsV')
        assert (token_data == {'id':1, 'expiry':None, 'key': cs_hashed_key})

        login_creds = {'email': 'Johnny@example.com'}
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
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

    def test_hello(self):
        res = self.__test.get('/users/api/v1.0/hello')
        assert (res.status_code == 200)
        res_str = json.loads(res.data)
        assert (res_str == 'User Service Desk at your service !\n')

    def test_get_token_key(self):
        key = 'hdfgdgfgfusy'
        plain = {'id':44, 'expiry':None, 'key': key}
        svc = TokenService()
        token = svc.issue(plain)
        ukey = HRService.get_token_key(token)
        assert key == ukey

