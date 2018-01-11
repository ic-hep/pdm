"""Lock file utilities."""
import os
import sys
import fcntl
import logging


class PIDLockFile(object):
    """
    Open a lockfile.

    Opens a file and try to acquire a filesystem lock on said file.
    If successful write the current processes pid into the file. If
    unsuccessful will exit program.
    """

    def __init__(self, filename):
        """Initialise."""
        self._filename = filename
        self._pidfile = None

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
        self._pidfile = open(self._filename, 'a+b')
        try:
            fcntl.flock(self._pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as err:
            if err.errno != 11:
                logging.error("Error trying to acquire lock: %s", err.message)
                raise
            self._pidfile.seek(0)
            sys.stderr.write("pidfile already locked by process with pid: %s\n" %
                             self._pidfile.read())
            sys.exit(0)
        self.update_pid()
        return self

    def __exit__(self, type_, value, traceback_):
        """Exit context."""
        self._pidfile.close()
        return False
