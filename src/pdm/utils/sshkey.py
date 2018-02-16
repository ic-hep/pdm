#!/usr/bin/env python
""" Tools for handling SSH keys. """

import base64
import struct
from M2Crypto import RSA

#pylint: disable=too-few-public-methods
class SSHKeyUtils(object):
    """ Utilities for working with SSH keys. """

    DEF_NUM_BITS = 2048
    DEF_EXPONENT = 5 # OpenSSH generally uses 5 as the exponent
    DEF_ENC_ALGO = 'aes_256_cbc'

    @staticmethod
    def __rsapub_to_ssh(key_in):
        """ This function takes an RSA object, extracts the public key
            and converts it to the SSH PEM encoded format (without the
            trimmings like type and comment).
            Returns a PEM string.
        """
        # It would be nice if a library did this, while some are available
        # they are all overkill for a relatively simple conversion
        algo = 'ssh-rsa'
        algo_hdr = struct.pack('>I', len(algo)) + algo
        exponent, modulus = key_in.pub()
        # exponent and modulus already have the length encoded
        buf = algo_hdr + exponent + modulus
        return base64.b64encode(buf)

    @staticmethod
    def gen_rsa_keypair(passphrase=None, comment="", bits=DEF_NUM_BITS):
        """ Generates a new SSH key-pair, encrypted with the
            given passphrase.
            If passphrase is None then the output is unencrypted.
            Returns a tuple of two strings: (pub, key)
                    pub is an ssh-rsa encoded public string.
                        (RFC4253 encoded)
                    key is a PEM encoded private key.
            Returns (pub, key)
        """
        # Generate a plain RSA key
        key = RSA.gen_key(bits, SSHKeyUtils.DEF_EXPONENT,
                          callback=lambda: None)
        # Convert the public part of the key
        pub_str = "ssh-rsa %s %s" % (SSHKeyUtils.__rsapub_to_ssh(key),
                                     comment)
        # and then the private part of the key
        if not passphrase:
            key_pem = key.as_pem(cipher=None)
        else:
            pw_cb = lambda x: passphrase
            key_pem = key.as_pem(cipher=SSHKeyUtils.DEF_ENC_ALGO,
                                 callback=pw_cb)
        return (pub_str, key_pem)

    @staticmethod
    def remove_pass(key_in, passphrase=None):
        """ Removes the password from an SSH key.
            key_in - The PEM encoded input key.
            passphrase - The password of the input key.
            Returns PEM encoded key with no password.
        """
        pw_cb = lambda x: passphrase
        key = RSA.load_key_string(key_in, callback=pw_cb)
        return key.as_pem(cipher=None)
