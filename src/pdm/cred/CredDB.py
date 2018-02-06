#!/usr/bin/env python
""" Credential service database. """

from sqlalchemy import Column, Integer, TEXT, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship

#pylint: disable=too-few-public-methods
class CredDBModel(object):
    """ Credential database model container. """

    def __init__(self, db_base):
        """ Define credential database tables. """

        #pylint: disable=too-few-public-methods, unused-variable
        class CAEntry(db_base):
            """ CA details table. """
            __tablename__ = 'castore'
            cred_id = Column(Integer, primary_key=True)
            pub_cert = Column(TEXT, nullable=False)
            priv_key = Column(TEXT, nullable=False)
            serial = Column(Integer, nullable=False)

        #pylint: disable=too-few-public-methods, unused-variable
        class UserCred(db_base):
            """ User credentials table. """
            __tablename__ = 'usercreds'
            cred_id = Column(Integer, primary_key=True)
            user_id = Column(Integer, nullable=False)
            cred_type = Column(Integer, nullable=False)
            expiry_date = Column(TIMESTAMP, nullable=False)
            cred_pub = Column(TEXT, nullable=False)
            cred_priv = Column(TEXT, nullable=False)
            sub_creds = relationship("JobCred", cascade="delete")

        #pylint: disable=too-few-public-methods, unused-variable
        class JobCred(db_base):
            """ Job credentials table. """
            __tablename__ = 'jobcreds'
            cred_id = Column(Integer, primary_key=True)
            base_id = Column(Integer, ForeignKey(UserCred.cred_id),
                             nullable=False)
            cred_type = Column(Integer, nullable=False)
            expiry_date = Column(TIMESTAMP, nullable=False)
            cred_pub = Column(TEXT, nullable=False)
            cred_priv = Column(TEXT, nullable=False)
