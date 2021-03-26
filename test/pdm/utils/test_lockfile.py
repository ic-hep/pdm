#!/usr/bin/env python
""" Test of utils lockfile module. """

import os
import fcntl
import unittest
import unittest.mock as mock

from pdm.utils.lockfile import PIDLockFile, AlreadyLockedError

class TestPIDLockFile(unittest.TestCase):
    """ Test the PIDLockFile class. """

    @mock.patch("logging.getLogger")
    @mock.patch("os.fsync")
    @mock.patch("fcntl.flock")
    @mock.patch("builtins.open")
    def test_locking(self, open_fcn, flock_fcn,
                     fsync_fcn, logging_fcn):
        """ Check that the locking works as expected. """
        # Mock file access calls
        TEST_FILENAME = '/my/test/file'
        file_handle = mock.Mock()
        file_handle.fileno.return_value = 123
        file_handle.read.return_value = "321"
        open_fcn.return_value = file_handle
        # Try a plain lock with no contention
        pid_lock = PIDLockFile(TEST_FILENAME)
        self.assertEqual(pid_lock.name, TEST_FILENAME)
        with pid_lock:
            # The file should now be "locked"
            self.assertEqual(pid_lock.fileno, 123)
            open_fcn.assert_called_with(TEST_FILENAME, "a+")
            flock_fcn.assert_called_with(123, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertFalse(file_handle.close.called)
        self.assertTrue(file_handle.close.called)
        # Check correct PID was written to file
        cur_pid = str(os.getpid())
        file_handle.write.assert_called_with(cur_pid)
        # Now try the same again, but trigger an IOError on opening the file
        open_fcn.side_effect = IOError("Directory doesn't exist")
        self.assertRaises(IOError, pid_lock.__enter__)
        open_fcn.side_effect = None
        # Same again, but file already locked
        flock_fcn.side_effect = IOError("Locking Error")
        flock_fcn.side_effect.errno = 11
        self.assertRaises(AlreadyLockedError, pid_lock.__enter__)
        # Same again, but different error code
        flock_fcn.side_effect = IOError("Locking Error")
        flock_fcn.side_effect.errno = 13 # Permission Denied
        self.assertRaises(IOError, pid_lock.__enter__)
