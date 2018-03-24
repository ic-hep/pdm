#!/usr/bin/env python

class ACLManager(object):
    """ Access Control List manager for Flask Wrapper.
        Keeps a list of users who are allowed to access resources
        and allows or rejects request based on the presented credentials.
    """

    AUTH_MODE_NONE = 0
    AUTH_MODE_X509 = 1
    AUTH_MODE_TOKEN = 2
    AUTH_MODE_ALLOW_ALL = 3

    def __init__(self, logger):
        """ Create an empty instance of ACLManager (no predfined groups or
            rules. Test mode is disabled by default.
        """
        self.__log = logger
        self.__test_mode = ACLManager.AUTH_MODE_NONE
        self.__test_data = None
        self.__groups = {}
        self.__rules = {}

    def add_group_entry(self, group_name, entry):
        """ Adds an entry to a group, if the group doesn't exist it will be
            created, otherwise it will be appeneded. Note that groups can't
            currently be nested.
        """
        pass

    def add_rule(self, res_path, entry):
        """ Adds a rule for a specific resource path. The entry can either
            be an existing group or a normal entry value.
        """
        pass

    def test_mode(self, auth_mode, auth_data=None):
        """ Enabled test mode, where the authentication info is pre-set for
            all requests. This should not be used in production.
        """
        pass

    def dump_debug(self):
        """ Dumps the configuration of the ACLManager to the logger
            at the debug level. This includes all group and rule configuration.
        """
        pass

    def check_request(self):
        """ Gets the current flask request object and checks it against the
            configured rule set.
        """
        pass

