#!/usr/bin/env python
""" A module for handling client tokens. """

import os
from itsdangerous import URLSafeSerializer

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
        Returns a tuple of (error, value)
        error is a string describing the problem or None if everything
        was fine. Value is the token value, if error == None.
    """
    try:
      res = self.__signer.loads(token)
      return (None, res)
    except:
      # TODO: More specific catch here
      return ("Token Error", None)
