#!/usr/bin/env python
""" Endpoint service database. """

from sqlalchemy import Column, Integer, TEXT, ForeignKey
from sqlalchemy.orm import relationship
from pdm.framework.Database import JSONMixin

#pylint: disable=too-few-public-methods
class EndpointDBModel(object):
    """ Endpoint database model container. """

    def __init__(self, db_base):
        """ Define endpoint database tables. """

        #pylint: disable=too-few-public-methods, unused-variable
        class Site(db_base, JSONMixin):
            """ Sites table. """
            __tablename__ = 'sites'
            site_id = Column(Integer, primary_key=True)
            site_name = Column(TEXT, nullable=False, unique=True)
            site_desc = Column(TEXT, nullable=False)
            endpoints = relationship("Endpoint", cascade="delete")
            users = relationship("UserMap", cascade="delete")

        #pylint: disable=too-few-public-methods, unused-variable
        class Endpoint(db_base):
            """ Endpoint (at sites) table. """
            __tablename__ = 'endpoints'
            ep_id = Column(Integer, primary_key=True)
            site_id = Column(Integer, ForeignKey(Site.site_id),
                             nullable=False)
            ep_uri = Column(TEXT, nullable=False)

        #pylint: disable=too-few-public-methods, unused-variable
        class UserMap(db_base):
            """ User mapping table. """
            __tablename__ = 'mappings'
            user_id = Column(Integer, primary_key=True)
            site_id = Column(Integer, ForeignKey(Site.site_id),
                             primary_key=True)
            username = Column(TEXT, nullable=False)
