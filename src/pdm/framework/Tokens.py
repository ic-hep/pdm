#!/usr/bin/env python
""" A module for handling client tokens. """

import os
from itsdangerous import URLSafeSerializer, BadData, BadSignature

class TokenService(object):
    """ This class issues and verifies client tokens using a given key.
    """

    def __init__(self, key=None, salt=None):
        """ Creates a token service using the given
            secret key and salt.
            If key it not specified, it will be randomly generated.
            Salt should be an application specific name.
        """
        if not salt:
            salt = 'pdmtokenservice'
        self.__salt = salt
        self.set_key(key)

    def set_key(self, key=None):
        """ Sets the key of this service.
            If key it not specified, it will be randomly generated.
            Returns None.
        """
        if not key:
            self.__key = os.urandom(32)
        else:
            self.__key = key
        self.__signer = URLSafeSerializer(self.__key, salt=self.__salt)

    def issue(self, value):
        """ Issues a token with the given value.
            Value can be any json serialisable object.
            Returns a token string.
        """
        return self.__signer.dumps(value)

    def check(self, token):
        """ Checks a token has a valid signature.
            Returns the token value.
            If the token is not valid, a ValueError will be raised.
        """
        try:
            res = self.__signer.loads(token)
            return res
        except BadData:
            raise ValueError("Token is invalid")

    @staticmethod
    def unpack(token):
        """ Unpacks a token without verification.
            Should only be used for fields which provide their own integrity.
            (Such as other tokens).
            Returns: The token object.
            Raises ValueError if the token cannot be unpacked.
        """
        unpacker = URLSafeSerializer("BadKey", None)
        _, res = unpacker.loads_unsafe(token)
        if not res:
            raise ValueError("Corrupt/empty token")
        return res
