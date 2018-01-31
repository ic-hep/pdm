#!/usr/bin/env python
""" Main user credential service.
"""

import random
from flask import current_app, request
from pdm.framework.FlaskWrapper import (db_model, export, export_ext, startup,
                                        jsonify)
from pdm.cred.CredDB import CredDBModel
from pdm.utils.X509 import X509CA, X509Utils

@export_ext('/cred/api/v1.0')
@db_model(CredDBModel)
class CredService(object):

    # Unique key for the user CA cert in the DB
    USER_CA_INDEX = 1

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
    @export_ext("ca")
    def get_ca():
        """ Get the CA certificate that is used to issue user creds.
        """
        db = request.db
        CAEntry = db.tables.CAEntry
        ca_info = CAEntry.query.filter_by(cred_id=CredService.USER_CA_INDEX) \
                               .first_or_404()
        res = {'ca': ca_info.pub_cert}
        return jsonify(res)

    @staticmethod
    @export_ext("user", ["POST"])
    def add_user():
        # Decode POST data
        user_id = 0
        user_key = "weakUserpass"
        # Generate a new DN for the user
        random_num = random.randint(1000000000, 9999999999)
        user_dn = "%s, CN=User_%u %u" % (current_app._user_base_dn,
                                         user_id, random_num)
        # Create a new X509 cert for the user
        # Create a new SSH key for the user
        pass

    @staticmethod
    @export_ext("user/<int:user_id>", ["DELETE"])
    def del_user(user_id):
        pass

    @staticmethod
    @export_ext("user/<int:user_id>")
    def get_user(user_id):
        pass

    @staticmethod
    @export_ext("cred", ["POST"])
    def add_cred():
        pass

    @staticmethod
    @export_ext("cred/<string:token>", ["DELETE"])
    def del_cred(token):
        pass

    @staticmethod
    @export_ext("cred/<string:token>")
    def get_cred():
        pass
