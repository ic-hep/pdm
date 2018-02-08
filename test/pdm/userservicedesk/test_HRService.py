__author__ = 'martynia'
import json
import unittest

from pdm.userservicedesk.HRService import HRService
from pdm.framework.FlaskWrapper import FlaskServer
from pdm.utils.hashing import hash_pass, check_hash

class TestHRService(unittest.TestCase):
    def setUp(self):
        conf = {}
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
        self.__service.fake_auth("TOKEN", "User_1")
        res = self.__test.get('/users/api/v1.0/users/self')
        assert (res.status_code == 200)
        user = json.loads(res.data)
        print user
        # assert (user[0]['id'] == 1)
        assert (user[0]['name'] == 'John')
        assert (user[0]['surname'] == 'Smith')
        assert (user[0]['email'] == 'Johnny@example.com')
        assert (user[0]['state'] == 0)
        #
        self.__service.fake_auth("TOKEN", "User_2")
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

        new_user = json.dumps(fred)

        res = self.__test.post('/users/api/v1.0/users', data=new_user)

        assert (res.status_code == 201)
        # db
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email=fred['email']).first()
        assert (dbuser.name == fred['name'])
        assert (check_hash(dbuser.password,fred['password']))
        assert (dbuser.email == fred['email'])
        response = json.loads(res.data)
        assert (response[0]['name'] == fred['name'])
        assert (response[0]['surname'] == fred['surname'])
        assert (response[0]['email'] == fred['email'])
        assert (response[0]['state'] == fred['state'])

        # try to duplicate the user:
        res = self.__test.post('/users/api/v1.0/users', data=new_user)
        assert (res.status_code == 403)

        new_user = json.dumps(barney)  # pass too short !
        res = self.__test.post('/users/api/v1.0/users', data=new_user)
        assert (res.status_code == 404)
        #
        b_email = barney.pop('email')
        new_user = json.dumps(barney)
        res = self.__test.post('/users/api/v1.0/users', data=new_user)
        assert (res.status_code == 404)

        barney['email'] = b_email
        password = barney.pop('password')
        new_user = json.dumps(barney)
        res = self.__test.post('/users/api/v1.0/users', data=new_user)
        assert (res.status_code == 404)

    def test_changePassword(self):
        """
        Test the password changing operation
        :return:
        """
        self.__service.fake_auth("TOKEN", "User_1")  # fake auth John, which is id=1
        new_pass_data = json.dumps({'passwd': 'very_secret', 'newpasswd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 200)
        # check if the password was actually modified:
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email='Johnny@example.com').first()
        assert (dbuser.name == "John")
        assert (check_hash(dbuser.password,'even_more_secret'))
        # TODO (response)

        # wrong password
        wrong_pass_data = json.dumps({'passwd': 'very_sercet', 'newpasswd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=wrong_pass_data)
        assert (res.status_code == 403)
        # same pass
        same_pass_data = json.dumps({'passwd': 'even_more_secret', 'newpasswd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=same_pass_data)
        assert (res.status_code == 403)
        # no pass
        no_pass = json.dumps({'passwd': None, 'newpasswd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 403)
        no_pass = json.dumps({'newpasswd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 403)
        no_pass = json.dumps({'passwd': 'even_more_secret'})
        res = self.__test.put('/users/api/v1.0/passwd', data=no_pass)
        assert (res.status_code == 403)
        #
        no_npass = json.dumps({'passwd': 'even_more_secret', 'newpasswd': None})
        res = self.__test.put('/users/api/v1.0/passwd', data=no_npass)
        assert (res.status_code == 403)
        # weak pass
        weak_pass = json.dumps({'passwd': 'even_more_secret', 'newpasswd': 'test'})
        res = self.__test.put('/users/api/v1.0/passwd', data=weak_pass)
        assert (res.status_code == 403)
        # non existing user
        self.__service.fake_auth("TOKEN", "User_7")
        res = self.__test.put('/users/api/v1.0/passwd', data=new_pass_data)
        assert (res.status_code == 404)

    def test_deleteUser(self):
        """
        Test updating user data
        :return:
        """
        # not existing user:
        self.__service.fake_auth("TOKEN", "User_7")
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 404)

        # delete poor Johny ;-(
        self.__service.fake_auth("TOKEN", "User_1")  # fake auth John, which is id=1
        res = self.__test.delete('/users/api/v1.0/users/self')
        assert (res.status_code == 200)

    def test_loginUser(self):
        """
        Test the user login procedure
        :return:
        """
        login_creds = json.dumps({'email': 'Johnny@example.com', 'passwd': 'very_secret'})
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
        assert (res.status_code == 200)
        # TODO check the token content
        token_data = self.__service.token_svc.check(json.loads(res.data))
        assert (token_data == 'User_1')

        login_creds = json.dumps({'email': 'Johnny@example.com'})
        res = self.__test.post('/users/api/v1.0/login', data=login_creds)
        assert (res.status_code == 404)
        res = self.__test.post('/users/api/v1.0/login',
                               data=json.dumps({'email': 'Johnny@example.com', 'passwd': 'very_seCret'}))
        assert (res.status_code == 403)
        res = self.__test.post('/users/api/v1.0/login',
                               data=json.dumps({'email': 'johnny@example.com', 'passwd': 'very_secret'}))
        assert (res.status_code == 403)
        res = self.__test.post('/users/api/v1.0/login',
                               data=json.dumps({'email': 'johnny@example.com', 'passwd': None}))
        assert (res.status_code == 403)

    def test_hello(self):
        res = self.__test.get('/users/api/v1.0/hello')
        assert (res.status_code == 200)
        res_str = json.loads(res.data)
        assert (res_str == 'User Service Desk at your service !\n')
