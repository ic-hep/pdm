"""Lock file utilities."""
import os
import sys
import fcntl
import logging


LOGGER = logging.getLogger(__name__)


class AlreadyLockedError(IOError):
    """Lockfile already locked error."""

    def __init__(self, *args, **kwargs):
        """Initialise."""
        super(AlreadyLockedError, self).__init__(*args, **kwargs)


class PIDLockFile(object):
    """
    Open a lockfile.

    Opens a file and try to acquire a filesystem lock on said file.
    If successful write the current processes pid into the file. If
    unsuccessful will exit program.
    """

    def __init__(self, filename, lock_fail_log=True):
        """
        Initialise.

        Args:
            filename (str): Lockfile path.
            lock_fail_log (bool): Whether to log failures to obtain
                                  the file lock. (default: True)
        """
        self._filename = filename
        self._pidfile = None
        self._lock_fail_log = lock_fail_log

    @property
    def name(self):
        """Return the name of the lockfile."""
        return self._filename

    @property
    def fileno(self):
        """Return the open lockfiles file descriptor."""
        return self._pidfile.fileno()

    def update_pid(self):
        """
        Update the pid written into the lockfile.

        This is usefull for daemon setup where a new
        process is forked twice.
        """
        self._pidfile.seek(0)
        self._pidfile.truncate()
        self._pidfile.write(str(os.getpid()))
        self._pidfile.flush()
        os.fsync(self._pidfile.fileno())

    def __enter__(self):
        """Enter context."""
        try:
            self._pidfile = open(self._filename, 'a+b')
        except IOError:
            LOGGER.exception("Error opening pidfile %s", self._filename)
            raise

        try:
            fcntl.flock(self._pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as err:
            self._pidfile.seek(0)
            pid = self._pidfile.read()
            self.__exit__(*sys.exc_info())
            # Don't want to log to daemon logger (probably file) that a second
            # attempt to start the daemon didn't work.
            if err.errno == 11:
                if self._lock_fail_log:
                    LOGGER.error("pidfile already locked by process with pid: %s", pid)
                raise AlreadyLockedError("pidfile already locked by process with pid: %s" % pid)
            if self._lock_fail_log:
                LOGGER.exception("Error trying to acquire lock on pidfile %s", self._filename)
            raise

        self.update_pid()
        return self

    def __exit__(self, type_, value, traceback_):
        """Exit context."""
        self._pidfile.close()
        return False
