#!/usr/bin/env python
""" Credential service database. """

from sqlalchemy import Column, Integer, TEXT, TIMESTAMP

    class Turtle(db_base, JSONMixin):
      __tablename__ = "turtles"
      id = Column(Integer, primary_key=True)
      name = Column(String(32))

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

        class JobCred(db_base):
            __tablename__ = 'jobcreds'
            cred_id = Column(Integer, primary_key=True)
            user_id = Column(Integer, nullable=False)
            base_id = Column(Integer, nullable=False)
            expiry_date = Column(TIMESTAMP, nullable=False)
            cred_pub = Column(TEXT, nullable=False)
            cred_priv = Column(TEXT, nullable=False)
