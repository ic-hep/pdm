#!/usr/bin/env python

import mock
import unittest
from functools import partial

from pdm.utils.X509 import X509Utils, X509CA


# We need a keypair for testing proxy generation
# It doesn't matter that these are expired and we don't
# have a CA.
TESTCERT_AND_KEY = ("""-----BEGIN CERTIFICATE-----
MIIC2DCCAcCgAwIBAgIBAjANBgkqhkiG9w0BAQsFADAfMQswCQYDVQQGEwJYWDEQ
MA4GA1UEAwwHVGVzdCBDQTAeFw0xODAxMzAxNDE5NDhaFw0xODAyMDMxNDE5NDha
MCExCzAJBgNVBAYTAlhYMRIwEAYDVQQDDAlUZXN0IFVzZXIwggEiMA0GCSqGSIb3
DQEBAQUAA4IBDwAwggEKAoIBAQC4JLzhms5bnBBiESlbUSFOk5Hi9bVFn15h44fm
E30kmsoQdz+eePZ9gPYpcg9MW7rxUCYdoKhfCUdx1sEo8m7+1RWMoQhUDhR8RD7b
/WQd++rXfLp+d3dw5qBwbcYewwndtzYFjaA+n6FKl93BRKszs+SBn6OApKpsL2OQ
Ni0SGeUfd0PK07ka2615fiSQ+6y0WmaPh0OYkWopZm/lI7wd6zWha/1g5GIDOGjE
dI73Dzf+h+bE0kiZiHhRFQY3slWCBo3Y3l9RXDuEGl0UkR9EuzhwNHS8mQXlby26
nm+PtynbKUkflJN5gxDSN4+Xwimo24jNudT9ZorMVkbSVQXfAgMBAAGjHTAbMAwG
A1UdEwEB/wQCMAAwCwYDVR0PBAQDAgSwMA0GCSqGSIb3DQEBCwUAA4IBAQBao+2+
7xZcZ/QOwzVXRwA3xT/pyscprZnn4FsUpVC5nq271l7G8FnGd51/iKnea3mxhSdO
xKLA7sYYfSxBhz3ip8eUncJvzUMXdl03pnJC6opVejFw7IvkMmuZnZRmDX3VNdCs
CXykEfzEB7L5QBDhhc8fYkFPCltz1O+N6E0b0WXPMEARQK5YzRqwzx+RS+Dg4W1H
SiLXzFAVWNEAKzihMuex+iiRYFpncQbuF+WbBNZTZhuh71t0PKlBrV3qw6JMG/dP
qdPfxBek0F3Qf4ze0fLGEIEbTMfdHbdzgvI14l6hFcJUH0bFJ9l7RPOOJTNQwDSP
w6piDJ1a0kdB2y2D
-----END CERTIFICATE-----""",
"""-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAuCS84ZrOW5wQYhEpW1EhTpOR4vW1RZ9eYeOH5hN9JJrKEHc/
nnj2fYD2KXIPTFu68VAmHaCoXwlHcdbBKPJu/tUVjKEIVA4UfEQ+2/1kHfvq13y6
fnd3cOagcG3GHsMJ3bc2BY2gPp+hSpfdwUSrM7PkgZ+jgKSqbC9jkDYtEhnlH3dD
ytO5GtuteX4kkPustFpmj4dDmJFqKWZv5SO8Hes1oWv9YORiAzhoxHSO9w83/ofm
xNJImYh4URUGN7JVggaN2N5fUVw7hBpdFJEfRLs4cDR0vJkF5W8tup5vj7cp2ylJ
H5STeYMQ0jePl8IpqNuIzbnU/WaKzFZG0lUF3wIDAQABAoIBADTAIXOnezH3FSJi
tCw6o4X09DfGF3WoX8s++PFJ5/GSfgwVfR4SnNn7FYlt6UAAjx8NzL10BoejCtpr
oM3wFSffNtsgTlh16BxpGHDAt+t2/SFZ07ri0k5/YrqSV8z8JlljYJBar+sAo53Q
v2/cEgcvo2gWqSnzAfcX5DetrV+fmiUltTB2gBQJ5k/rH7YzdO4KLqp2K922DfRG
YmEIMQxqsrkjWEPE44WP0gxTaq/7RZ//UWowz1zip2NHAkAzHs/1nYs+/dXkjJHS
nmnD5h2FTOHPi94UCybJxNIj+StH+VHyW+idOQMIsIRBpRu1It3Ywkd7icvZAqGY
n/i99RECgYEA9F+zpCZ8rQHfCegSwEyeU3QZupD+XOUUSQJWA0fBJIwxK4GP8+0Q
saDETyYo9rTUXekgmuv1Yuo82aQ+B1zXWJa5JWH3x+su985+3YZKXy05XO3ZqEHZ
NnDqIKaf1eI6HyvBybHbe8YUtxqazkTdD6i8I6902ZlaKKR3pSXWq6sCgYEAwOd5
TbAgK0oFlExgBj5EYSqqXhjsI33RrTBHA2+BmVVnsMjOoJrIU4udlfLDYsJ9UYs7
XpbqrO+2B88IgA1RFpEwzofpONX8XCPL4Am7OsueL/RmOuF0tuY0ATdT8WvNbkFk
9qXARSjQEkCYnlfM7lMykLj1FehHM7seud9bOp0CgYARQcDZ0q3zObKabH0Gf2Ke
2hAHEL4lqTepgDS6vpJxFkVSoS+dNhx7rrKuNC+oXFSy3QekaQ1HEuuBIwwOUQwU
AXDJpwVsZLtIXJiw5A7UcckfOtyn+R5xrb+a1qlq3TLliJ2CtMCfGPnVhFdyQYKq
3GuMyZMi2qV3QUYBr45dSQKBgHTH7SS9+kuarVQBBKTi70yPosICfnpiAhzBvEv1
JlUoYfShLI4IBjylqgoMBIL2UR2bl56E6J83I1EI4hF7flqWHSD7IJK64OL6/MKt
wX4vpJ1NbNI6iQjsxhDyaMwfwib8Sd4TrBlyQry6BGrfpn2lOlho0F6p1ukXX9uQ
v071AoGBAJJO+2RBUsCbDytTCP2pvulEy+p0mBiZ/DQrGjquBBB2PQ7nW8XbVp1O
9y6EDLBC34X3DIUZLGcBcCeR6Tm3jp2nTCbNcVivDBSp1dalXcsB8B84T9nYAMSN
ELDTXzkmV/eqakXQVhwEhKH1ff00h8xF/VT2DE3yy9RC0jZ0vfKL
-----END RSA PRIVATE KEY-----""")


