#!/usr/bin/env python
""" Utilities for hashing things. """

import os
import hashlib
import binascii

# Hashing constants
HASH_SALT_LEN = 16
HASH_ALGO = 'sha256'
HASH_ITER = 10000

def hash_pass(password):
    """ A helper function to convert a password to a hash.
        password - Input password string to hash.
        Returns a string of the hashed password.
        Note: The hashes are salted and are therefore different
              every time. Use check_hash to check an existing hash
              against a password.
    """
    salt = os.urandom(HASH_SALT_LEN)
    hashed_pass = hashlib.pbkdf2_hmac(HASH_ALGO, password,
                                      salt, HASH_ITER)
    hash_str = "$5$%s$%s" % (binascii.hexlify(salt),
                             binascii.hexlify(hashed_pass))
    return hash_str

def check_hash(hash_in, password):
    """ Checks a password against a hashed version to see if they
        match.
        hash_in - A salted password hash (such as that from hash_pass)
        password - A password string in to compare.
        Returns True is the password matches the hash.
    """
    hash_parts = hash_in.split("$")
    if len(hash_parts) != 4:
        raise ValueError("Invalid hash, not enough $ parts")
    if hash_parts[1] != "5":
        raise ValueError("Unreconised hash type")
    try:
        salt = binascii.unhexlify(hash_parts[2])
        stored_hash = binascii.unhexlify(hash_parts[3])
    except TypeError:
        raise ValueError("Malfomed base64 in hash input")
    new_hash = hashlib.pbkdf2_hmac(HASH_ALGO, password,
                                   salt, HASH_ITER)
    return new_hash == stored_hash
