#!/usr/bin/env python

import os
import mock
import unittest
from functools import partial

from pdm.utils.X509 import X509Utils


# We need a keypair for testing proxy generation
# It doesn't matter that these are expired and we don't
# have a CA.
TESTCERT_HASH = "4ee00b4f" # OpenSSL hash for this cert
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
        TEST_DN = 'C=UK, L=London, O=Test Corp., OU=Security, CN=DN Tester'
        x509_obj = X509Utils.str_to_x509name(TEST_DN)
        self.assertIsInstance(x509_obj, X509.X509_Name)
        self.assertEqual(x509_obj.C, 'UK')
        self.assertEqual(x509_obj.L, 'London')
        self.assertEqual(x509_obj.O, 'Test Corp.')
        self.assertEqual(x509_obj.OU, 'Security')
        self.assertEqual(x509_obj.CN, 'DN Tester')
        self.assertEqual(X509Utils.x509name_to_str(x509_obj), TEST_DN)
        # Bonus: Convert a DN with two similar segments
        TEST_DN = 'C=UK, CN=Test User, CN=Proxy'
        x509_obj = X509Utils.str_to_x509name(TEST_DN)
        self.assertIsInstance(x509_obj, X509.X509_Name)
        # Interface currently prevents access to multiple fields
        # i.e. x509_obj.CN will only return "Test User".
        # Just check that all fields appear if object is converted back:
        self.assertEqual(X509Utils.x509name_to_str(x509_obj), TEST_DN)

    def test_dn_normalisation(self):
        """ Test the X509 DN normalisation function. """
        # Test DN in expected output format
        TEST_DN = "C=XX, L=YY, CN=Test CA"
        # Test both RFC and OpenSSL style DNs with increasing amounts of space
        # All should match the TEST_DN after normalisation.
        self.assertEqual(X509Utils.normalise_dn(TEST_DN), TEST_DN)
        self.assertEqual(X509Utils.normalise_dn("/C=XX/L=YY/CN=Test CA"),
                         TEST_DN)
        self.assertEqual(X509Utils.normalise_dn("/C=XX / L =  YY /  CN = Test CA  "),
                         TEST_DN)
        # Check that leading space doesn't upset the algorithm
        self.assertEqual(X509Utils.normalise_dn("   / C =XX / L =  YY /  CN = Test CA  "),
                         TEST_DN)
        self.assertEqual(X509Utils.normalise_dn("C = XX, L = YY, CN = Test CA"),
                         TEST_DN)
        self.assertEqual(X509Utils.normalise_dn("C  =  XX,   L  =  YY,    CN = Test CA   "),
                         TEST_DN)
        self.assertEqual(X509Utils.normalise_dn("     C  =  XX,   L  =  YY,    CN = Test CA"),
                         TEST_DN)

    def test_get_cert_expiry(self):
        """ Test that the get_cert_expiry function works. """
        from M2Crypto import X509
        # Just generate a CA and get its expiry time
        test_ca = X509CA()
        test_ca.gen_ca("/C=XX/L=YY/CN=Test CA", 1234)
        ca_pem = test_ca.get_cert()
        ca_obj = X509.load_cert_string(ca_pem)
        ca_exp = ca_obj.get_not_after().get_datetime()
        self.assertEqual(X509Utils.get_cert_expiry(ca_pem), ca_exp)
        
    @mock.patch("pdm.utils.X509.open", create=True)
    @mock.patch("pdm.utils.X509.os")
    @mock.patch("pdm.utils.X509.tempfile")
    def test_add_ca_to_dir(self, temp_mock, os_mock, open_mock):
        """ Test the add_ca_to_dir functions. """
        os_mock.path.join.side_effect = os.path.join
        os_mock.path.exists.return_value = False
        cert_pem = TESTCERT_AND_KEY[0]
        cert_hash = TESTCERT_HASH
        # Try just writing a single CA and check it gets written to the
        # correct name.
        res = X509Utils.add_ca_to_dir([cert_pem], "/mydir")
        self.assertEqual(res, "/mydir")
        open_mock.assert_has_calls([
            mock.call("/mydir/%s.0" % cert_hash, "w"),
            mock.call("/mydir/%s.signing_policy" % cert_hash, "w")],
            any_order=True)
        # Test directory creation
        temp_mock.mkdtemp.return_value = "/tmpca.test"
        res = X509Utils.add_ca_to_dir([cert_pem])
        self.assertEqual(res, "/tmpca.test")
        # Check that duplicate CA causes an exception
        os_mock.path.exists.return_value = True
        self.assertRaises(Exception, X509Utils.add_ca_to_dir,
                          [cert_pem], "/mydir")
        def pol_exists(path):
            return path.endswith('.signing_policy')
        os_mock.path.exists.side_effect = pol_exists
        self.assertRaises(Exception, X509Utils.add_ca_to_dir,
                          [cert_pem], "/mydir")

