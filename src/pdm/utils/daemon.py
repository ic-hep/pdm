"""Daemon Utility Module."""
import sys
import atexit
import signal
import resource
import logging
import os
from os.path import abspath, realpath, expanduser, expandvars

from .lockfile import PIDLockFile, AlreadyLockedError


class Daemon(object):
    """
    Daemon Base.

    This daemon base class is designed to work on LINUX systems only.
    The design borrows heavily from Chad J. Schroeder's recipe:
    http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way
    as well as taking guidance from PEP 3143 and inspiration from daemonize:
    https://github.com/thesharp/daemonize

    Example:
    >>> import logging
    >>> from pdm.utils import Daemon
    >>>
    >>> def my_func(a):
    >>>     logging.getLogger('my_func').info("In daemon: %s", a)
    >>>
    >>> Daemon(pidfile='daemon.pid', target=my_func, args=('Hello World',)).start()
    """

    def __init__(self, pidfile, target, args=None, kwargs=None, **options):
        """
        Initialise Daemon.

        Args:
            pidfile (str): Path to the pid lockfile.
            target (function): Python function for the daemon to run.
            args (tuple): Positional args for the target function (default: None).
            kwargs (dict): Keyword args for the target function (default: None).

        Options:
            debug (bool): Run in debug/foreground mode (no forks). (default: False)
            logname (str): Name of the logger to use. (default: __class__.__name__)
            loglevel (int): Level to log to. (default: logging.INFO)
            logfile (str): Path to the logging outputfile.
                           (default: $PWD/__class__.__name__.log)
            logconfig (str): Path to the logging configuration file. Note this
                             option will override logfile and loglevel as it is
                             assumed that the configuration file will correctly
                             setup the logger with name logname.
            extra_fds (Iterable): Any file descriptors that should not be closed
                                  when spawning the daemon. Note that the fds for
                                  the pidfile and the handler associated with the
                                  logger with name logname OR the root logger are
                                  added automatically.
        """
        self._pidfilename = abspath(realpath(expanduser(expandvars(pidfile))))
        if not pidfile.startswith(os.sep):
            self._pidfilename = os.path.join(os.getcwd(), pidfile)
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._debug = options.get('debug', False)
        self._extra_fds = set(options.get('extra_fds', ()))
        logname = options.get('logname', self.__class__.__name__)
        logconfig = options.get('logconfig')
        loglevel = options.get('loglevel', logging.INFO)
        logfile = options.get('logfile',
                              os.path.join(os.getcwd(), "%s.log" % self.__class__.__name__))
        if not self._debug:
            if logconfig is not None:
                logging.config.fileConfig(logconfig)
            else:
                logging.basicConfig(filename=logfile,
                                    level=loglevel,
                                    format="[%(asctime)s] %(name)15s : %(levelname)8s : "
                                    "%(message)s")
        else:
            logging.basicConfig(stream=sys.stderr,
                                level=loglevel,
                                format="[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s")
        self._logger = logging.getLogger(logname)
        self._extra_fds.update(handler.stream.fileno() for handler in
                               (self._logger.handlers or logging.getLogger().handlers))

    @property
    def pid(self):
        """Get the pid of the running daemon."""
        with open(self._pidfilename, 'r') as pidfile:
            return pidfile.read()

    def exit(self):
        """Called on daemon exit."""
        self._logger.info("Daemon shutting down...")

    def terminate(self, *_):
        """Called on receiving SIGTERM."""
        self._logger.warning("Daemon received SIGTERM.")

    #pylint: disable=too-many-branches, too-many-statements
    def start(self):
        """Start daemon process."""
        try:
            with PIDLockFile(self._pidfilename, lock_fail_log=False) as pidfile:
                if not self._debug:
                    try:
                        # Run in the background.
                        pid = os.fork()
                    except OSError:
                        self._logger.exception("Error forking for the first time.")
                        # From the recipe there appears to be no reason why
                        # this first parent must exit immediately. Returning here and
                        # if pid==0 allows any python code after daemon.start() to
                        # execute normally in the parent.
                        return
                        # os._exit(1)
                    if pid != 0:
                        return
                        # os._exit(0)

                    # Disassociate from control terminal.
                    # Disassociate from process group.
                    os.setsid()
                    try:
                        # Don't reacquire a control terminal.
                        pid = os.fork()
                    except OSError:
                        self._logger.exception("Error forking for the second time.")
                        #pylint: disable=protected-access
                        os._exit(1)
                    if pid != 0:
                        #pylint: disable=protected-access
                        os._exit(0)

                    # Change current working directory.
                    # (don't want to find something unmounted underneath us)
                    os.chdir('/')
                    # Reset the file access creation mask.
                    os.umask(0o27)

                    # Get max open file descriptors.
                    try:
                        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
                    except ValueError:
                        self._logger.exception("Invalid resource 'resource.RLIMIT_NOFILE' "
                                               "specified.")
                    except resource.error:
                        self._logger.exception("Underlying system call for getrlimit failed.")

                    if maxfd == resource.RLIM_INFINITY:
                        maxfd = 1024

                    # Close all open file descriptors.
                    for filed in range(maxfd):
                        if filed not in self._extra_fds | {pidfile.fileno}:
                            try:
                                os.close(filed)
                            except OSError:
                                pass

                    # Ignore terminal I/O signals.
                    os.open(os.devnull, os.O_RDONLY)
                    if 1 in self._extra_fds:
                        os.open(os.devnull, os.O_RDWR)
                    if 2 in self._extra_fds:
                        os.open(os.devnull, os.O_RDWR)
                    pidfile.update_pid()

                atexit.register(logging.shutdown)
                atexit.register(self.exit)
                signal.signal(signal.SIGTERM, self.terminate)

                self._logger.info("Daemon target starting...")
                try:
                    self._target(*self._args, **self._kwargs)
                except Exception:
                    self._logger.exception("Daemon runtime error in target.")

                if not self._debug:
                    sys.exit(0)

        except AlreadyLockedError as err:
            sys.stderr.write(str(err))
            sys.stderr.write('\n')
