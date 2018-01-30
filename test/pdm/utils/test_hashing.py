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
