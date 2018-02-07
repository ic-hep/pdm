#!/usr/bin/env python

import json
import unittest

from pdm.demo.DemoService import DemoService
from pdm.framework.FlaskWrapper import FlaskServer


class TestDemoService(unittest.TestCase):

    def setUp(self):
        conf = { 'test_param': 1111 }
        self.__service = FlaskServer("pdm.demo.DemoService")
        self.__service.test_mode(DemoService, conf)
        self.__service.fake_auth("ALL")
        self.__test = self.__service.test_client()

    def test_init_existingDB(self):
        """ Tests that the config step completes correctly if a DB already
            exists.
        """
        # Create a clean copy of the service
        service = FlaskServer("pdm.demo.DemoService")
        service.test_mode(DemoService, None)
        service.build_db()
        # Add a single turtle to the table
        db = service.test_db()
        new_turtle = db.tables.Turtle(name='Before')
        db.session.add(new_turtle)
        db.session.commit()
        # Continue service start-up
        service.before_startup({})
        service.fake_auth("ALL")
        client = service.test_client()
        # Now check that we only have one turtle
        # Rather than the 3 we get by default
        res = client.get('/demo/api/v1.0/turtles')
        assert(res.status_code == 200)
        assert(len(json.loads(res.data)) == 1)

    def test_web(self):
        """ Check that the basic website redirect + index page work. """
        res = self.__test.get('/')
        assert(res.status_code == 302)
        assert('/web/turtles' in res.location)
        self.__service.testing = True
        res = self.__test.get('/web/turtles')
        assert(res.status_code == 200)
        assert("<html>" in res.data)

    def test_hello(self):
        res = self.__test.get('/demo/api/v1.0/hello')
        assert(res.status_code == 200)
        res_str = json.loads(res.data)
        assert(res_str == "Hello World!\n")

    def test_defTurtles(self):
        # We should have 3 turtles by default
        res = self.__test.get('/demo/api/v1.0/turtles')
        assert(res.status_code == 200)
        turtles = json.loads(res.data)
        assert(len(turtles) == 3)

    def test_addGetDelTurtle(self):
        # Try adding a turtle and then get its info
        new_turtle = json.dumps({'name': 'New Turtle'})
        res = self.__test.post('/demo/api/v1.0/turtles', data=new_turtle)
        assert(res.status_code == 200)
        turtle_id = json.loads(res.data)['id']
        print "Turtle ID: %s" % turtle_id
        # Get info
        res = self.__test.get('/demo/api/v1.0/turtles/%u' % turtle_id)
        assert(res.status_code == 200)
        turtle = json.loads(res.data)
        assert(turtle['id'] == turtle_id)
        assert(turtle['name'] == 'New Turtle')
        # modify the turtle
        mod_turtle = {'name': 'New Lovely Turtle'}
        res = self.__test.put('/demo/api/v1.0/turtles/%u' % turtle_id,
                              data=json.dumps(mod_turtle))
        assert(res.status_code == 200)
        turtle = json.loads(res.data)
        assert(turtle['id'] == turtle_id)
        assert(turtle['name'] == 'New Lovely Turtle')
        # Delete Turtle
        res = self.__test.delete('/demo/api/v1.0/turtles/%u' % turtle_id)
        assert(res.status_code == 200)
        # Check Turtle is gone
        res = self.__test.get('/demo/api/v1.0/turtles/%u' % turtle_id)
        assert(res.status_code == 404)

    def test_delTimmy(self):
        # Timmy the Turtle is protected and can't be deleted
        # Test that this works
        res = self.__test.get('/demo/api/v1.0/turtles')
        assert(res.status_code == 200)
        turtles = json.loads(res.data)
        timmy_id = None
        for turtle_id, turtle_name in turtles.iteritems():
          if turtle_name == 'Timmy':
            timmy_id = int(turtle_id)
            break
        print "Timmy ID: %s" % timmy_id
        assert(timmy_id is not None)
        # Found Timmy, now try delete
        res = self.__test.delete('/demo/api/v1.0/turtles/%u' % timmy_id)
        assert(res.status_code == 401)

    def test_getToken(self):
        res = self.__test.get('/demo/api/v1.0/get_token')
        assert(res.status_code == 200)
        assert(len(res.data) > 10)
        assert("." in res.data)
        # Actually check token content
        token_data = self.__service.token_svc.check(json.loads(res.data))
        assert(token_data == "Hello")

    def test_verifyTokenGood(self):
        self.__service.fake_auth("TOKEN", "TTest")
        res = self.__test.get('/demo/api/v1.0/verify_token')
        assert(res.status_code == 200)
        res_str = json.loads(res.data)
        assert(res_str == 'Token OK! (TTest)')

    def test_verifyTokenBad(self):
        res = self.__test.get('/demo/api/v1.0/verify_token')
        assert(res.status_code == 200)
        res_str = json.loads(res.data)
        assert(res_str == 'Token Missing!')
