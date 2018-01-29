#!/usr/bin/env python
""" X509 CA: Modules for issuing certificates.
"""

from M2Crypto import m2, ASN1, EVP, RSA, X509


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
          if not len(dn_part):
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
        if not len(input_dn):
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
        if not len(input_dn):
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

    def __init__(self):
        self.__cert = None
        self.__key = None
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
        # Generate an RSA key-pair
        # We add an empty callback so we don't get text on stdout
        priv_key = RSA.gen_key(self.KEY_SIZE,
                               self.PUB_EXPONENT,
                               callback=lambda: None)
        pub_key = EVP.PKey()
        pub_key.assign_rsa(priv_key)
        # Create the initial request
        req = X509.Request()
        if not req.set_version(self.CERT_VER):
            raise RuntimeError("Failed to set CA CSR version")
        if not req.set_subject_name(X509Utils.str_to_x509name(ca_name)):
            raise RuntimeError("Failed to set CA CSR subject")
        if not req.set_pubkey(pub_key):
            raise RuntimeError("Failed to set CA CSR pubkey")
        if not req.sign(pub_key, self.SIG_ALGO):
            raise RuntimeError("Failed to sign CA CSR")
        # Now convert the request into a self-signed (CA) cert
        cert = X509.X509()
        if not cert.set_version(self.CERT_VER):
            raise RuntimeError("Failed to set CA cert version")
        if not cert.set_serial_number(1):
            raise RuntimeError("Failed to set CA cert serial")
        if not cert.set_subject(req.get_subject()):
            raise RuntimeError("Failed to set CA cert subject")
        if not cert.set_issuer(req.get_subject()):
            raise RuntimeError("Failed to set CA cert issuer")
        if not cert.set_pubkey(req.get_pubkey()):
            raise RuntimeError("Failed to set CA cert pubkey")
        not_before = m2.x509_get_not_before(cert.x509)
        m2.x509_gmtime_adj(not_before, 0)
        not_after = m2.x509_get_not_after(cert.x509)
        m2.x509_gmtime_adj(not_after, valid_days * 24 * 3600)
        # Add CA extensions
        ca_ext = X509.new_extension('basicConstraints', 'CA:TRUE', 1)
        if not cert.add_ext(ca_ext):
            raise RuntimeError("Failed to add CA cert constraints ext")
        # TODO: Add subject/auth key ID fields
        #cert.add_ext(X509.new_extension('subjectKeyIdentifier', 'abcd'))
        #cert.add_ext(X509.new_extension('AuthorityKeyIdentifier', 'abcd'))
        # Finally sign the cert
        if not cert.sign(pub_key, self.SIG_ALGO):
            raise RuntimeError("Failed to sign CA cert")
        # Store the results as the active CA objects
        self.__cert = cert
        self.__key = priv_key
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
        self.__serial = serial

    def clear(self):
        """ Clears the stored CA information. """
        self.__cert = None
        self.__key = None
        self.__serial = None

    def ready(self):
        """ Returns True if the CA is properly initialised,
            False otherwise.
        """
        if self.__cert and self.__key and self.__serial:
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

