#!/usr/bin/env python
""" Site service database. """

from sqlalchemy import Column, Boolean, Integer, TEXT, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from pdm.framework.Database import JSONMixin, DictMixin

#pylint: disable=too-few-public-methods
class SiteDBModel(object):
    """ Site database model container. """

    def __init__(self, db_base):
        """ Define site database tables. """

        #pylint: disable=too-few-public-methods, unused-variable
        class Site(db_base, JSONMixin, DictMixin):
            """ Sites table. """
            __tablename__ = 'sites'
            __excluded_fields__ = ["site_owner", "endpoints", "creds"]
            site_id = Column(Integer, primary_key=True)
            site_name = Column(TEXT, nullable=False, unique=True)
            site_desc = Column(TEXT, nullable=False)
            site_owner = Column(Integer, nullable=False)
            user_ca_cert = Column(TEXT, nullable=True)
            service_ca_cert = Column(TEXT, nullable=True)
            auth_type = Column(Integer, nullable=False)
            auth_uri = Column(TEXT, nullable=False)
            public = Column(Boolean, nullable=False)
            def_path = Column(TEXT, nullable=False)

        #pylint: disable=too-few-public-methods, unused-variable
        class Endpoint(db_base, JSONMixin):
            """ Data (gridftp) endpoints table. """
            __tablename__ = 'endpoints'
            ep_id = Column(Integer, primary_key=True)
            site_id = Column(Integer, ForeignKey(Site.site_id),
                             nullable=False)
            ep_uri = Column(TEXT, nullable=False)

        #pylint: disable=too-few-public-methods, unused-variable
        class Cred(db_base):
            """ A user credential cache table. """
            __tablename__ = 'creds'
            cred_owner = Column(Integer, primary_key=True)
            site_id = Column(Integer, ForeignKey(Site.site_id),
                             primary_key=True)
            cred_username = Column(TEXT, nullable=False)
            cred_expiry = Column(TIMESTAMP, nullable=False)
            cred_value = Column(TEXT, nullable=False)

        Site.endpoints = relationship(Endpoint, cascade="delete")
        # Mainly for cascading deletion
        Site.creds = relationship(Cred, cascade="delete")
