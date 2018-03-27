""" Database model for User service. """

from  pdm.utils.db import managed_session
from pdm.framework.Database import JSONMixin
from sqlalchemy import Column, Integer, String, DateTime, func


# pylint: disable=too-few-public-methods
class UserModel(object):
    """ User service tables. """

    def __init__(self, db_base):
        """ Create user tables. """

        class User(db_base, JSONMixin):
            """ Main user table. """
            __tablename__ = "user"
            __excluded_fields__ = ('id', 'password')
            id = Column(Integer, primary_key=True, autoincrement=True)
            # username = Column(String(80), unique=True, nullable=False)
            name = Column(String(80), unique=False, nullable=False)
            surname = Column(String(80), unique=False, nullable=False)
            state = Column(Integer, default=0)
            # dn = db.Column(db.String(200), unique=True, nullable=False)
            password = Column(String(80), unique=False, nullable=False)
            email = Column(String(120), unique=True, nullable=False)
            last_login = Column(DateTime, default=None)
            date_created = Column(DateTime, default=func.current_timestamp())
            date_modified = Column(
                DateTime, default=func.current_timestamp(),
                onupdate=func.current_timestamp())

            @staticmethod
            def get_all():
                """ Get all defined users. """
                # pylint: disable=no-member
                return User.query.all()

            def save(self, db):
                """ Save this object to the DB. """
                with managed_session(db) as m_session:
                    m_session.add(self)

            def delete(self, db):
                """ Delete this object from DB. """
                with managed_session(db) as m_session:
                    m_session.delete(self)

            def __repr__(self):
                return '<User %r>' % self.email

            def __str__(self):
                return 'User: %s, surname: %s, name: %s' % (self.email, self.surname, self.name)
