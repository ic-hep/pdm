#!/usr/bin/env python
""" Test cases for framework Token module. """

import unittest

from pdm.framework.Tokens import TokenService

class TokenServiceTest(unittest.TestCase):
    """ Test TokenService functions. """

    def test_basic(self):
        """ Test generating and recovering a token. """
        svc = TokenService()
        TEST_STR = "Hello World"
        token = svc.issue(TEST_STR)
        res = svc.check(token)
        self.assertEqual(TEST_STR, res)
        # Check bad token case
        self.assertRaises(ValueError, svc.check, "BadToken")

    def test_salt(self):
        """ Check that setting the salt works. """
        TEST_STR = "Salt Test"
        svc1 = TokenService(key="FixedKey", salt="salt1")
        token1 = svc1.issue(TEST_STR)
        svc2 = TokenService(key="FixedKey", salt="salt2")
        token2 = svc2.issue(TEST_STR)
        self.assertNotEqual(token1, token2)
        self.assertRaises(ValueError, svc1.check, token2)
        self.assertRaises(ValueError, svc2.check, token1)
        self.assertEqual(TEST_STR, svc1.check(token1))
        self.assertEqual(TEST_STR, svc2.check(token2))

    def test_key(self):
        """ Check that different keys yield different results. """
        TEST_STR = "Key Test"
        svc1 = TokenService(key="KeyA")
        token1 = svc1.issue(TEST_STR)
        svc2 = TokenService(key="KeyB")
        token2 = svc2.issue(TEST_STR)
        self.assertNotEqual(token1, token2)
        self.assertRaises(ValueError, svc1.check, token2)
        self.assertRaises(ValueError, svc2.check, token1)
        self.assertEqual(TEST_STR, svc1.check(token1))
        self.assertEqual(TEST_STR, svc2.check(token2))

    def test_inst(self):
        """ Check that two instances with the same parameters
            generate compatible tokens.
        """
        TEST_STR = "Inst Test"
        params = ("KeyStr", "SaltStr")
        svc1 = TokenService(*params)
        token1 = svc1.issue(TEST_STR)
        svc2 = TokenService(*params)
        token2 = svc2.issue(TEST_STR)
        # Tokens should be identical
        self.assertEqual(token1, token2)
        self.assertEqual(TEST_STR, svc1.check(token2))

    def test_unpack(self):
        """ Test that the unpacker without verification works
            correctly.
        """
        TEST_OBJ = {"a": "field1", "b": "ASD" }
        svc = TokenService()
        token = svc.issue(TEST_OBJ)
        retval = TokenService.unpack(token)
        self.assertDictEqual(TEST_OBJ, retval)
        # Check the error handling
        self.assertRaises(ValueError, svc.unpack, "not_a_token")
