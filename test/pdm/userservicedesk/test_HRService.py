__author__ = 'martynia'
import json
import unittest

from pdm.userservicedesk.HRService import HRService
from pdm.framework.FlaskWrapper import FlaskServer


class TestHRService(unittest.TestCase):

    def setUp(self):

        conf = {}
        self.__service = FlaskServer(self.__name__)
        self.__service.test_mode(HRService, None) # to skip DB auto build
        self.__service.fake_auth("ALL")
        # database
        #self.__service.test_mode(HRService, None)
        self.__service.build_db() # build manually
        # Add a single turtle to the table
        db = self.__service.test_db()
        new_user = db.tables.User(username = 'guest',
                                  name = 'John', surname = 'Smith',
                                  email = 'Johnny@example.com', state = 0,
                                  password = 'very_secret')
        db.session.add(new_user)
        db.session.commit()
        self.__service.before_startup(conf) # to continue startup
        #
        self.__test = self.__service.test_client()

    def test_getUserSelf(self):
        """
        GET operation on users/<string:username>
        :return:
        """
        self.__service.fake_auth("TOKEN", "User_1")
        res = self.__test.get('/users/api/v1.0/users/self')
        assert(res.status_code == 200)
        user = json.loads(res.data)
        print user
        assert(user[0]['id'] == 1)
        assert(user[0]['name'] == 'John')
        assert(user[0]['surname'] == 'Smith')
        assert(user[0]['email'] == 'Johnny@example.com')
        assert(user[0]['state'] == 0)
        #
        self.__service.fake_auth("TOKEN", "User_2")
        res = self.__test.get('/users/api/v1.0/users/self')
        assert(res.status_code == 404)

    def test_addUser(self):
        """

        :return:
        """
        self.__service.fake_auth("ALL")
        fred = {'username': 'fred',
             'surname' : 'Flintstone',
             'name': 'Fred',
             'email': 'fred@flintstones.com',
             'state' : 0, 'password': 'Wilma'}

        new_user = json.dumps(fred)
        print "clientside:", new_user

        res = self.__test.post('/users/api/v1.0/users', data=new_user)

        assert(res.status_code == 201)
        #db
        db = self.__service.test_db()
        dbuser = db.tables.User.query.filter_by(email=fred['email']).first()
        assert(dbuser.name == fred['name'])
        assert(dbuser.password == fred['password'])
        assert(dbuser.email == fred['email'])
        response = json.loads(res.data)
        assert(response[0]['name']  == fred['name'])
        assert(response[0]['surname']  == fred['surname'])
        assert(response[0]['email']  == fred['email'])
        assert(response[0]['state']  == fred['state'])




