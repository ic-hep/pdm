__author__ = 'martynia'

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from pdm.utils.config import ConfigSystem

db = SQLAlchemy()
cs = ConfigSystem.get_instance()

def create_app(configname):

# configuration:
    from instance.config import app_config
    cs.setup(app_config[configname])
# app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = cs.get_section('database').get('SQLALCHEMY_DATABASE_URI', 'sqlite:////tmp/test.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    #global db
    #db = SQLAlchemy(app)
    db.init_app(app)
    # the next line is essential. Otherwise db will be pointing to a null db engine
    app.app_context().push()  # http://piotr.banaszkiewicz.org/blog/2012/06/29/flask-sqlalchemy-init_app/ (Erik Bray)
    return app

def foo():
    pass