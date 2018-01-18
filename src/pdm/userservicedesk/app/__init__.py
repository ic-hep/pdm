__author__ = 'martynia'

from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()

def create_app(config):

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    #global db
    #db = SQLAlchemy(app)
    db.init_app(app)
    # the next line is essential. Otherwise db will be pointing to a null db engine
    app.app_context().push()  # http://piotr.banaszkiewicz.org/blog/2012/06/29/flask-sqlalchemy-init_app/ (Erik Bray)
    return app

def foo():
    pass