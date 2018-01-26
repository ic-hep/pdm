"""Database Utility Module."""
import logging
from contextlib import contextmanager


@contextmanager
def managed_session(db):
    """Managed database session context."""
    try:
        yield db.session
        db.session.commit()
    except Exception:  # pylint: disable=broad-except
        logging.getLogger('managed_session')\
               .exception("Error in database session... rolling back!")
        db.session.rollback()
        raise
