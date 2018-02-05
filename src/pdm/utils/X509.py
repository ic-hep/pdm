#!/usr/bin/env python
""" X509 CA: Modules for issuing certificates.
"""

import random
#pylint: disable=no-member
from M2Crypto import m2
from M2Crypto import ASN1, EVP, RSA, X509


class X509Utils(object):
    """ A series of helper functions for X509 objects. """

    @staticmethod
    def convert_dn(input_dn, input_sep, output_sep, with_space):
        """ Converts a DN from one format to another.
            input_dn is the string to convert.
            input_sep & output_sep are the seperators to use between segs.
            with_space is a bool, True to include spaces around the = sign.
        """
        eq_val = "="
        if with_space:
            eq_val = " = "
        dn_parts = input_dn.split(input_sep)
        output_parts = []
        for dn_part in dn_parts:
            if not dn_part:
                continue # Empty segment
            field, value = dn_part.split("=", 1)
            field = field.strip()
            value = value.strip()
            output_parts.append("%s%s%s" % (field, eq_val, value))
        return output_sep.join(output_parts)

    @staticmethod
    def openssl_to_rfc(input_dn):
        """ This converts an OpenSSL style DN: /C=XX/L=YY/...
            to an RFC2253 style one: C = XX, L = YY, ...
            If the input doesn't start with / character (i.e. input
            is probably already RFC2253) then input is returned.
        """
        if not input_dn:
            raise ValueError("Empty DN provided to conversion function.")
        if input_dn[0] != '/':
            return input_dn
        return X509Utils.convert_dn(input_dn, '/', ', ', True)

    @staticmethod
    def rfc_to_openssl(input_dn):
        """ This convert an RFC style DN: C = XX, L = YY, ...
            to an OpenSSL style one: /C=XX/L=YY,...
            If the input already starts with a / then it is
            directly returned (as it's probably already in the
            correct format.
        """
        if not input_dn:
            raise ValueError("Empty DN provided to conversion function.")
        if input_dn[0] == '/':
            return input_dn
        output_dn = X509Utils.convert_dn(input_dn, ',', '/', False)
        # Output needs an extra '/' on the beginning
        return '/%s' % output_dn

    @staticmethod
    def str_to_x509name(dn_val):
        """ Converts a raw DN string into an X509_Name object.
            Input DN can be in OpenSSL or RFC2253 format.
        """
        real_dn = X509Utils.openssl_to_rfc(dn_val)
        new_name = X509.X509_Name()
        for dn_part in real_dn.split(","):
            field, value = dn_part.split("=", 1)
            field = field.strip()
            value = value.strip()
            new_name.add_entry_by_txt(field,
                                      ASN1.MBSTRING_ASC,
                                      value,
                                      -1, # Length, -1 = auto
                                      -1, # Position, -1 = end
                                      0)  # Set, 0 = Add new
        return new_name

    @staticmethod
    def x509name_to_str(x509_name):
        """ Converts an X509_Name object to a plain string.
            The output string will be in RFC2253 format with
            "readable" spacing..
        """
        return x509_name.as_text(flags=m2.XN_FLAG_ONELINE)


