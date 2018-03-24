#!/usr/bin/env python
""" ACLManager module tests. """

import logging
import unittest

from pdm.framework.ACLManager import ACLManager

class TestACLManager(unittest.TestCase):
    """ Test the ACLManager class. """

    def setUp(self):
        """ Create an instance of ACLManager to test. """
        self.__inst = ACLManager(logging.getLogger())

    def __gen_req(self, method, path, auth_mode, auth_data):
        """ Call self.__inst.check_request while generating a fake request
            with the given parameters (without using test_mode on the 
            ACLManager).
            Returns True if the request was successful (i.e. access would
            have been allowed).
        """
        # TODO: implement this
        return False

    def test_basic(self):
        """ Add simple ANY rules and see if they work. """
        # TODO: implement this
        pass

    def test_groups(self):
        """ Check that groups are applied correctly. """
        # TODO: implement this
        pass

    def test_auth_modes(self):
        """ Check that all auth modes work as expected. """
        # TODO: implement this
        pass

    def test_test_mode(self):
        """ Check that test mode works correctly. """
        # TODO: implement this
        pass

    def test_wildcards(self):
        """ Check that test mode works correctly. """
        # TODO: implement this
        pass

