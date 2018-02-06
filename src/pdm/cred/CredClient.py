#!/usr/bin/env python
""" Credential service client module. """

import sys
import string
import random
import datetime
from pdm.framework.RESTClient import RESTClient

class CredClient(RESTClient):
    """ Client class for CredService service. """

    def __init__(self):
        """ Create the credential client. """
        super(CredClient, self).__init__('cred')

    def ca(self):
        """ Get the user CA certificate.
            Returns CA cert in PEM format.
        """
        return self.get('ca')['ca']

    def add_user(self, user_id, user_key, user_email=None):
        """ Adds a set of user credentials.
            user_id - The numeric user ID.
            user_key - An encryption key for the creds.
            user_email - Optional user email string.
            Returns Nothing, raises on error.
        """
        data = {}
        data['user_id'] = user_id
        data['user_key'] = user_key
        if user_email:
            data['user_email'] = user_email
        self.post('user', data)

    def del_user(self, user_id):
        """ Delete a user cred set by ID.
            Returns Nothing.
        """
        self.delete('user/%u' % user_id)

    def user_expiry(self, user_id):
        """ Get the expiry time of user creds.
            Returns a datetime.datetime object with the expiry time.
        """
        res = self.get('user/%u' % user_id)
        expiry = datetime.datetime.strptime(res['valid_until'], 
                                            "%Y-%m-%dT%H:%M:%S")
        return expiry

    def add_cred(self, user_id, user_key, cred_type):
        """ Adds a credential of a given type for a job.
            user_id - The user ID int.
            user_key - The credential key, matching the value given to
                       ad_user.
            cred_type - The cred type to get, one of CredService.CRED_TYPE_*
            Returns a token string.
        """
        data = {}
        data['user_id'] = user_id
        data['user_key'] = user_key
        data['cred_type'] = cred_type
        data['max_lifetime'] = sys.maxint
        res = self.post('cred', data)
        return res['token']

    def del_cred(self, token):
        """ Delete a credential by token.
            Returns Nothing.
        """
        self.delete('cred/%s' % token)

    def get_cred(self, token):
        """ Gets a credential by token.
            Returns a tuple of strings:
              (pub_key, priv_key)
        """
        res = self.get('cred/%s' % token)
        return (str(res['pub_key']),
                str(res['priv_key']))


class MockCredClient(object):
    """ Mock client class for CredService service.
        Returns a set of static values.
    """

    CA_STR = "---BEGIN CERTIFICATE---"
    CERT_STR = "CERT_PEM_STR"
    KEY_STR = "KEY_PEM_STR"

    def __init__(self):
        """ Create the credential client. """
        self.__valid_users = {}
        self.__creds = []

    def ca(self):
        """ Get the user CA certificate.
            Returns CA cert in PEM format.
        """
        return MockCredClient.CA_STR

    def add_user(self, user_id, user_key, user_email=None):
        """ Adds a set of user credentials.
            user_id - The numeric user ID.
            user_key - An encryption key for the creds.
            user_email - Optional user email string.
            Returns Nothing, raises on error.
        """
        self.__valid_users[user_id] = user_key

    def del_user(self, user_id):
        """ Delete a user cred set by ID.
            Returns Nothing.
        """
        if not user_id in self.__valid_users:
            raise RuntimeError("Request failed with code 404.")
        del self.__valid_users[user_id]

    def user_expiry(self, user_id):
        """ Get the expiry time of user creds.
            Returns a datetime.datetime object with the expiry time.
        """
        next_day = datetime.datetime.now() \
                       + datetime.timedelta(days=1)
        return next_day

    def add_cred(self, user_id, user_key, cred_type):
        """ Adds a credential of a given type for a job.
            user_id - The user ID int.
            user_key - The credential key, matching the value given to
                       ad_user.
            cred_type - The cred type to get, one of CredService.CRED_TYPE_*
            Returns a token string.
        """
        if not user_id in self.__valid_users:
            raise RuntimeError("Request failed with code 404.")
        if self.__valid_users[user_id] != user_key:
            raise RuntimeError("Request failed with code 500.")
        token = ''.join([random.choice(string.lowercase) for _ in xrange(32)])
        self.__creds.append(token)
        return token

    def del_cred(self, token):
        """ Delete a credential by token.
            Returns Nothing.
        """
        if not token in self.__creds:
            raise RuntimeError("Request failed with code 404.")
        self.__creds.remove(token)

    def get_cred(self, token):
        """ Gets a credential by token.
            Returns a tuple of strings:
              (pub_key, priv_key)
        """
        if not token in self.__creds:
            raise RuntimeError("Request failed with code 404.")
        return (self.CERT_STR, self.KEY_STR)
