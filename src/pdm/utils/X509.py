#!/usr/bin/env python
""" X509 CA: Modules for issuing certificates.
"""

import os
import random
import hashlib
import tempfile
from distutils import dir_util
#pylint: disable=no-member
from M2Crypto import m2
from M2Crypto import ASN1, X509
from OpenSSL import crypto


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
            "readable" spacing...
        """
        raw_dn = x509_name.as_text(flags=m2.XN_FLAG_ONELINE)
        # Renormalise the spacing to remove spaces around the equals.
        return X509Utils.normalise_dn(raw_dn)

    @staticmethod
    def normalise_dn(dn_str):
        """ Converts a DN from any standard format (RFC2253, OpenSSL) with any
            spacing into plain RFC2253 format with "readable" spacing.
            Returns a string.
        """
        dn_input = dn_str.strip()
        if dn_input.startswith('/'):
            # Input is OpenSSL
            return X509Utils.convert_dn(dn_input, '/', ', ', False)
        else:
            # Input is RFC2253 with unknown spacing
            return X509Utils.convert_dn(dn_input, ',', ', ', False)

    @staticmethod
    def get_cert_expiry(cert_pem):
        """ Gets the expiry date of a given X.509 public certificate
            in PEM format.
            cert_pem - Input cert PEM string.
            Returns a datetime object of the expiry time.
        """
        cert = X509.load_cert_string(cert_pem, X509.FORMAT_PEM)
        return cert.get_not_after().get_datetime()

    @staticmethod
    def write_policy(ca_pem, target_file):
        """ Writes a signing policy for CA described by ca_pem
            into the file with filename target_file.

            The policy file will allow any issued certs to be in
            /OU=Users or /OU=Hosts.

            Returns None.
        """
        if isinstance(ca_pem, unicode):
            ca_pem = ca_pem.encode('ascii','ignore')
        cert = X509.load_cert_string(ca_pem, X509.FORMAT_PEM)
        ca_raw_dn = X509Utils.x509name_to_str(cert.get_subject())
        ca_dn = X509Utils.rfc_to_openssl(ca_raw_dn)
        policy_text = "access_id_CA   X509    '%s'\n" % ca_dn
        policy_text += "pos_rights     globus  CA:sign\n"
        policy_text += "cond_subjects  globus  '\"/OU=Users/*\" \"/OU=Hosts/*\"'\n"
        with open(target_file, "w") as pol_fd:
            pol_fd.write(policy_text)

    @staticmethod
    def add_ca_to_dir(ca_list, dir_path=None, template_dir=None):
        """ Adds a CA list to OpenSSL style hash dir.

            ca_list - A list of strings, each one a PEM encoded CA certificate
                      to be written to the directory.
            dir_path - The directory to write the files to. If not specified a
                       temporary directory will be created.
                       Note: The caller must delete the directory when they are
                             finished with it to prevent cluttering up /tmp.
            template_dir - Template directory path (str) to use as the initial
                           contents of the CA dir if we create it. If dir_path
                           is not none, then this option is ignored.
                           Set to None (default) to disable this feature.
            Returns the directory path to the CA dir.
        """
        ca_path = dir_path
        if not ca_path:
            ca_path = tempfile.mkdtemp(prefix='tmpca')
            if template_dir:
                dir_util.copy_tree(template_dir, ca_path,
                                   preserve_symlinks=True)
        for ca_pem in ca_list:
            # Get the OpenSSL hash of the PEM file
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_pem)
            cert_hash = "%08x" % cert.subject_name_hash()
            # Normally we would have to support writing .n files where
            # .n gets larger if earlier numbers already exist.
            # But the signing_policy files don't support that, so instead
            # we'll only support .0 and throw an exception otherwise.
            cert_name = "%s.0" % cert_hash
            cert_path = os.path.join(ca_path, cert_name)
            sigpol_name = "%s.signing_policy" % cert_hash
            sigpol_path = os.path.join(ca_path, sigpol_name)
            if os.path.exists(cert_path):
                raise Exception("A cert '%s' already exists in dir." % \
                                cert_hash)
            elif os.path.exists(sigpol_path):
                raise Exception("A policy '%s' already exists in dir." % \
                                cert_hash)

            with open(cert_path, "w") as cert_fd:
                cert_fd.write(ca_pem)
            X509Utils.write_policy(ca_pem, sigpol_path)
        return ca_path
