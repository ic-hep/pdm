__author__ = 'martynia'

from  pdm.userservicedesk.app import foo
from  pdm.userservicedesk.app import db
from  pdm.utils.db import managed_session

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pdm.framework.Database import JSONMixin

class UserModel(object):

    def __init__(self, db_base):

        class User(db_base, JSONMixin):
            __tablename__ = "user"
            id = db.Column(db.Integer, primary_key=True, autoincrement=True)
            username = db.Column(db.String(80), unique=True, nullable=False)
            name = db.Column(db.String(80), unique=False, nullable=False)
            surname = db.Column(db.String(80), unique=False, nullable=False)
            state = db.Column(db.Integer)
            #dn = db.Column(db.String(200), unique=True, nullable=False)
            password = db.Column(db.String(80), unique=False, nullable=False)
            email = db.Column(db.String(120), unique=True, nullable=False)
            date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
            date_modified = db.Column(
                db.DateTime, default=db.func.current_timestamp(),
                onupdate=db.func.current_timestamp())


            @staticmethod
            def get_all():
                return User.query.all()

            def save(self):
                with managed_session(db) as m_session:
                    m_session.add(self)

                    #db.session.add(self)
                    #db.session.commit()

            def delete(self):
                with managed_session(db) as m_session:
                    m_session.delete(self)
                    #db.session.delete(self)
                    #db.session.commit()

            def __repr__(self):
                return '<User %r>' % self.username

            def __str__(self):
                return 'User: %s, surname: %s, name: %s, email: %s ' % (self.username, self.surname, self.name, self.email)
