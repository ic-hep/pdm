"""Database Utility Module."""
import logging
from contextlib import contextmanager

from flask import abort


@contextmanager
def managed_session(request,
                    message="Error in database session... rolling back!",
                    logger=logging.getLogger(__name__),
                    http_error_code=None):
    """Managed database session context."""
    try:
        yield request.db.session
        request.db.session.commit()
    except Exception:  # pylint: disable=broad-except
        request.db.session.rollback()
        if logger is not None:
            logger.exception(message)
        if http_error_code is None:
            raise
        abort(http_error_code)
