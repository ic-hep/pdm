#!/usr/bin/env python
""" Main user credential service.
"""

import json
import random
from flask import current_app, request
from pdm.framework.FlaskWrapper import db_model, export_ext, startup, jsonify
from pdm.framework.Tokens import TokenService
from pdm.cred.CredDB import CredDBModel
from pdm.utils.X509 import X509CA, X509Utils
from pdm.utils.sshkey import SSHKeyUtils

@export_ext('/cred/api/v1.0')
@db_model(CredDBModel)
class CredService(object):
    """ Credential management service. """

    # Unique key for the user CA cert in the DB
    USER_CA_INDEX = 1
    CRED_TYPE_X509 = 0
    CRED_TYPE_SSH = 1

    @staticmethod
    @startup
    def configure_ca(config):
        """ Configure a new CA if one doesn't already exist in the DB.
        """
        log = current_app.log
        db = current_app.db
        CAEntry = db.tables.CAEntry
        # Load config parameters
        log.info("Processing config parameters.")
        # Start with required parameters
        current_app.ca_config = {}
        req_params = ('ca_dn', 'ca_key', 'user_dn_base', 'user_cred_secret')
        for conf_key in req_params:
            if not conf_key in config:
                raise RuntimeError("%s parameter missing from config file." \
                                       % conf_key)
            current_app.ca_config[conf_key] = config.pop(conf_key)
        # TODO: Normalise DNs into RFC format here!
        # Then do optional parameters with defaults
        current_app.ca_config['ca_days'] = config.pop('ca_days', 3650)
        current_app.ca_config['user_max_days'] = \
            config.pop('user_max_days', 365)
        current_app.ca_config['proxy_max_hours'] = \
            config.pop('proxy_max_hours', 12)

        # Create a token service for issuing the user cred tokens
        token_key = current_app.ca_config['user_cred_secret']
        current_app.ca_token_svc = TokenService(token_key, 'CATokenSalt')

        log.info("Looking for existing user CA...")
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX)\
                               .first()
        if ca_info:
            log.info("User CA already exists in DB.")
            # Try to load CA to check key is correct
            ca_key = current_app.ca_config['ca_key']
            ca_obj = X509CA()
            try:
                ca_obj.set_ca(str(ca_info.pub_cert), str(ca_info.priv_key),
                              ca_info.serial, ca_key)
            except:
                log.error('Failed to load CA cert from DB, check that ca_key'
                          ' is correct.')
                raise RuntimeError('Failed to load CA cert from DB')
            # Check DN matches config
            ca_dn = current_app.ca_config['ca_dn']
            stored_dn = ca_obj.get_dn()
            if stored_dn != ca_dn:
                log.warning("Stored user CA DN ('%s') doesn't match "
                            "config DN ('%s')", stored_dn, ca_dn)
            return

        # Generate a new CA certificate
        log.info("No user CA found, generating new CA...")
        ca_obj = X509CA()
        ca_dn = current_app.ca_config['ca_dn']
        ca_days = current_app.ca_config['ca_days']
        ca_key = current_app.ca_config['ca_key']
        log.info("  CA Subject: %s", ca_dn)
        log.info("  CA Lifetime (days): %u", ca_days)
        ca_obj.gen_ca(ca_dn, ca_days)
        new_ca = CAEntry(cred_id=CredService.USER_CA_INDEX,
                         pub_cert=ca_obj.get_cert(),
                         priv_key=ca_obj.get_key(ca_key),
                         serial=ca_obj.get_serial())
        db.session.add(new_ca)
        db.session.commit()
        log.info("User CA generated and stored in DB successfully.")

    @staticmethod
    def __load_ca():
        """ A helper function to get a pre-configured CA object from the
            database. Note: This opens the database row with update locking.
            Returns a tuple of (ca_obj, ca_entry) or types (X509CA, CAEntry).
        """
        db = request.db
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.with_for_update() \
                               .filter_by(cred_id=CredService.USER_CA_INDEX) \
                               .first_or_404()
        ca_obj = X509CA()
        ca_obj.set_ca(str(ca_info.pub_cert),
                      str(ca_info.priv_key),
                      ca_info.serial,
                      current_app.ca_config['ca_key'])
        return (ca_obj, ca_info)

    @staticmethod
    def __delegate_cred(base_cred, base_key=None, limited=True):
        """ A helper function to generate a new derrived credential from an
            existing cred. Lifetime will be set to proxy_max_hours if
            applicable (ssh-keys have no real lifetime).
            base_cred - A UserCred or JobCred DB object to delegate from.
            cred_key - The passphrase for the base credential key (or None)
            limited - Whether to generate a limited credential if possible.
            Returns a tuple of (public_key, private_key, expiry)
            public_key & private_key are the new cred keys as strings.
            expiry is the expiry date of the new credential.
        """
        if base_cred.cred_type == CredService.CRED_TYPE_SSH:
            # There isn't much we can do for SSH delegation,
            # we just return the base keys
            return (base_cred.cred_pub,
                    base_cred.cred_priv,
                    base_cred.expiry_date)
        if base_cred.cred_type != CredService.CRED_TYPE_X509:
            raise RuntimeError("Unknown credential type %u!" % \
                                   base_cred.cred_type)
        # We have to do X509 proxy delegation here
        valid_hours = current_app.ca_config['proxy_max_hours']
        proxy_cert, proxy_key = X509CA.gen_proxy(base_cred.cred_pub,
                                                 base_cred.cred_priv,
                                                 valid_hours,
                                                 base_key,
                                                 limited)
        # Get real proxy expiry
        expiry = X509Utils.get_cert_expiry(proxy_cert)
        return (proxy_cert, proxy_key, expiry)

    @staticmethod
    @export_ext("ca")
    def get_ca():
        """ Get the CA certificate that is used to issue user creds.
        """
        db = request.db
        ca_cert = None
        try:
            ca_obj, _ = CredService.__load_ca()
            ca_cert = ca_obj.get_cert()
        finally:
            db.session.rollback() # Close the lock on the CA table
        if not ca_cert:
            request.log.error("Failed to open CA cert in get_ca.")
            return "Internal Error", 500
        res = {'ca': ca_cert}
        return jsonify(res)

    @staticmethod
    @export_ext("user", ["POST"])
    def add_user():
        db = request.db
        UserCred = db.tables.UserCred
        # Decode POST data
        try:
            if not request.data:
                raise ValueError("Missing POST data")
            user_data = json.loads(request.data)
            user_id = int(user_data["user_id"])
            user_key = str(user_data["user_key"])
            user_email = user_data.pop("user_email", None)
            if user_email:
                # It may be unicode, convert to string
                user_email = str(user_email)
        except ValueError, KeyError:
            return "Malformed POST data", 500
        # Generate a new DN for the user
        random_num = random.randint(1000000000, 9999999999)
        user_dn = "%s, CN=User_%u %u" % (current_app.ca_config['user_dn_base'],
                                         user_id, random_num)
        # Create a new X509 cert for the user
        ca_obj, ca_entry = CredService.__load_ca()
        cert_life = current_app.ca_config['user_max_days']
        cert_pub, cert_priv = ca_obj.gen_cert(user_dn,
                                              cert_life,
                                              email=user_email,
                                              passphrase=user_key)
        ca_entry.serial = ca_obj.get_serial()
        db.session.commit() # Store the CA serial back in the DB
        cert_expiry = X509Utils.get_cert_expiry(cert_pub)
        ca_cred = UserCred(user_id=user_id,
                           cred_type=CredService.CRED_TYPE_X509,
                           expiry_date=cert_expiry,
                           cred_pub=cert_pub,
                           cred_priv=cert_priv)
        # Create a new SSH key for the user
        ssh_pub, ssh_priv = SSHKeyUtils.gen_rsa_keypair(user_key)
        # SSH keys don't exipre... We'll use the same time as the
        # cert so they both need renewing together.
        ssh_cred = UserCred(user_id=user_id,
                            cred_type=CredService.CRED_TYPE_SSH,
                            expiry_date=cert_expiry,
                            cred_pub=ssh_pub,
                            cred_priv=ssh_priv)
        # Finally add the new entries to the DB
        db.session.add(ca_cred)
        db.session.add(ssh_cred)
        db.session.commit()
        # Success, return an empty 200
        return ""

    @staticmethod
    @export_ext("user/<int:user_id>", ["DELETE"])
    def del_user(user_id):
        db = request.db
        UserCred = db.tables.UserCred
        # This will cascade delete on the JobCred table
        UserCred.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    @staticmethod
    @export_ext("user/<int:user_id>")
    def get_user(user_id):
        db = request.db
        UserCred = db.tables.UserCred
        newest_cred = UserCred.query.filter_by(user_id=user_id) \
                                    .order_by(UserCred.expires.desc()) \
                                    .first_or_404()
        ret = {'valid_until': newest_cred.expires}
        return jsonify(res)

    @staticmethod
    @export_ext("cred", ["POST"])
    def add_cred():
        try:
            # Decode the POST data
            if not request.data:
                raise ValueError("Missing POST data")
            user_data = json.loads(request.data)
            user_id = int(user_data["user_id"])
            user_key = user_data["user_key"]
            cred_type = user_data["cred_type"]
            max_lifetime = int(user_data["max_lifetime"])
            # Cap max_lifetime to within config
            max_lifetime = min(max_lifetime,
                               current_app.ca_config['proxy_max_hours'])
        except ValueError, KeyError:
            return "Malformed POST data", 500
        # Now prepare the DB
        db = request.db
        UserCred = db.tables.UserCred
        JobCred = db.tables.JobCred
        # We have to get the user's newest credential of the type specified.
        base_cred = UserCred.query.filter_by(user_id=user_id,
                                             cred_type=cred_type) \
                                  .order_by(UserCred.expires.desc()) \
                                  .first_or_404()
        # Create new credentials
        new_details = CredService.__delegate_cred(base_cred,
                                                  base_key=user_key,
                                                  limited=False)
        new_pub, new_priv, expiry = new_details
        new_cred = JobCred(base_id=base_cred.cred_id,
                           expiry_date=expiry,
                           cred_pub=new_pub,
                           cred_priv=new_prev)
        db.session.add(new_cred)
        db.session.commit()
        # Generate the token for retrieving this credential
        token = current_app.ca_token_svc.issue(new_cred.cred_id)
        return token

    @staticmethod
    @export_ext("cred/<string:token>", ["DELETE"])
    def del_cred(token):
        try:
            cred_id = current_app.ca_token_svc.check(token)
        except ValueError:
            return "Invalid token", 403
        db = request.db
        JobCred = db.tables.JobCred
        JobCred.query.filter_by(cred_id=cred_id).delete()
        db.session.commit()
        return ""

    @staticmethod
    @export_ext("cred/<string:token>")
    def get_cred():
        try:
            cred_id = current_app.ca_token_svc.check(token)
        except ValueError:
            return "Invalid token", 403
        db = request.db
        JobCred = db.tables.JobCred
        base_cred = JobCred.query.filter_by(cred_id=cred_id).first_or_404()
        # Delegate a new credential from the job credential
        new_pub, new_priv, _ = CredService.__delegate_cred(base_cred,
                                                           base_key=None,
                                                           limited=True)
        res = {'cred_type': base_cred.cred_type,
               'pub_key': new_pub,
               'priv_key': new_priv}
        return jsonify(res)
