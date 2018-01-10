"""Lock file utilities."""
import os
import fcntl
from contextlib import contextmanager

@contextmanager
def pidlockfile(filename):
    """"""
    with open(filename, 'r+b') as pidfile:
        fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        pidfile.write(str(os.getpid()))
        pidfile.flush()
        os.fsync(pidfile.fileno())
        yield
