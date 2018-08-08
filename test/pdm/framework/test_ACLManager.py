#!/usr/bin/env python
""" ACLManager module tests. """

import json
import logging
import unittest

from flask import Flask, current_app, request
from werkzeug.exceptions import HTTPException, Forbidden, NotFound
from pdm.utils.X509 import X509Utils
from pdm.framework.ACLManager import ACLManager, set_session_state

class FakeTokenSVC(object):
    """ A fake token service class for testing ACL Manager. """

    def __init__(self, token_ok=True):
        self.__token_ok = token_ok

    def check(self, raw_token):
        if not self.__token_ok:
            raise ValueError("Invalid Token")
        return json.loads(raw_token)


class TestACLManager(unittest.TestCase):
    """ Test the ACLManager class. """

    def setUp(self):
        """ Create an instance of ACLManager to test. """
        self.__log = logging.getLogger()
        self.__inst = ACLManager(self.__log)

    def __gen_req(self, path, method="GET",
                  auth_mode=ACLManager.AUTH_MODE_NONE, auth_data=None,
                  cert_ok=True, token_ok=True):
        """ Call self.__inst.check_request while generating a fake request
            with the given parameters (without using test_mode on the 
            ACLManager).
            Returns True if the request was successful (i.e. access would
            have been allowed).
        """
        app = Flask("ACLManagertest")
        app.secret_key = "TestKey" # Required for session support
        token_svc = FakeTokenSVC(token_ok)
        try:
            headers = {}
            enable_session = False
            if auth_mode == ACLManager.AUTH_MODE_X509:
                if cert_ok:
                    headers['Ssl-Client-Verify'] = 'SUCCESS'
                else:
                    headers['Ssl-Client-Verify'] = 'FAILED'
                headers['Ssl-Client-S-Dn'] = auth_data
            elif auth_mode == ACLManager.AUTH_MODE_TOKEN:
                headers['X-Token'] = json.dumps(auth_data)
            elif auth_mode == ACLManager.AUTH_MODE_SESSION:
                enable_session = True
            with app.test_request_context(path=path, method=method,
                                          headers=headers):
                if enable_session:
                    set_session_state(True)
                # Prepare a standard looking request
                current_app.log = self.__log
                current_app.token_svc = token_svc
                request.uuid = "Test-Test-Test"
                # Call the check function
                self.__inst.check_request()
                # Check that request info was correctly propagated
                if auth_mode == ACLManager.AUTH_MODE_X509:
                    norm_dn = X509Utils.normalise_dn(auth_data)
                    self.assertEqual(request.dn, norm_dn)
                elif auth_mode == ACLManager.AUTH_MODE_TOKEN:
                    if token_ok:
                        self.assertEqual(request.token, auth_data)
                        self.assertEqual(request.raw_token, auth_data)
                        self.assertTrue(request.token_ok)
                    else:
                        self.assertFalse(request.token_ok)
                elif auth_mode == ACLManager.AUTH_MODE_SESSION:
                    self.assertTrue(request.session_ok)
            # Access was allowed (no exception raised)
            return True
        except Forbidden:
            # Access was denied (Forbidden exception thrown)
            return False

    def test_basic(self):
        """ Add simple ALL rules and see if they work. """
        self.__inst.add_rule("/test1", "ALL")
        self.__inst.add_rule("/test2", "ALL")
        self.__inst.add_rule("/test/nested", "ALL")
        self.__inst.add_rule("/test/post%MISC", "ALL")
        self.__inst.add_rule("/test/multi%POST", "ALL")
        self.__inst.add_rule("/test/multi%PUT", "ALL")
        self.assertFalse(self.__gen_req("/"))
        self.assertTrue(self.__gen_req("/test1"))
        self.assertTrue(self.__gen_req("/test1/"))
        self.assertTrue(self.__gen_req("/test2"))
        self.assertFalse(self.__gen_req("/test"))
        self.assertFalse(self.__gen_req("/test/nest"))
        self.assertTrue(self.__gen_req("/test/nested"))
        self.assertFalse(self.__gen_req("/test/post", "GET"))
        self.assertTrue(self.__gen_req("/test/post", "MISC"))
        self.assertTrue(self.__gen_req("/test/multi", "POST"))
        self.assertTrue(self.__gen_req("/test/multi", "PUT"))
        self.assertFalse(self.__gen_req("/test/multi", "GET"))
        # Check that requests containing a % char are always rejected.
        self.assertRaises(NotFound, self.__gen_req, "/test/test/test%%")

    def test_auth_modes(self):
        """ Check that all auth modes work as expected. """
        self.__inst.add_rule("/cert_only", "CERT")
        self.__inst.add_rule("/cert_dn1", "CERT:/C=XX/OU=Test/CN=Test User1")
        self.__inst.add_rule("/cert_dn2", "CERT:C = YY, OU = Bah, CN = Test User2")
        self.__inst.add_rule("/token_only", "TOKEN")
        self.__inst.add_rule("/session_only", "SESSION")
        self.__inst.add_rule("/all", "ALL")
        # Now test that each auth mode only works with the expected endpoint
        # We do this by looping over every endpoint in the TEST_EP list and
        # trying them with certain authentication parameters.
        TEST_EP = ["/cert_only", "/cert_dn1", "/cert_dn2",
                   "/token_only", "/session_only", "/all", "/none"]
        # AUTH_TESTs is a list of tuples: (auth_mode, auth_data, res)
        # res is a list of whether each TEST_EP should be expected to work
        # with this endpoint or not (in the order of TEST_EP)
        AUTH_TESTS = [
          (ACLManager.AUTH_MODE_X509, 'C = XX, OU = Test, CN = Test User1',
           (True, True, False, False, False, True, False, )),
          (ACLManager.AUTH_MODE_X509, 'C = YY, OU = Bah, CN = Test User2',
           (True, False, True, False, False, True, False, )),
          (ACLManager.AUTH_MODE_X509, 'C = ZZ, OU = Other, CN = Test User3',
           (True, False, False, False, False, True, False, )),
          (ACLManager.AUTH_MODE_TOKEN, "TOKENTEXT",
           (False, False, False, True, False, True, False, )),
          (ACLManager.AUTH_MODE_TOKEN, "OTHERTOKENTEXT",
           (False, False, False, True, False, True, False, )),
          (ACLManager.AUTH_MODE_SESSION, None,
           (False, False, False, False, True, True, False, )),
          (ACLManager.AUTH_MODE_NONE, None,
           (False, False, False, False, False, True, False, )),
        ]
        for auth_mode, auth_data, auth_res in AUTH_TESTS:
            for i in xrange(0, len(TEST_EP)):
                res = self.__gen_req(TEST_EP[i], "GET", auth_mode, auth_data)
                self.assertEqual(res, auth_res[i],
                    "Path %s failed, auth_data=%s, Expected: %s, Actual: %s" % \
                    (TEST_EP[i], auth_data, auth_res[i], res))
        # Finally, check that token fails if the token provided is bad
        res = self.__gen_req("/token_only", "GET", ACLManager.AUTH_MODE_TOKEN,
                             "BAD_TOKEN", token_ok=False)
        self.assertFalse(res)
                                        

    def test_groups(self):
        """ Check that groups are applied correctly. """
        self.__inst.add_group_entry("grp1", "ALL")
        self.__inst.add_rule("/group1", "@grp1")
        self.__inst.add_group_entry("grp2", "CERT")
        self.__inst.add_group_entry("grp2", "TOKEN")
        self.__inst.add_rule("/group2", "@grp2")
        # Missing group
        self.assertRaises(ValueError, self.__inst.add_rule,
                          "/group3", "@grp3")
        # Check the groups work as expected
        self.assertTrue(self.__gen_req("/group1"))
        self.assertTrue(self.__gen_req("/group1", "GET",
                        ACLManager.AUTH_MODE_X509, "CN=Test"))
        self.assertTrue(self.__gen_req("/group1", "GET",
                        ACLManager.AUTH_MODE_TOKEN, "TOKENSTR"))
        self.assertFalse(self.__gen_req("/group2"))
        self.assertTrue(self.__gen_req("/group2", "GET",
                        ACLManager.AUTH_MODE_X509, "CN=Test"))
        self.assertTrue(self.__gen_req("/group2", "GET",
                        ACLManager.AUTH_MODE_TOKEN, "TOKENSTR"))

    def test_bad_rules(self):
        """ Check that malformed rules and groups are rejected. """
        # Bad auth type
        self.assertRaises(ValueError,
                          self.__inst.add_rule, "/bad", "BAD")
        # Nested Group
        self.__inst.add_group_entry("grp1", "ALL")
        self.assertRaises(ValueError,
                          self.__inst.add_group_entry, "/bad", "@grp1")
        # Cert with no DN
        self.assertRaises(ValueError,
                          self.__inst.add_rule, "/bad", "CERT:")
        # Two rules for the same path
        self.__inst.add_rule("/good", "TOKEN")
        self.assertRaises(ValueError,
                          self.__inst.add_rule, "/good", "CERT")

    def test_wildcards(self):
        """ Check that wildcards work as expected. """
        self.__inst.add_rule("/ep1/?", "ALL")
        self.__inst.add_rule("/ep1/test/?", "ALL")
        self.__inst.add_rule("/ep1/test/?/test2", "ALL")
        self.__inst.add_rule("/ep1/test/?/test2/?", "ALL")
        self.__inst.add_rule("/ep2/test/?/?", "ALL")
        self.__inst.add_rule("/ep3/test/*", "ALL")
        self.__inst.add_rule("/ep4/*/test", "ALL")
        self.__inst.add_rule("/ep5/?/test%POST", "ALL")
        # Check paths work as expected
        # EP1
        self.assertFalse(self.__gen_req("/ep1"))
        self.assertTrue(self.__gen_req("/ep1/blah"))
        self.assertTrue(self.__gen_req("/ep1/test"))
        self.assertFalse(self.__gen_req("/ep1/blah/bad"))
        self.assertTrue(self.__gen_req("/ep1/test/blah"))
        self.assertTrue(self.__gen_req("/ep1/test/blah/test2"))
        self.assertTrue(self.__gen_req("/ep1/test/blah/test2/blah2"))
        self.assertFalse(self.__gen_req("/ep1/test/blah/test3"))
        # EP2
        self.assertFalse(self.__gen_req("/ep2"))
        self.assertFalse(self.__gen_req("/ep2/test/blah2"))
        self.assertTrue(self.__gen_req("/ep2/test/blah2/extra"))
        # EP3
        self.assertFalse(self.__gen_req("/ep3"))
        self.assertFalse(self.__gen_req("/ep3/test"))
        self.assertTrue(self.__gen_req("/ep3/test/extra1"))
        self.assertTrue(self.__gen_req("/ep3/test/extra1/extra2"))
        # EP4
        self.assertFalse(self.__gen_req("/ep4/blah/test"))
        self.assertFalse(self.__gen_req("/ep4/blah/blah/test"))
        # EP5
        self.assertFalse(self.__gen_req("/ep5/blah/test", "GET"))
        self.assertTrue(self.__gen_req("/ep5/blah/test", "POST"))
        # Special case: only wildcard
        self.__inst.add_rule("*", "ALL")
        self.assertTrue(self.__gen_req("/"))
        self.assertTrue(self.__gen_req("/special"))
        self.assertTrue(self.__gen_req("/special/special"))

    def test_wildcard_but_wrong_auth(self):
        """ Simply test wildcard rule which matches one auth type,
            but the user has a different auth type.
        """
        self.__inst.add_rule("/test/?", "CERT")
        self.assertFalse(self.__gen_req("/test/blah", "GET",
                                        ACLManager.AUTH_MODE_TOKEN, "X"))
        self.assertTrue(self.__gen_req("/test/blah", "GET",
                                        ACLManager.AUTH_MODE_X509, "C=X"))

    def __check_test_mode(self, auth_mode, auth_data):
        """ Helper function for testing test_mode.
        """
        self.__inst.test_mode(auth_mode, auth_data)
        app = Flask("ACLManagertest")
        with app.test_request_context(path="/test", method="GET"):
            request.uuid = "Test-Test-Test"
            # Call the check function
            self.__inst.check_request()
            # Check that request info was correctly propagated
            if auth_mode == ACLManager.AUTH_MODE_X509:
                norm_dn = X509Utils.normalise_dn(auth_data)
                self.assertEqual(request.dn, norm_dn)
            elif auth_mode == ACLManager.AUTH_MODE_TOKEN:
                self.assertEqual(request.token, auth_data)
                self.assertEqual(request.raw_token, auth_data)
                self.assertTrue(request.token_ok)
            elif auth_mode == ACLManager.AUTH_MODE_SESSION:
                self.assertTrue(request.session_ok)

    def test_test_mode(self):
        """ Check that test mode works correctly. """
        self.__check_test_mode(ACLManager.AUTH_MODE_X509, "/C=XX/CN=Test1")
        self.__check_test_mode(ACLManager.AUTH_MODE_X509, "C=YY,CN=Test2")
        self.__check_test_mode(ACLManager.AUTH_MODE_TOKEN, "TOKENSTR")
        self.__check_test_mode(ACLManager.AUTH_MODE_TOKEN, "TEST2")
        self.__check_test_mode(ACLManager.AUTH_MODE_SESSION, None)

    @staticmethod
    def __test_redir_cb():
        return "Hello World"

    def __run_redir(self, app, path):
        """ Try to get the given path in app context. """
        with app.test_request_context(path=path, method="GET"):
            request.uuid = "Test-Test-Test"
            self.__inst.check_request()

    def test_redir(self):
        """ Check that the redirect works correctly on 403.
            (if set on the end object).
            This is slightly more complex than all of the other auth
            checks as it relies on a proper rule existing in flask
        """
        app = Flask("ACLManagertest")
        # Configure the endpoint/rule
        self.__test_redir_cb.export_redir = '/login?ret=%(return_to)s'
        app.add_url_rule('/test', "/test", self.__test_redir_cb)
        # Configure Auth
        self.__inst.add_rule("/test", "SESSION")
        self.__inst.add_rule("/test2", "SESSION")
        # Run test
        # Check that /test returns a redirect
        with self.assertRaises(HTTPException) as err:
            self.__run_redir(app, "/test")
        self.assertEqual(err.exception.response.status_code, 302)
        self.assertEqual(err.exception.response.location, "/login?ret=%2Ftest")
        # Whereas /test2 should return a classic 403
        self.assertRaises(Forbidden, self.__run_redir, app, "/test2")

    def test_token_expiry(self):
        """ Check that invalid tokens are correctly rejected. """
        # Still valid
        GOOD_TOKEN = {'id': 123, 'expiry': '2099-12-31T23:59:59.00' }
        # Expired
        BAD_TOKEN = {'id': 123, 'expiry': '1999-12-31T23:59:59.00' }
        # Malformed expiry string
        UGLY_TOKEN = {'id': 123, 'expiry': 'This is not a date.' }
        # Prepare the endpoint
        self.__inst.add_rule("/ep_tkn", "TOKEN")
        # Check all tokens can still access
        self.assertTrue(self.__gen_req('/ep_tkn', 'GET',
                                       ACLManager.AUTH_MODE_TOKEN, GOOD_TOKEN))
        self.assertFalse(self.__gen_req('/ep_tkn', 'GET',
                                        ACLManager.AUTH_MODE_TOKEN, BAD_TOKEN))
        self.assertFalse(self.__gen_req('/ep_tkn', 'GET',
                                        ACLManager.AUTH_MODE_TOKEN, UGLY_TOKEN))
