__author__ = 'martynia'

import unittest
import os
import json
from pdm.userservicedesk.app import create_app, db
from pdm.userservicedesk.app.models import User
import logging
import requests

logging.basicConfig(level=logging.DEBUG)

class UserManamementTestCase(unittest.TestCase):

    def setUp(self):
        """Define test variables and initialize app."""
        self.app = create_app("testing")
        self.client = self.app.test_client
        self.users = {
            "dn": "dummy",
            "name": "John",
            "password": "very_secret",
            "state": 0,
            "surname": "Smith",
            "username": "admin",
            "email" : "admin@example.com"
        }
        self.users2 = {
            "dn": "dummy2",
            "name": "John",
            "password": "very_secret",
            "state": 0,
            "surname": "Smith",
            "username": "guest",
            "email" : "guest@example.com"
        }

        # binds the app to the current context
        #with self.app.app_context():
            # create all tables
        db.create_all()  # suffucient (we have a 'push' in create_app.

    def test_user_creation(self):
        """Test API can create a new user (POST request)"""
        res = requests.post('http://localhost:5000/users/api/v1.0/users', json=self.users)
        self.assertEqual(res.status_code, 201)
        self.assertDictContainsSubset(self.users, res.json()[0])

    def test_get_all_users(self):
        """Test API can get a user (GET request)."""
        res = requests.post('http://localhost:5000/users/api/v1.0/users', json=self.users2)
        self.assertEqual(res.status_code, 201)
        res = requests.get('http://localhost:5000/users/api/v1.0/users')
        self.assertEqual(res.status_code, 200)

#  order dicts in a list in case we have more users in future tests:

        from operator import itemgetter
        expected_list = sorted([self.users2], key=itemgetter('dn'))
        actual_list   = sorted(res.json(), key=itemgetter('dn'))

        self.assertEqual(len(expected_list), len(actual_list))

        for idx, user in enumerate(expected_list) :
            self.assertDictContainsSubset(user, actual_list[idx])

    def test_user_modification(self):
        """Test API can modify a user (PUT request)"""
        res = requests.post('http://localhost:5000/users/api/v1.0/users', json=self.users2)
        self.assertEqual(res.status_code, 201)
        #
        res = requests.put('http://localhost:5000/users/api/v1.0/users/guest', json=dict(email='admin2@example.com'))
        self.assertEqual(res.status_code, 200)
        # check the response
        self.assertEqual(res.json()[0]['email'], 'admin2@example.com')
        # check the stored user and its email address
        res = requests.get('http://localhost:5000/users/api/v1.0/users/guest')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]['email'], 'admin2@example.com')

    def test_user_deletion(self):
        """Test API can delete a particular user (GET request)"""
        res = requests.post('http://localhost:5000/users/api/v1.0/users', json=self.users2)
        self.assertEqual(res.status_code, 201)
        res = requests.delete('http://localhost:5000/users/api/v1.0/users/guest')
        self.assertEqual(res.status_code, 200)
        res = requests.get('http://localhost:5000/users/api/v1.0/users/guest')
        self.assertEqual(res.status_code, 404)
        res = requests.delete('http://localhost:5000/users/api/v1.0/users/guest')
        self.assertEqual(res.status_code, 404)

    def test_get_user(self):
        """Test API can list a particular user (GET request)"""
        res = requests.post('http://localhost:5000/users/api/v1.0/users', json=self.users2)
        self.assertEqual(res.status_code, 201)
        #
        res = requests.get('http://localhost:5000/users/api/v1.0/users/guest')
        self.assertEqual(res.status_code, 200)
        #
        self.assertEqual(len(res.json()), 1)
        self.assertDictContainsSubset(self.users2, res.json()[0])
        # non existing user
        res = requests.get('http://localhost:5000/users/api/v1.0/users/ursamajor')
        self.assertEqual(res.status_code, 404)

    def tearDown(self):
        """teardown all initialized variables."""
        with self.app.app_context():
            # drop all tables
            pass
            db.session.remove()
            db.drop_all()

# Make the tests conveniently executable
if __name__ == "__main__":
    unittest.main()