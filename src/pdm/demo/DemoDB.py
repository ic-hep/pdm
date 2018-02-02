#!/usr/bin/env python
""" Demo DB Model.
"""

from sqlalchemy import Column, Integer, String
from pdm.framework.Database import JSONMixin

#pylint: disable=too-few-public-methods
class DBModel(object):
    """ Turtle Demo DB Model. """

    def __init__(self, db_base):
        """ Declare Turtle tables against db_base. """

        #pylint: disable=unused-variable
        class Turtle(db_base, JSONMixin):
            """ Main Turtle DB table/object. """
            __tablename__ = "turtles"
            #pylint: disable=invalid-name
            id = Column(Integer, primary_key=True)
            name = Column(String(32))
