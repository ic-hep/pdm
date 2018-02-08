#!/usr/bin/env python
""" Test the hashing util module. """

import unittest

from pdm.utils.hashing import hash_pass, check_hash

class TestHashing(unittest.TestCase):
    """ Test the hashing functions. """

    def test_hashing(self):
        test_hash = hash_pass("Test String")
        # Basic check
        self.assertTrue(check_hash(test_hash, "Test String"))
        self.assertFalse(check_hash(test_hash, "Other String"))
        # Check salting
        TEST_STR = "Another Test"
        hash1 = hash_pass(TEST_STR)
        hash2 = hash_pass(TEST_STR)
        self.assertNotEqual(hash1, hash2)
        self.assertTrue(check_hash(hash1, TEST_STR))
        self.assertTrue(check_hash(hash2, TEST_STR))
        # Check invalid hashes
        self.assertRaises(ValueError, check_hash, "Not Hashed!", "X")
        self.assertRaises(ValueError, check_hash, "$4$ABC$DEF", "X")
        self.assertRaises(ValueError, check_hash, "$5$123$123", "X")

    def test_hash_salt(self):
        """ Test that hashing with a fixed salt works correctly. """
        test_hash1 = hash_pass("Test", "my salt")
        test_hash2 = hash_pass("Test", "my salt")
        self.assertEqual(test_hash1, test_hash2)
        test_hash3 = hash_pass("Test", "my salt2")
        self.assertNotEqual(test_hash1, test_hash3)
        # Extract actual hash and check that it's really different
        real_hash1 = test_hash1.split("$")[-1]
        real_hash3 = test_hash3.split("$")[-1]
        self.assertNotEqual(real_hash1, real_hash3)