class X509CA(object):
    """ An X509 Certificate Authority implementation.
    """

    # Default parameters for cert generation
    PUB_EXPONENT = m2.RSA_F4 # == 65537
    KEY_SIZE = 2048
    SIG_ALGO = 'sha256'
    CERT_VER = 2
    # Encryption algorithm for private keys
    # (if passphrase specified)
    ENC_ALGO = 'aes_256_cbc'
    # Proxy extension constants
    ## DER encoded proxy cert info extension for unlimited proxy
    ## (unlimited path length with no restrictions)
    PROXY_UNLIMITED = 'DER:30:0C:30:0A:06:08:2B:06:01:05:05:07:15:01'
    ## DER encoded extension for limited proxy
    PROXY_LIMITED = 'DER:30:0F:30:0D:06:0B:2B:06:01:04:01:9B:50:01:01:01:09'
    # Allowed cert & proxy key use
    DEFAULT_KEY_USE = 'digitalSignature,keyEncipherment,dataEncipherment'

    @staticmethod
    def __gen_csr(req_dn):
        """ Generate a CSR for the given DN.
            Returns a tuple of (RSA, PKey, CSR)
            where RSA is an M2Crypto.RSA object containg the RSA key-pair.
            PKey is an EVP.PKey containing the keys.
            CSR is an M2Crypto.X509.Request object.
            Raises a RuntimeError if anything goes wrong.
            NOTE: Keep evp_key in scope while rsa_key is in scope otherwise
                  the interpreter may segfault in newer versions of python.
        """
        # First generate a key pair
        rsa_key = RSA.gen_key(X509CA.KEY_SIZE,
                              X509CA.PUB_EXPONENT,
                              callback=lambda: None)
        evp_key = EVP.PKey()
        evp_key.assign_rsa(rsa_key)
        # Create the request
        req = X509.Request()
        if not req.set_version(X509CA.CERT_VER):
            raise RuntimeError("Failed to set cert CSR version")
        if not req.set_subject_name(X509Utils.str_to_x509name(req_dn)):
            raise RuntimeError("Failed to set cert CSR subject")
        if not req.set_pubkey(evp_key):
            raise RuntimeError("Failed to set cert CSR pubkey")
        if not req.sign(evp_key, X509CA.SIG_ALGO):
            raise RuntimeError("Failed to sign cert CSR")
        return (rsa_key, evp_key, req)

    @staticmethod
    def __gen_basic_cert(req, valid_days, serial, issuer):
        """ Generate a cert template from a CSR.
            req - The M2Crypto.X509.Request object.
            valid_days - Lifetime of new cert in days (from now).
            serial - Serial of new certificate.
            issuer - CA's M2Crypto.X509.X509 object.
        """
        cert = X509.X509()
        if not cert.set_version(X509CA.CERT_VER):
            raise RuntimeError("Failed to set CA cert version")
        if not cert.set_serial_number(serial):
            raise RuntimeError("Failed to set CA cert serial")
        if not cert.set_subject(req.get_subject()):
            raise RuntimeError("Failed to set CA cert subject")
        if not cert.set_issuer(issuer.get_subject()):
            raise RuntimeError("Failed to set CA cert issuer")
        if not cert.set_pubkey(req.get_pubkey()):
            raise RuntimeError("Failed to set CA cert pubkey")
        not_before = m2.x509_get_not_before(cert.x509)
        m2.x509_gmtime_adj(not_before, 0)
        not_after = m2.x509_get_not_after(cert.x509)
        m2.x509_gmtime_adj(not_after, valid_days * 24 * 3600)
        return cert

    #pylint: disable=unused-argument
    @staticmethod
    def __add_basic_exts(cert, auth_pubkey, is_ca=False):
        """ Adds basic extensions to a cert.
            Specifially, basicConstraints, subjectKeyID and AuthKeyID.
            cert - X509.X509 object to add extensions to.
            auth_pubkey - EVP.PKey object to digest for the authKeyID field.
            is_ca - Used to set the CA basicConstraint, boolean. If set to
                    None then no CA contraint is included.
            Returns None, Raises RuntimeError on failure.
        """
        if is_ca is not None:
            bc_str = 'CA:FALSE'
            if is_ca:
                bc_str = 'CA:TRUE'
            ca_ext = X509.new_extension('basicConstraints', bc_str, 1)
            if not cert.add_ext(ca_ext):
                raise RuntimeError("Failed to add CA cert constraints ext")
        # TODO: Add subject/auth key ID fields, as well as keyUsage
        # TODO: Check results
        #cert.add_ext(X509.new_extension('subjectKeyIdentifier', 'hash'))
        #cert.add_ext(X509.new_extension('authorityKeyIdentifier', 'keyid'))
        cert.add_ext(X509.new_extension('keyUsage', X509CA.DEFAULT_KEY_USE))

    @staticmethod
    def __gen_ca(req, evp_key, valid_days, serial=1):
        """ Generate a CA cert by self-signing a CSR.
            Returns an X509.X509 object.
            Raises a RuntimeError if anything goes wrong.
        """
        cert = X509CA.__gen_basic_cert(req, valid_days, serial, req)
        # Add CA extensions
        X509CA.__add_basic_exts(cert, req, True)
        # Finally sign the cert
        if not cert.sign(evp_key, X509CA.SIG_ALGO):
            raise RuntimeError("Failed to sign CA cert")
        return cert

    #pylint: disable=too-many-arguments
    @staticmethod
    def __gen_cert(req, valid_days, serial, alt_names, issuer, sign_key):
        """ Generates a normal non-CA cert for and signs it with
            the given certificate.
            req - X509.Request object to base the cert on.
            valid_days - Lifetime of new cert in days.
            serial - Serial number of new cert.
            alt_names - Iterable of alternative names to attach in extensions.
            issuer - X509.X509 object for CA (Used to get issuer DN).
            sign_key - EVP.PKey object to sign cert with.
            Returns signed X509.X509 object.
        """
        cert = X509CA.__gen_basic_cert(req, valid_days, serial, issuer)
        X509CA.__add_basic_exts(cert, issuer, False)
        for alt_name in alt_names:
            an_ext = X509.new_extension('subjectAltName', alt_name, 0)
            if not cert.add_ext(an_ext):
                raise RuntimeError("Failed to add altName '%s'" % alt_name)
        if not cert.sign(sign_key, X509CA.SIG_ALGO):
            raise RuntimeError("Failed to sign normal cert")
        return cert

    def __init__(self):
        self.__cert = None
        self.__key = None
        self.__sign_key = None
        self.__serial = None

    def gen_ca(self, ca_name, valid_days, serial=None):
        """ Generate a new CA certificate + key.
            ca_name should be a DN string for the new CA
                    in RFC format (/C=XX/L=YY...).
            valid_days is the number of days the CA should
                       be valid for.
            serial is the starting serial number for the CA,
                   if unset, serial numbers start from 2 (CA is 1)
            Returns None.
        """
        self.clear()
        # Get the private key & request
        rsa_key, evp_key, req = self.__gen_csr(ca_name)
        # Now convert the request into a self-signed (CA) cert
        cert = self.__gen_ca(req, evp_key, valid_days)
        # Store the results as the active CA objects
        self.__cert = cert
        self.__key = rsa_key
        self.__sign_key = evp_key
        if serial is not None:
            if serial <= 1:
                raise ValueError("CA starting serial must be greater than 1.")
            self.__serial = serial
        else:
            self.__serial = 2

    def set_ca(self, cert_pem, key_pem, serial, passphrase=None):
        """ Set the current CA state from PEM strings.
            cert - the CA cert PEM string.
            key - the matching CA key PEM string.
            serial - the next serial number as an int.
            passphrase - Optional password to use to decrypt the private key.
            Returns None.
        """
        cert = X509.load_cert_string(cert_pem, X509.FORMAT_PEM)
        pw_cb = lambda x: ""
        if passphrase:
            pw_cb = lambda x: passphrase
        key = RSA.load_key_string(key_pem, callback=pw_cb)
        if serial <= 1:
            raise ValueError("CA serial must be larger than 1.")
        # Store the newly loaded objects
        self.__cert = cert
        self.__key = key
        self.__sign_key = EVP.PKey()
        self.__sign_key.assign_rsa(key)
        self.__serial = serial

    def clear(self):
        """ Clears the stored CA information. """
        self.__cert = None
        self.__key = None
        self.__sign_key = None
        self.__serial = None

    def ready(self):
        """ Returns True if the CA is properly initialised,
            False otherwise.
        """
        if self.__cert and self.__key and self.__sign_key and self.__serial:
            return True
        return False

    def __check_init(self):
        """ Throws a RuntimeError exception if the CA
            is not properly initialised.
        """
        if not self.ready():
            raise RuntimeError("CA not initialised")

    def get_cert(self):
        """ Returns the CA certificate in PEM format.
        """
        self.__check_init()
        return self.__cert.as_pem()

    def get_key(self, passphrase=None):
        """ Returns the CA key in PEM format.
            If passphrase is set to a string, the PEM file will be
            encrypted with the given password.
        """
        self.__check_init()
        if not passphrase:
            return self.__key.as_pem(cipher=None)
        pw_cb = lambda x: passphrase
        return self.__key.as_pem(cipher=self.ENC_ALGO, callback=pw_cb)

    def get_dn(self):
        """ Gets the DN of this CA in RFC format.
        """
        self.__check_init()
        return X509Utils.x509name_to_str(self.__cert.get_subject())

    def get_serial(self):
        """ Gets the current CA serial number as an int.
        """
        self.__check_init()
        return self.__serial

    def gen_cert(self, subject, valid_days, email=None, passphrase=None):
        """ Creates and signs a cert with the given details.
            subject - The target DN in RFC format.
            valid_days - Lifetime of new cert, from now, in days.
            email - Optional e-mail address to attach as an alt name.
            Returns PEM encoded public cert and private key tuple:
                    (cert, key).
        """
        self.__check_init()
        # Generate request
        # See note about evp_key in __gen_csr doc.
        #pylint: disable=unused-variable
        rsa_key, evp_key, req = self.__gen_csr(subject)
        # Convert request to cert
        alt_names = []
        if email:
            alt_names.append("email:%s" % email)
        new_serial = self.__serial
        cert = X509CA.__gen_cert(req, valid_days, new_serial,
                                 alt_names, self.__cert, self.__sign_key)
        # Finally convert output to PEM
        cert_pem = cert.as_pem()
        if passphrase:
            pw_cb = lambda x: passphrase
            key_pem = rsa_key.as_pem(cipher=self.ENC_ALGO, callback=pw_cb)
        else:
            key_pem = rsa_key.as_pem(cipher=None)
        # Everything successful, bump CA serial number
        self.__serial += 1
        return (cert_pem, key_pem)

    @staticmethod
    def __gen_proxy(usercert, sign_key, valid_days):
        """ Internal method for generating an RFC proxy.
            cert - X509.X509 object of user cert.
            sign_key - EVP.PKey object to sign the proxy with.
            Returns a (cert, evp_key, key) tuple of types (X509, EVP, RSA).
        """
        cert_dn = X509Utils.x509name_to_str(usercert.get_subject())
        proxy_serial = random.randint(1000000000, 9999999999)
        proxy_dn = "%s, CN = %u" % (cert_dn, proxy_serial)
        # Note: While it's unused, evp_key must stay in memory while
        #       rsa_key is valid otherwise it may cause a segfault.
        rsa_key, evp_key, req = X509CA.__gen_csr(proxy_dn)
        cert = X509CA.__gen_basic_cert(req, valid_days, proxy_serial, usercert)
        key_use_ext = X509.new_extension('keyUsage', X509CA.DEFAULT_KEY_USE)
        if not cert.add_ext(key_use_ext):
            raise RuntimeError("Failed to proxy key usage ext")
        proxy_ext = X509.new_extension('proxyCertInfo',
                                       X509CA.PROXY_UNLIMITED, 1)
        if not cert.add_ext(proxy_ext):
            raise RuntimeError("Failed to add proxy info ext")
        if not cert.sign(sign_key, X509CA.SIG_ALGO):
            raise RuntimeError("Failed to sign proxy cert")
        return (cert, evp_key, rsa_key)

    @staticmethod
    def gen_proxy(cert_pem, key_pem, valid_days, passphrase=None):
        """ Generates an RFC3820 proxy for the supplied user cert.
            cert_pem & key_pem - User cery & key PEM files.
            valid_days - How long the proxy should be valid for.
            passphrase - Passphrase to use for encrypted user key.
            Returns a tuple of PEM strings (proxycert, proxykey)
            proxykey is unencrypted.
        """
        user_cert = X509.load_cert_string(cert_pem)
        pw_cb = lambda x: None
        if passphrase:
            pw_cb = lambda x: passphrase
        user_key = RSA.load_key_string(key_pem, callback=pw_cb)
        sign_key = EVP.PKey()
        sign_key.assign_rsa(user_key)
        #pylint: disable=unused-variable
        proxy_cert, evp_key, proxy_key = X509CA.__gen_proxy(user_cert,
                                                            sign_key,
                                                            valid_days)
        proxy_cert_pem = proxy_cert.as_pem()
        proxy_key_pem = proxy_key.as_pem(cipher=None)
        return (proxy_cert_pem, proxy_key_pem)
