"""Database Utility Module."""
import logging
from contextlib import contextmanager

from flask import abort


@contextmanager
def managed_session(request,
                    message="Error in database session",
                    logger=logging.getLogger(__name__),
                    http_error_code=None):
    """ Managed database session context.
        request - A flask request object containing a db attribute.
        message - The message to log if an error occurs, also returned
                  to the user if abort is called.
        logger - If not None, log the message to this logger.
        http_error_code - If set, a Flask abort exception is raised
                 with this code & the provided message.
        If http_error_code is unset, the internal exception is re-raised.
    """
    try:
        yield request.db.session
        request.db.session.commit()
    except Exception:
        request.db.session.rollback()
        if logger is not None:
            logger.exception(message)
        if http_error_code is None:
            raise
        abort(http_error_code, description=message)
