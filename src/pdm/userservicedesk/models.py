
from  pdm.utils.db import managed_session
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, func
from pdm.framework.Database import JSONMixin

class UserModel(object):

    def __init__(self, db_base):

        class User(db_base, JSONMixin):
            __tablename__ = "user"
            id = Column(Integer, primary_key=True, autoincrement=True)
            #username = Column(String(80), unique=True, nullable=False)
            name = Column(String(80), unique=False, nullable=False)
            surname = Column(String(80), unique=False, nullable=False)
            state = Column(Integer)
            #dn = db.Column(db.String(200), unique=True, nullable=False)
            password = Column(String(80), unique=False, nullable=False)
            email = Column(String(120), unique=True, nullable=False)
            last_login = Column(DateTime, default=None)
            date_created = Column(DateTime, default=func.current_timestamp())
            date_modified = Column(
                DateTime, default=func.current_timestamp(),
                onupdate=func.current_timestamp())


            @staticmethod
            def get_all():
                return User.query.all()

            def save(self, db):

                with managed_session(db) as m_session:
                    m_session.add(self)

            def delete(self, db):
                with managed_session(db) as m_session:
                    m_session.delete(self)

            def __repr__(self):
                return '<User %r>' % self.email

            def __str__(self):
                return 'User: %s, surname: %s, name: %s' % (self.email, self.surname, self.name)