class TestX509Utils(unittest.TestCase):
    """ Tests of the X509Utils module. """

    def test_openssl_to_rfc(self):
        """ Test X509Utils.openssl_to_rfc. """
        # Test some DNs in various formats
        TEST_PAIRS = [
            # Simple conversion
            ('/C=XX/L=YY/OU=ZZ',
             'C = XX, L = YY, OU = ZZ'),
            # Input already in correct format
            ('C = XX, L = YY, OU = ZZ',
             'C = XX, L = YY, OU = ZZ'),
        ]
        for test_in, test_out in TEST_PAIRS:
            self.assertEqual(X509Utils.openssl_to_rfc(test_in),
                             test_out)
        # Test error cases
        self.assertRaises(ValueError, X509Utils.openssl_to_rfc, "")

    def test_rfc_to_openssl(self):
        """ Test X509Utils.rfc_to_openssl. """
        TEST_PAIRS = [
            # Simple Conversion
            ('C = XX, L = YY, OU = ZZ',
             '/C=XX/L=YY/OU=ZZ'),
            # Input already in correct format
            ('/C=XX/L=YY/OU=ZZ',
             '/C=XX/L=YY/OU=ZZ'),
        ]
        for test_in, test_out in TEST_PAIRS:
            self.assertEqual(X509Utils.rfc_to_openssl(test_in),
                             test_out)
        self.assertRaises(ValueError, X509Utils.rfc_to_openssl, "")

    def test_x509name(self):
        """ Test the X509_Name import/export functions. """
        from M2Crypto import X509
        # Convert a DN into an object and back
        TEST_DN = 'C = UK, L = London, O = Test Corp., OU = Security, CN = DN Tester'
        x509_obj = X509Utils.str_to_x509name(TEST_DN)
        self.assertIsInstance(x509_obj, X509.X509_Name)
        self.assertEqual(x509_obj.C, 'UK')
        self.assertEqual(x509_obj.L, 'London')
        self.assertEqual(x509_obj.O, 'Test Corp.')
        self.assertEqual(x509_obj.OU, 'Security')
        self.assertEqual(x509_obj.CN, 'DN Tester')
        self.assertEqual(X509Utils.x509name_to_str(x509_obj), TEST_DN)
        # Bonus: Convert a DN with two similar segments
        TEST_DN = 'C = UK, CN = Test User, CN = Proxy'
        x509_obj = X509Utils.str_to_x509name(TEST_DN)
        self.assertIsInstance(x509_obj, X509.X509_Name)
        # Interface currently prevents access to multiple fields
        # i.e. x509_obj.CN will only return "Test User".
        # Just check that all fields appear if object is converted back:
        self.assertEqual(X509Utils.x509name_to_str(x509_obj), TEST_DN)
        

