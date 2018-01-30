#!/usr/bin/env python

import mock
import unittest

from pdm.utils.X509 import X509Utils, X509CA


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
