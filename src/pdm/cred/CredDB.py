#!/usr/bin/env python
""" Credential service database. """

from sqlalchemy import Column, Integer, TEXT, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship

class CredDBModel(object):
    """ Credential database model container. """

    def __init__(self, db_base):
        """ Define credential database tables. """

        class CAEntry(db_base):
            __tablename__ = 'castore'
            cred_id = Column(Integer, primary_key=True)
            pub_cert = Column(TEXT, nullable=False)
            priv_key = Column(TEXT, nullable=False)
            serial = Column(Integer, nullable=False)

        class UserCred(db_base):
            __tablename__ = 'usercreds'
            cred_id = Column(Integer, primary_key=True)
            user_id = Column(Integer, nullable=False)
            cred_type = Column(Integer, nullable=False)
            expiry_date = Column(TIMESTAMP, nullable=False)
            cred_pub = Column(TEXT, nullable=False)
            cred_priv = Column(TEXT, nullable=False)
            sub_creds = relationship("JobCred",
                                     cascade="all,delete",
                                     backref="base_cred")

        class JobCred(db_base):
            __tablename__ = 'jobcreds'
            cred_id = Column(Integer, primary_key=True)
            base_id = Column(Integer, ForeignKey(UserCred.cred_id),
                             nullable=False)
            expiry_date = Column(TIMESTAMP, nullable=False)
            cred_pub = Column(TEXT, nullable=False)
            cred_priv = Column(TEXT, nullable=False)