class TestX509CA(unittest.TestCase):
    """ Tests of the X509CA module. """

    def setUp(self):
        """ Just get an instance of the test object. """
        self.__ca = X509CA()

    def test_ready(self):
        """ Check that the ready flag works as expected. """
        # Unconfigured CA should return ready == False
        # and raise if any get methods are called.
        self.__ca.gen_ca("/C=XX/L=YY/CN=Test CA", 1234)
        self.assertTrue(self.__ca.ready())
        self.__ca.clear()
        self.assertFalse(self.__ca.ready())
        self.assertRaises(RuntimeError, self.__ca.get_cert)
        self.assertRaises(RuntimeError, self.__ca.get_key)
        self.assertRaises(RuntimeError, self.__ca.get_dn)
        self.assertRaises(RuntimeError, self.__ca.get_serial)

    def test_get_dn(self):
        """ Check the get DN function. """
        self.__ca.gen_ca("/C=XX/L=YY/CN=Test CA", 1234)
        self.assertTrue(self.__ca.ready())
        # Get DN returns value in RFC format.
        self.assertEquals(self.__ca.get_dn(),
                          "C = XX, L = YY, CN = Test CA")


    @mock.patch('M2Crypto.X509.Request')
    def test_gen_req_errors(self, req_constr):
        """ Check that any errors created while generating the CA request
            actually result in an exception (otherwise a malformed CA may
            be generated).
        """
        constr_params = ("/C=ZZ/CN=Another CA", 5)
        req_obj = mock.MagicMock()
        req_constr.return_value = req_obj
        REQ_FN = [
            'set_version',
            'set_subject_name',
            'set_pubkey',
            'sign',
        ]
        for fcn in REQ_FN:
            print "Testing errors on function %s" % fcn
            getattr(req_obj, fcn).return_value = 0
            self.assertRaises(RuntimeError, self.__ca.gen_ca, *constr_params)
            self.assertTrue(getattr(req_obj, fcn).called)
            getattr(req_obj, fcn).return_value = 1

    @mock.patch('M2Crypto.m2.x509_get_not_after')
    @mock.patch('M2Crypto.m2.x509_get_not_before')
    @mock.patch('M2Crypto.X509.X509')
    def test_gen_ca_errors(self, x509_constr, not_before, not_after):
        """ Checks that errors created while generating the CA cert are
            correctly converted into exceptions.
        """
        constr_params = ("/C=ZZ/CN=Another CA", 5)
        x509_obj = mock.MagicMock()
        x509_constr.return_value = x509_obj
        not_before.return_value = None
        not_after.return_value = None
        X509_FN = [
            'set_version',
            'set_serial_number',
            'set_subject',
            'set_issuer',
            'set_pubkey',
            'add_ext',
            'sign',
        ]
        for fcn in X509_FN:
            print "Testing errors on function %s" % fcn
            getattr(x509_obj, fcn).return_value = 0
            self.assertRaises(RuntimeError, self.__ca.gen_ca, *constr_params)
            self.assertTrue(getattr(x509_obj, fcn).called)
            getattr(x509_obj, fcn).return_value = 1

    @mock.patch('M2Crypto.m2.x509_get_not_after')
    @mock.patch('M2Crypto.m2.x509_get_not_before')
    @mock.patch('M2Crypto.X509.X509')
    def test_gen_cert_errors(self, x509_constr, not_before, not_after):
        """ Check that any errors returned while generating the CA cert
            correctly get converted into exceptions.
            This only does the non-CA cert specific errors, everything else
            should be covered by test_gen_ca_errors.
        """
        x509_obj = mock.MagicMock()
        x509_constr.return_value = x509_obj
        not_before.return_value = None
        not_after.return_value = None
        # Create CA certificate
        self.__ca.gen_ca("/C=ZZ/CN=Issuer CA", 5)
        # Now test the error handling
        X509_FN = [
            'add_ext',
            'sign',
        ]
        CERT_PARAMS = ("/C=ZZ/CN=Test Cert", 1, "test@test.test")
        for fcn in X509_FN:
            print "Testing errors on function %s" % fcn
            getattr(x509_obj, fcn).return_value = 0
            self.assertRaises(RuntimeError, self.__ca.gen_cert, *CERT_PARAMS)
            self.assertTrue(getattr(x509_obj, fcn).called)
            getattr(x509_obj, fcn).return_value = 1
        # We also have to check that adding the altName fails in the correct
        # way, this is hidden behind another all to add_ext
        def add_ext_altfail(ext):
            if ext.get_name() == 'subjectAltName':
                return 0
            return 1
        x509_obj.add_ext.called = False
        x509_obj.add_ext.side_effect = add_ext_altfail
        self.assertRaises(RuntimeError, self.__ca.gen_cert, *CERT_PARAMS)
        self.assertTrue(x509_obj.add_ext.called)
        x509_obj.add_ext.side_effect = None

    def test_gen_serial(self):
        """ Check that gen_ca serial checking works correctly. """
        constr_params = ("/C=ZZ/CN=Another CA", 5)
        # No serial, should set serial to 2.
        self.__ca.gen_ca(*constr_params)
        self.assertEquals(self.__ca.get_serial(), 2)
        self.__ca.gen_ca(*constr_params, serial=123)
        self.assertEquals(self.__ca.get_serial(), 123)
        # Also check for bad serial errors
        self.assertRaises(ValueError, self.__ca.gen_ca,
                          *constr_params, serial=-100)
        self.assertRaises(ValueError, self.__ca.gen_ca,
                          *constr_params, serial=0)
        self.assertRaises(ValueError, self.__ca.gen_ca,
                          *constr_params, serial=1)

    def test_import_export(self):
        """ Check that we can export a CA to PEM and then
            re-import it again afterwards. Both with and
            without a passphrase.
        """
        TEST_DN = "C = ZZ, CN = Yet Another CA"
        constr_params = (TEST_DN, 4)
        for passphrase in (None, 'weakpass'):
            print "Test passphrase: %s" % passphrase
            # Init CA
            self.__ca.clear()
            self.assertFalse(self.__ca.ready())
            self.__ca.gen_ca(*constr_params, serial=44)
            self.assertTrue(self.__ca.ready())
            # Now export the CA details
            cert = self.__ca.get_cert()
            key = self.__ca.get_key(passphrase)
            serial = self.__ca.get_serial()
            # Check the CA details
            self.assertIsInstance(cert, str)
            self.assertIsInstance(key, str)
            self.assertIsInstance(serial, int)
            self.assertTrue('BEGIN CERTIFICATE' in cert)
            self.assertTrue('BEGIN RSA PRIVATE KEY' in key)
            self.assertEqual(serial, 44)
            # Clear and re-import 
            self.__ca.clear()
            self.assertFalse(self.__ca.ready())
            self.__ca.set_ca(cert, key, serial, passphrase)
            self.assertTrue(self.__ca.ready())
            self.assertEqual(self.__ca.get_serial(), 44)
            self.assertEqual(self.__ca.get_dn(), TEST_DN)
            # Finally, test the serial error handling
            self.assertRaises(ValueError, self.__ca.set_ca,
                              cert, key, -123, passphrase)
            self.assertRaises(ValueError, self.__ca.set_ca,
                              cert, key, 0, passphrase)
            self.assertRaises(ValueError, self.__ca.set_ca,
                              cert, key, 1, passphrase)

    def test_gen_cert(self):
        """ Check issuing a client certificate. """
        from M2Crypto import X509, RSA
        TEST_ISSUER = "C = ZZ, L = YY, O = Test CA, CN = Basic Test CA"
        TEST_SUBJECT = "C = ZZ, L = YY, CN = Test User"
        TEST_EMAIL = "test@test.test"
        TEST_DAYS = 3
        self.__ca.gen_ca(TEST_ISSUER, 5)
        start_serial = self.__ca.get_serial()
        cert, key = self.__ca.gen_cert(TEST_SUBJECT,
                                       valid_days=TEST_DAYS, email=TEST_EMAIL)
        self.assertTrue('BEGIN CERTIFICATE' in cert)
        self.assertTrue('BEGIN RSA PRIVATE KEY' in key)
        # Load the cert and check its properties
        cert_obj = X509.load_cert_string(cert)
        self.assertEqual(cert_obj.get_serial_number(), start_serial)
        cert_subject = X509Utils.x509name_to_str(cert_obj.get_subject())
        self.assertEqual(cert_subject, TEST_SUBJECT)
        cert_issuer = X509Utils.x509name_to_str(cert_obj.get_issuer())
        self.assertEqual(cert_issuer, TEST_ISSUER)
        # Check cert times
        from datetime import datetime
        start_time = cert_obj.get_not_before().get_datetime()
        end_time = cert_obj.get_not_after().get_datetime()
        valid_time = end_time - start_time
        self.assertEqual(valid_time.days,TEST_DAYS)
        self.assertEqual(valid_time.seconds, 0)
        # Check cert started in the last 60 seconds
        # I'm not sure this will work in BST, I guess we'll see.
        start_diff = datetime.now(start_time.tzinfo) - start_time
        self.assertEqual(start_diff.days, 0)
        self.assertLess(start_diff.seconds, 60)
        # Check cert extensions
        self.assertEqual(cert_obj.get_ext('basicConstraints').get_value(),
                         'CA:FALSE')
        self.assertEqual(cert_obj.get_ext('subjectAltName').get_value(),
                         'email:%s' % TEST_EMAIL)
        # Check that the CA's serial number increased
        self.assertGreater(self.__ca.get_serial(), start_serial)
        # Issue another cert, but with an encrypted private key
        cert, key = self.__ca.gen_cert("C = ZZ, L = YY, CN = Test User 2",
                                        valid_days=3, email="test2@test.com",
                                        passphrase="weakpass")
        # Check that key is encrypted correctly
        self.assertRaises(RSA.RSAError, RSA.load_key_string, key,
                          callback=lambda x: None)
        self.assertRaises(RSA.RSAError, RSA.load_key_string, key,
                          callback=lambda x: "wrongpass")
        key_obj = RSA.load_key_string(key, callback=lambda x: "weakpass")
        self.assertIsInstance(key_obj, RSA.RSA)

    def test_gen_proxy(self):
        """ Test generating a user proxy. """
        from M2Crypto import X509, RSA
        TEST_DAYS = 1
        USER_DN = "C = XX, CN = Test User"
        self.__ca.gen_ca("C = XX, CN = Test CA", 5)
        usercert, userkey = self.__ca.gen_cert(USER_DN, 4)
        proxycert, proxykey = self.__ca.gen_proxy(usercert, userkey,
                                                  TEST_DAYS)
        # TODO: Actually check proxy here!
        # Check proxy looks fine
        proxy_obj = X509.load_cert_string(proxycert)
        proxy_serial = proxy_obj.get_serial_number()
        proxy_subject = X509Utils.x509name_to_str(proxy_obj.get_subject())
        exp_proxy_subj = "%s, CN = %u" % (USER_DN, proxy_serial)
        self.assertEqual(exp_proxy_subj, proxy_subject)
        proxy_issuer = X509Utils.x509name_to_str(proxy_obj.get_issuer())
        self.assertEqual(proxy_issuer, USER_DN)
        # Check proxy times
        from datetime import datetime
        start_time = proxy_obj.get_not_before().get_datetime()
        end_time = proxy_obj.get_not_after().get_datetime()
        valid_time = end_time - start_time
        self.assertEqual(valid_time.days,TEST_DAYS)
        self.assertEqual(valid_time.seconds, 0)
        # Test generating proxy with passphrase
        USER_PASSPHRASE = "weaktest"
        usercert, userkey = self.__ca.gen_cert("/C=XX, CN=Test User", 4,
                                               passphrase=USER_PASSPHRASE)
        self.assertRaises(RSA.RSAError, self.__ca.gen_proxy, usercert,
                          userkey, 1)
        self.assertRaises(RSA.RSAError, self.__ca.gen_proxy, usercert,
                          userkey, 1, "wrongtest")
        proxycert, proxykey = self.__ca.gen_proxy(usercert, userkey,
                                                  1, USER_PASSPHRASE)

    @mock.patch('M2Crypto.m2.x509_get_not_after')
    @mock.patch('M2Crypto.m2.x509_get_not_before')
    @mock.patch('M2Crypto.X509.X509')
    def test_gen_proxy_errors(self, x509_constr, not_before, not_after):
        """ Test all possible error conditions on generating a proxy.
            Only includes tests not tested by general certificate tests.
        """
        x509_obj = mock.MagicMock()
        x509_constr.return_value = x509_obj
        not_before.return_value = None
        not_after.return_value = None
        # We use a pregenerated usercert & key
        usercert, userkey = TESTCERT_AND_KEY
        # Check sign failures
        x509_obj.sign.return_value = 0
        self.assertRaises(RuntimeError, self.__ca.gen_proxy,
                          usercert, userkey, 1)
        self.assertTrue(x509_obj.sign.called)
        x509_obj.sign.return_value = 1
        # Now we have to check the
        def add_ext_fail(fail_ext, ext):
            print ext.get_name()
            if ext.get_name() == fail_ext:
                return 0
            return 1
        x509_obj.add_ext.called = False
        x509_obj.add_ext.side_effect = partial(add_ext_fail, 'keyUsage')
        self.assertRaises(RuntimeError, self.__ca.gen_proxy,
                          usercert, userkey, 1)
        self.assertTrue(x509_obj.add_ext.called)
        x509_obj.add_ext.called = False
        x509_obj.add_ext.side_effect = partial(add_ext_fail, 'proxyCertInfo')
        self.assertRaises(RuntimeError, self.__ca.gen_proxy,
                          usercert, userkey, 1)
        self.assertTrue(x509_obj.add_ext.called)
        x509_obj.add_ext.side_effect = None
