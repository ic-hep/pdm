__author__ = 'martynia'

from  pdm.userservicedesk.app import foo
from  pdm.userservicedesk.app import db

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

#app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
#db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), unique=False, nullable=False)
    surname = db.Column(db.String(80), unique=False, nullable=False)
    state = db.Column(db.Integer)
    dn = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(
        db.DateTime, default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp())



    #def __init__(self, username, name, surname, dn, password, email, state = 1):
    #    """initialize with user data."""
    #    self.name = name
    #    self.username = username

    @staticmethod
    def get_all():
        return User.query.all()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return '<User %r>' % self.username