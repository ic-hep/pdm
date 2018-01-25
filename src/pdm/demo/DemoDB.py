#!/usr/bin/env python
""" Demo DB Model.
"""

from sqlalchemy import Column, Integer, String
from pdm.framework.Database import JSONMixin

class DBModel(object):

  def __init__(self, db_base):

    class Turtle(db_base, JSONMixin):
      __tablename__ = "turtles"
      id = Column(Integer, primary_key=True)
      name = Column(String(32))

