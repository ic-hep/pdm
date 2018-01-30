#!/usr/bin/env python
""" Main user credential service.
"""

from flask import current_app, request
from pdm.framework.FlaskWrapper import db_model, export, export_ext, startup
from pdm.cred.CredDB import CredDBModel

@export_ext('/creds/api/v1.0')
@db_model(CredDBModel)
class CredService(object):

    @staticmethod
    @startup
    def configure_ca(config):
        pass

    @staticmethod
    @export
    def get_ca():
        pass

    @staticmethod
    @export
    def add_user():
        pass

    @staticmethod
    @export
    def get_user():
        pass

    @staticmethod
    @export
    def renew_user():
        pass

    @staticmethod
    def add_job():
        pass

    @staticmethod
    @export
    def get_job():
        pass

    @staticmethod
    @export
    def del_job():
        pass
