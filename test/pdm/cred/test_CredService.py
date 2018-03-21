#!/usr/bin/env python
""" Tests for the cred service module. """

import json
import datetime
import unittest
from copy import deepcopy
from M2Crypto import X509, RSA

from pdm.utils.X509 import X509Utils
from pdm.cred.CredService import CredService
from pdm.framework.Tokens import TokenService
from pdm.framework.FlaskWrapper import FlaskServer


class test_CredService(unittest.TestCase):
    """ Test the CredService service. """

    DEF_CONFIG = {'ca_dn': '/C=XX/OU=Test CA',
                  'ca_key': 'weakCAPass',
                  'user_dn_base': '/C=XX/OU=Test Users',
                  'user_cred_secret': 'weakUserPass'}

    def setUp(self):
        """ Configure the basic test service with some
            sensible default parameters.
        """
        self.__service = FlaskServer("pdm.cred.CredService")
        self.__service.test_mode(CredService,
                                 deepcopy(test_CredService.DEF_CONFIG))
        self.__service.fake_auth("ALL")
        self.__client = self.__service.test_client()

    def test_regen(self):
        """ Call the service initialisation a second time and check
            that the CA cert doesn't get regenerated (i.e. doesn't
            change in the DB).
        """
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        ca_info1 = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                          .first()
        # Re-run the start-up
        self.__service.before_startup(deepcopy(test_CredService.DEF_CONFIG))
        ca_info2 = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                          .first()
        self.assertEqual(ca_info1.pub_cert, ca_info2.pub_cert)

    def test_ca_config(self):
        """ Test that the CA was created as per the user configuration.
        """
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                         .first()
        # TODO: Check ca_info against DEF_CONFIG parameters here!

    def test_ca_badconf(self):
        """ Check that an error is throw if any non-optional bits of the
            config are missing.
        """
        for conf_key in ('ca_dn', 'ca_key',
                         'user_dn_base', 'user_cred_secret'):
            conf = deepcopy(test_CredService.DEF_CONFIG)
            conf.pop(conf_key)
            test_inst = FlaskServer("pdm.cred.CredService")
            self.assertRaises(RuntimeError, test_inst.test_mode,
                              CredService, conf)

    def test_ca_wrong_key(self):
        """ Check that an exception if thrown if the CA is loaded with the
            wrong key.
        """
        conf = deepcopy(test_CredService.DEF_CONFIG)
        conf['ca_key'] = "wrongKey"
        self.assertRaises(RuntimeError, self.__service.before_startup, conf)

    def test_ca(self):
        """ Test that we can access the CA cert with GET /ca.
        """
        res = self.__client.get('/cred/api/v1.0/ca')
        self.assertEqual(res.status_code, 200)
        json_obj = json.loads(res.data)
        # Check returned object matches the spec
        self.assertIsInstance(json_obj, dict)
        self.assertItemsEqual(['ca'], json_obj.keys())
        # Get the actual CA cert PEM
        ca_data = json_obj['ca']
        self.assertIn("BEGIN CERTIFICATE", ca_data)
        # Check that the ca_data matches the database entry
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                         .first()
        self.assertEqual(ca_data, ca_info.pub_cert)

    def test_ca_missing(self):
        """ Check that GET /ca call fails gracefully if CA is missing from DB,
            should never happen unless DB is corrupt, but check anyway.
        """
        db = self.__service.test_db()
        CAEntry = db.tables.CAEntry
        CAEntry.query.delete()
        db.session.commit()
        res = self.__client.get('/cred/api/v1.0/ca')
        self.assertEqual(res.status_code, 404)

    def test_add_user_missing_post(self):
        """ Check that add user sends 500 on missing POST data. """
        res = self.__client.post('/cred/api/v1.0/user')
        self.assertEqual(res.status_code, 500)        

    def test_add_user(self):
        """ Add a user and check that suitable credentials are created in
            the database.
        """
        TEST_USER_ID = 123
        TEST_USER_KEY = "weakUserKey"
        TEST_USER_EMAIL = "test@test.test"
        TEST_INPUT = {'user_id': TEST_USER_ID,
                      'user_key': TEST_USER_KEY,
                      'user_email': TEST_USER_EMAIL}
        res = self.__client.post('/cred/api/v1.0/user', data=TEST_INPUT)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, "")
        # Check credentials in database
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        creds = UserCred.query.filter_by(user_id=TEST_USER_ID).all()
        # We should have two creds, an SSH key and an X509 key
        self.assertEqual(len(creds), 2)
        user_serial = None
        found_x509 = False
        found_ssh = False
        for cred in creds:
            if cred.cred_type == CredService.CRED_TYPE_X509:
                found_x509 = True
                cred_str= cred.cred_pub.encode('ascii','ignore')
                x509_obj = X509.load_cert_string(cred_str)
                user_serial = x509_obj.get_serial_number()
                user_dn = X509Utils.x509name_to_str(x509_obj.get_subject())
                templ_dn = "C = XX, OU = Test Users, CN = User_%u " % \
                               TEST_USER_ID
                self.assertIn(templ_dn, user_dn)
                # TODO: Check user e-mail was stored in cert
            elif cred.cred_type == CredService.CRED_TYPE_SSH:
                found_ssh = True
                self.assertIn("ssh-rsa", cred.cred_pub)
            # TODO: Check cred was stored with supplied key
        self.assertTrue(found_x509)
        self.assertTrue(found_ssh)
        # Check CA serial was stored correctly (one higher than user serial)
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                         .first()
        self.assertEqual(user_serial + 1, ca_info.serial)

    def test_add_cred_x509(self):
        """ Add an X509 credential to a user.
        """
        TEST_USER_ID = 123
        TEST_USER_KEY = "weakUserKey"
        TEST_CRED_TYPE = CredService.CRED_TYPE_X509
        TEST_LIFETIME = 6
        # First add the test user
        add_user = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY}
        res = self.__client.post('/cred/api/v1.0/user', data=add_user)
        self.assertEqual(res.status_code, 200)
        # Then create a credential
        add_cred = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY,
                    'cred_type': TEST_CRED_TYPE,
                    'max_lifetime': TEST_LIFETIME}
        res = self.__client.post('/cred/api/v1.0/cred', data=add_cred)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 1)
        self.assertIn('token', res_obj)
        token = res_obj['token']
        # TODO: Check that Token matches the expected value
        # TODO: Check that cred in DB looks OK

    def test_add_cred_ssh(self):
        """ Add an SSH credential to a user.
        """
        TEST_USER_ID = 123
        TEST_USER_KEY = "weakUserKey"
        TEST_CRED_TYPE = CredService.CRED_TYPE_SSH
        TEST_LIFETIME = 6
        # First add the test user
        add_user = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY}
        res = self.__client.post('/cred/api/v1.0/user', data=add_user)
        self.assertEqual(res.status_code, 200)
        # Then create a credential
        add_cred = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY,
                    'cred_type': TEST_CRED_TYPE,
                    'max_lifetime': TEST_LIFETIME}
        res = self.__client.post('/cred/api/v1.0/cred', data=add_cred)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 1)
        self.assertIn('token', res_obj)
        token = res_obj['token']
        # TODO: Check that Token matches the expected value
        # TODO: Check that cred in DB looks OK

    def test_add_cred_badtype(self):
        """ Adds a bad credential to a user and check we get an error
            back.
        """
        TEST_USER_ID = 123
        TEST_USER_KEY = "weakUserKey"
        TEST_CRED_TYPE = 999
        TEST_LIFETIME = 6
        # First add the test user
        add_user = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY}
        res = self.__client.post('/cred/api/v1.0/user', data=add_user)
        self.assertEqual(res.status_code, 200)
        # Then create a credential
        add_cred = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY,
                    'cred_type': TEST_CRED_TYPE,
                    'max_lifetime': TEST_LIFETIME}
        res = self.__client.post('/cred/api/v1.0/cred', data=add_cred)
        self.assertEqual(res.status_code, 404)
        # Manually create an unknown cred type in DB
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        bad_cred = UserCred(user_id=TEST_USER_ID,
                            cred_type=TEST_CRED_TYPE,
                            expiry_date=datetime.datetime.now(),
                            cred_pub="", cred_priv="")
        db.session.add(bad_cred)
        db.session.commit()
        # Check we get an error back
        res = self.__client.post('/cred/api/v1.0/cred', data=add_cred)
        self.assertEqual(res.status_code, 500)

    def test_add_cred_missing_post(self):
        """ Check that add cred sends 500 on missing POST data. """
        res = self.__client.post('/cred/api/v1.0/cred')
        self.assertEqual(res.status_code, 500)        

    def test_del_user(self):
        """ Add a user with creds and then delete them.
            Check everything is deleted.
        """
        TEST_USER_ID = 321
        # Manually configure DB
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        JobCred = db.tables.JobCred
        user_obj = UserCred(user_id=TEST_USER_ID,
                            cred_type=CredService.CRED_TYPE_SSH,
                            expiry_date=datetime.datetime.now(),
                            cred_pub="PUB", cred_priv="PRIV")
        db.session.add(user_obj)
        db.session.commit()
        job_obj = JobCred(base_id=user_obj.cred_id,
                          cred_type=CredService.CRED_TYPE_SSH,
                          expiry_date=user_obj.expiry_date,
                          cred_pub="PUB2", cred_priv="PRIV2")
        db.session.add(job_obj)
        db.session.commit()
        # Now try deleting everything
        res = self.__client.delete('/cred/api/v1.0/user/%u' % TEST_USER_ID)
        self.assertEqual(res.status_code, 200)
        # Check both tables are actually empty
        ret_users = UserCred.query.all()
        self.assertFalse(ret_users)
        ret_jobs = JobCred.query.all()
        self.assertFalse(ret_jobs)

    def test_get_user(self):
        """ Add a user directly to DB and check GET user/ID verb works. """
        TEST_USER_ID = 321
        TEST_CRED_TYPE = 999
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        # Create three times, one in an hour, one in a day, one in a minute
        now = datetime.datetime.now()
        next_hour = now + datetime.timedelta(hours=1)
        next_day = now + datetime.timedelta(days=1)
        next_min = now + datetime.timedelta(minutes=1)
        # Add two creds to the database
        for cred_time in (next_hour, next_day, next_min):
            cred = UserCred(user_id=TEST_USER_ID,
                            cred_type=TEST_CRED_TYPE,
                            expiry_date=cred_time,
                            cred_pub="PUB", cred_priv="PRIV")
            db.session.add(cred)
        db.session.commit()
        # Call get user and check we get the latest date back
        res = self.__client.get('/cred/api/v1.0/user/%u' % TEST_USER_ID)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 1)
        self.assertIn('valid_until', res_obj)
        valid = res_obj['valid_until']
        self.assertEqual(valid, next_day.isoformat())

    def test_del_cred(self):
        """ Add a user + cred and check we can delete the cred.  """
        TEST_USER_ID = 321
        # Manually configure DB
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        JobCred = db.tables.JobCred
        user_obj = UserCred(user_id=TEST_USER_ID,
                            cred_type=CredService.CRED_TYPE_SSH,
                            expiry_date=datetime.datetime.now(),
                            cred_pub="PUB", cred_priv="PRIV")
        db.session.add(user_obj)
        db.session.commit()
        job_obj = JobCred(base_id=user_obj.cred_id,
                          expiry_date=user_obj.expiry_date,
                          cred_type=CredService.CRED_TYPE_SSH,
                          cred_pub="PUB2", cred_priv="PRIV2")
        db.session.add(job_obj)
        db.session.commit()
        # Now we have to generate the token needed to delete the key
        token_key = test_CredService.DEF_CONFIG["user_cred_secret"]
        # Salt for token is hardcoded
        token_svc = TokenService(token_key, 'CATokenSalt')
        token = token_svc.issue(job_obj.cred_id)
        # Now try the delete
        res = self.__client.delete('/cred/api/v1.0/cred/%s' % token)
        self.assertEqual(res.status_code, 200)
        # Check DB is empty
        jobs = JobCred.query.all()
        self.assertFalse(jobs)

    def __get_cred_helper(self, cred_type):
        """ A helper for the test_get_cred_* functions.
            Builds a full user + cred chain, returns a token.
        """
        TEST_USER_ID = 543
        TEST_USER_KEY = "anotherUserKey"
        TEST_LIFETIME = 12
        # First add the test user
        add_user = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY}
        res = self.__client.post('/cred/api/v1.0/user', data=add_user)
        self.assertEqual(res.status_code, 200)
        # Then create a credential
        add_cred = {'user_id': TEST_USER_ID,
                    'user_key': TEST_USER_KEY,
                    'cred_type': cred_type,
                    'max_lifetime': TEST_LIFETIME}
        res = self.__client.post('/cred/api/v1.0/cred', data=add_cred)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 1)
        self.assertIn('token', res_obj)
        return res_obj['token']

    def test_get_cred_x509(self):
        """ Try getting a cred, we should get a delegated proxy back.
            This is basically the full workflow test.
        """
        token = self.__get_cred_helper(CredService.CRED_TYPE_X509)
        # Now fetch the credential
        res = self.__client.get('/cred/api/v1.0/cred/%s' % token)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 3)
        self.assertIn('cred_type', res_obj)
        self.assertEqual(res_obj['cred_type'], CredService.CRED_TYPE_X509)
        self.assertIn('pub_key', res_obj)
        self.assertIn('priv_key', res_obj)
        # TODO: Check credential looks correct
        # Private key should be unencrypted
        pw_cb = lambda x: None
        rsa_key = RSA.load_key_string(str(res_obj['priv_key']), callback=pw_cb)
        self.assertIsInstance(rsa_key, RSA.RSA)

    def test_get_cred_ssh(self):
        """ Try to get an SSH cred for a job.
        """
        token = self.__get_cred_helper(CredService.CRED_TYPE_SSH)
        # Now fetch the credential
        res = self.__client.get('/cred/api/v1.0/cred/%s' % token)
        self.assertEqual(res.status_code, 200)
        res_obj = json.loads(res.data)
        self.assertEqual(len(res_obj), 3)
        self.assertIn('cred_type', res_obj)
        self.assertEqual(res_obj['cred_type'], CredService.CRED_TYPE_SSH)
        self.assertIn('pub_key', res_obj)
        self.assertIn('priv_key', res_obj)
        # Check credential looks correct
        self.assertIn('ssh-rsa', res_obj['pub_key'])
        # For SSH, the public credential should match the user DB
        TEST_USER_ID = 543
        db = self.__service.test_db()
        UserCred = db.tables.UserCred
        cred_type = CredService.CRED_TYPE_SSH
        user_obj = UserCred.query.filter_by(user_id=TEST_USER_ID,
                                            cred_type=cred_type).first()
        self.assertEqual(res_obj['pub_key'], user_obj.cred_pub)
        # Private key should be unencrypted RSA
        pw_cb = lambda x: None
        rsa_key = RSA.load_key_string(str(res_obj['priv_key']), callback=pw_cb)
        self.assertIsInstance(rsa_key, RSA.RSA)

    def test_cred_bad_token(self):
        """ Check both get and delete cred return 403 on bad tokens. """
        BAD_TOKEN = "BAD"
        FULL_URL = '/cred/api/v1.0/cred/%s' % BAD_TOKEN
        res = self.__client.get(FULL_URL)
        self.assertEqual(res.status_code, 403)
        res = self.__client.delete(FULL_URL)
        self.assertEqual(res.status_code, 403)
