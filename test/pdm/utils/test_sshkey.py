#!/usr/bin/env python
""" Test for SSH key utils. """

import unittest

from pdm.utils.sshkey import SSHKeyUtils

class TestSSHKeyUtils(unittest.TestCase):
    """ Test the SSHKeyUtils functions. """

    def test_gen_key(self):
        """ Test SSH key generation. """
        from M2Crypto import RSA
        # Just generate a plain key.
        pubkey, privkey = SSHKeyUtils.gen_rsa_keypair()
        # pubkey should have 3 parts
        pub_parts = pubkey.split(' ', 3)
        self.assertEqual(pub_parts[0], 'ssh-rsa')
        # RSA SSH keys always start with the same header
        self.assertTrue(pub_parts[1].startswith("AAAAB3NzaC1yc2EAAAA"))
        # We asked for no comment, so this one should be empty.
        self.assertEqual(pub_parts[2], '')
        # Check we can load the private key
        key_obj = RSA.load_key_string(privkey)
        self.assertIsInstance(key_obj, RSA.RSA)

    def test_enc_gen_key(self):
        """ Test encrypted SSH key generation. """
        from M2Crypto import RSA
        TEST_PASS = "weakpass"
        TEST_COMMENT = "my encrypted sshkey"
        pubkey, privkey = SSHKeyUtils.gen_rsa_keypair(TEST_PASS, TEST_COMMENT)
        # Check the comment was set correctly
        comment = pubkey.split(' ', 2)[2]
        self.assertEqual(comment, TEST_COMMENT)
        # Check the key is encrypted
        pw_cb = lambda x: None
        self.assertRaises(RSA.RSAError, RSA.load_key_string,
                          privkey, callback=pw_cb)
        pw_cb = lambda x: "wrongpass"
        self.assertRaises(RSA.RSAError, RSA.load_key_string,
                          privkey, callback=pw_cb)
        pw_cb = lambda x: TEST_PASS
        key_obj = RSA.load_key_string(privkey, callback=pw_cb)
        self.assertIsInstance(key_obj, RSA.RSA)
