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
    def test_gen_cert_errors(self, x509_constr, not_before, not_after):
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
