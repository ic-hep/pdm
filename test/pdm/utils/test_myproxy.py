#!/usr/bin/env python

import os
import mock
import unittest

from pdm.utils.myproxy import MyProxyUtils


class TestMyProxyUtils(unittest.TestCase):
    """ Test the MyProxyUtils module. """

    @staticmethod
    def get_args(popen_mock):
        """ A helper function to get the effective
            command line from a Popen call.
            Returns a tuple of args, env
        """
        cmd_args = " ".join(popen_mock.call_args[0][0])
        return cmd_args, popen_mock.call_args[1]['env']

    @mock.patch("pdm.utils.myproxy.X509Utils")
    @mock.patch("pdm.utils.myproxy.Popen")
    def test_myproxy_logon(self, popen_mock, x509_mock):
        """ Test that the logon function works as expected.
        """
        x509_mock.add_ca_to_dir.return_value = "/tmp/cadir"
        # Set-up a fake Popen object
        proc = mock.MagicMock()
        proc.communicate.return_value = ('PEMFILE', '')
        proc.returncode = 0
        popen_mock.return_value = proc
        # Simplest test
        res = MyProxyUtils.logon("localhost:12345", "user", "pass")
        self.assertEqual(res, 'PEMFILE')
        self.assertEqual(proc.communicate.call_args[0][0], 'pass\n')
        args, _ = self.get_args(popen_mock)
        self.assertIn('-s localhost', args)
        self.assertIn('-p 12345', args)
        self.assertIn('-l user', args)
        # Test X509 CADir string works correctly
        res = MyProxyUtils.logon("localhost:12345", "user", "pass",
                                 ca_certs="/opt/etc/certs")
        _, env = self.get_args(popen_mock)
        self.assertEqual(env['X509_CERT_DIR'], "/opt/etc/certs")
        # Now try a more advanced test
        log = mock.MagicMock()
        res = MyProxyUtils.logon("localhost:12345", "user", "pass",
                                 ca_certs=['A', 'B'], voms="dteam",
                                 hours=123, myproxy_bin="/opt/myproxy-logon",
                                 vomses="/opt/etc/vomses", log=log)
        args, env = self.get_args(popen_mock)
        self.assertTrue(args.startswith('/opt/myproxy-logon'))
        self.assertIn('-t 123', args)
        self.assertIn('-m dteam', args)
        self.assertEqual(env['X509_CERT_DIR'], "/tmp/cadir")
        self.assertEqual(env['X509_VOMS_DIR'], "/opt/etc/vomses")
        self.assertTrue(log.debug.called)

    def assertRaisesMsg(self, msgPart, func, *args, **kwargs):
        """ Helper function to check error messages look correct.
            Like assertRaises, but checks msgPart is in the exception msg. """
        try:
            func(*args, **kwargs)
            self.assertFail() # Should have raised an exception
        except Exception as err:
            self.assertIn(msgPart, str(err))

    @mock.patch("pdm.utils.myproxy.Popen")
    def test_myproxy_logon_errors(self, popen_mock):
        """ Check the error case handling for myproxy logon. """
        ARGS = ["localhost:12345", "user", "pass"]
        proc = mock.MagicMock()
        proc.communicate.return_value = ('', '')
        proc.returncode = 1
        popen_mock.return_value = proc
        # Simple, wrong error code
        log = mock.MagicMock()
        self.assertRaisesMsg('Unknown', MyProxyUtils.logon, *ARGS, log=log)
        self.assertTrue(log.warn.called)
        # Various user/system errors
        proc.communicate.return_value = ('', 'invalid password')
        self.assertRaisesMsg('Incorrect password', MyProxyUtils.logon, *ARGS)
        proc.communicate.return_value = ('', 'Unable to connect to localhost')
        self.assertRaisesMsg('Connection error', MyProxyUtils.logon, *ARGS)
        proc.communicate.return_value = ('', 'No credentials exist for username user')
        self.assertRaisesMsg('Unrecognised user', MyProxyUtils.logon, *ARGS)
        proc.communicate.return_value = ('', 'Error in service module')
        self.assertRaisesMsg('Unrecognised user', MyProxyUtils.logon, *ARGS)
        # Hard system error (such as myproxy-logon not found)
        proc.communicate.side_effect = IOError("Failed to read myproxy-logon")
        self.assertRaisesMsg('Failed to run', MyProxyUtils.logon, *ARGS, log=log)

    @staticmethod
    def voms_open_fcn(fname, mode):
        """ Helper function for test_load_voms_list.
        """
        assert(fname.startswith("/mydir"))
        voname = os.path.basename(fname)
        file_fd = mock.MagicMock()
        file_fd.readline.return_value = '"%s" "..."' % voname
        open_obj = mock.MagicMock()
        open_obj.__enter__.return_value = file_fd
        if voname == 'badfile':
            file_fd.readline.side_effect = IOError("Failed to read file")
        return open_obj

    @mock.patch("pdm.utils.myproxy.open", create=True)
    @mock.patch("pdm.utils.myproxy.os")
    def test_load_voms_list(self, os_mock, open_mock):
        """ Check that the load_voms_list function works as expected.
            Specficially it returns a sorted list of VOs ignorning
            bad files.
        """
        os_mock.listdir.return_value = ["vo2.test.vo", "vo1", "badfile"]
        os_mock.path.join.side_effect = os.path.join
        open_mock.side_effect = self.voms_open_fcn
        res = MyProxyUtils.load_voms_list("/mydir")
        self.assertIsInstance(res, list)
        self.assertItemsEqual(res, ["vo1", "vo2.test.vo"])
        self.assertTrue(sorted(res))
