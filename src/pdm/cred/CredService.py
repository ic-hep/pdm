#!/usr/bin/env python
""" Main user credential service.
"""

import json
import random
from flask import current_app, request
from pdm.framework.FlaskWrapper import (db_model, export, export_ext, startup,
                                        jsonify)
from pdm.cred.CredDB import CredDBModel
from pdm.utils.X509 import X509CA, X509Utils
from pdm.utils.sshkey import SSHKeyUtils

@export_ext('/cred/api/v1.0')
@db_model(CredDBModel)
class CredService(object):

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
        ca_num = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX)\
                              .count()
        if ca_num:
            # CA already exists, so no need to create it
            return
        # Generate a new CA certificate
        # TODO: Use user specified parameters
        log.info("Generating new user CA...")
        ca_obj = X509CA()
        ca_name = "/C=XX/OU=Test CA"
        ca_days = 3650
        ca_key = "weakCApass"
        log.info("  CA Subject: %s", ca_name)
        log.info("  CA Lifetime (days): %u", ca_days)
        ca_obj.gen_ca(ca_name, 3650)
        new_ca = CAEntry(cred_id=CredService.USER_CA_INDEX,
                         pub_cert=ca_obj.get_cert(),
                         priv_key=ca_obj.get_key(),
                         serial=ca_obj.get_serial())
        db.session.add(new_ca)
        db.session.commit()
        log.info("CA generated and stored in DB successfully.")
        # TODO: Load any other parameters
        current_app._user_base_dn = "C=XX, OU=Test Users"
        current_app._user_lifetime = 365

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
                      ca_info.serial)
        return (ca_obj, ca_info)

    @staticmethod
    @export_ext("ca")
    def get_ca():
        """ Get the CA certificate that is used to issue user creds.
        """
        db = request.db
        ca_obj, _ = CredService.__load_ca()
        ca_cert = ca_obj.get_cert()
        db.session.rollback() # Close the lock on the CA table
        res = {'ca': ca_cert}
        return jsonify(res)

    @staticmethod
    @export_ext("user", ["POST"])
    def add_user():
        db = request.db
        UserCred = db.tables.UserCred
        # Decode POST data
        user_id = 0
        user_key = "weakUserpass"
        user_email = None
        # Generate a new DN for the user
        random_num = random.randint(1000000000, 9999999999)
        user_dn = "%s, CN=User_%u %u" % (current_app._user_base_dn,
                                         user_id, random_num)
        # Create a new X509 cert for the user
        ca_obj, ca_entry = CredService.__load_ca()
        cert_pub, cert_priv = ca_obj.gen_cert(user_dn,
                                              current_app._user_lifetime,
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
            # TODO: min(lifetime, config max)
            mex_lifetime = int(user_data["max_lifetime"])
        except ValueError, KeyError:
            return "Malformed POST data", 500
        # Now prepare the DB
        db = request.db
        UserCred = db.tables.UserCred
        JobCred = db.tables.JobCred
        # We have to get the user's newest credential of the type specified.
        newest_cred = UserCred.query.filter_by(user_id=user_id,
                                               cred_type=cred_type) \
                                    .order_by(UserCred.expires.desc()) \
                                    .first_or_404()
        # TODO: Create new credentials
        # TODO: Generate the token for retrieving this credential
        token = request.token_svc.issue(0)
        return token

    @staticmethod
    @export_ext("cred/<string:token>", ["DELETE"])
    def del_cred(token):
        try:
            cred_id = self.token_svc.check(token)
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
            cred_id = self.token_svc.check(token)
        except ValueError:
            return "Invalid token", 403
        db = request.db
        JobCred = db.tables.JobCred
        cred = JobCred.query.filter_by(cred_id=cred_id).first_or_404()
        # TODO: Delegate a new credential from the job credential here
        # Now delegate a new credential if possible
        res = {'cred_type': cred.cred_type,
               'pub_key': "",
               'priv_key': ""}
        return jsonify(res)
