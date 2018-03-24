#!/usr/bin/env python

from flask import request


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
        self.__test_mode = auth_mode
        self.__test_data = auth_data

    @staticmethod
    def __get_real_request_auth():
        # Cert auth
        if 'Ssl-Client-Verify' in request.headers \
            and 'Ssl-Client-S-Dn' in request.headers:
            # Request has client cert
            if request.headers['Ssl-Client-Verify'] == 'SUCCESS':
                request.dn = request.headers['Ssl-Client-S-Dn']
        # Token Auth
        if 'X-Token' in request.headers:
            raw_token = request.headers['X-Token']
            try:
                token_value = current_app.token_svc.check(raw_token)
                request.token = token_value
                request.token_ok = True
            except ValueError:
                # Token decoding failed, it is probably corrupt or has been
                # tampered with.
                current_app.log.info("Request %s token validation failed.",
                                     req_uuid)
                return "403 Invalid Token", 403

    def __get_fake_request_auth(self):
        if self.__test_mode == ACLManager.AUTH_MODE_X509:
            request.dn = self.__test_data
        elif self.__test_mode == ACLManager.AUTH_MODE_TOKEN:
            request.token = self.__test_data
            request.token_ok = True

    def check_request(self):
        """ Gets the current flask request object and checks it against the
            configured rule set.
        """
        request.dn = None
        request.token = None
        request.token_ok = False
        if self.__test_mode == ACLManager.AUTH_MODE_NONE:
            self.__get_real_request_auth()
        else:
            self.__get_fake_request_auth()
