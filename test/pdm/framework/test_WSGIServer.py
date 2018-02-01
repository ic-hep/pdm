#!/usr/bin/env python
""" Tests for the WSGIServer module. """

import mock
import unittest

from pdm.framework.WSGIServer import WSGIAuth, WSGIServer

class TestWSGIAuth(unittest.TestCase):
    """ Test WSGIAuth class. """

    def setUp(self):
        """ Setup a basic WSGIAuth object with a fake request. """
        self.__auth = WSGIAuth(None, None, None)
        # Pre-build a fake request as we'll need it for most tests
        self.__headers = mock.MagicMock()
        self.__transport = mock.MagicMock()
        self.__request = mock.MagicMock()
        self.__request.requestHeaders = self.__headers
        self.__request.transport = self.__transport

    @mock.patch("twisted.web.wsgi.WSGIResource.render")
    def test_remove_headers(self, _):
        """ Check that the auth module removes any pre-existing SSL auth
            headers so that clients can't just spoof them.
        """
        self.__auth.render(self.__request)
        for bad_hdr in ("SSL_CLIENT_S_DN", "SSL_CLIENT_I_DN",
                        "SSL_CLIENT_VERIFY"):
            self.__headers.removeHeader.assert_any_call(bad_hdr)

    @mock.patch("twisted.web.wsgi.WSGIResource.render")
    def test_non_ssl(self, _):
        """ Mock a connection with client cert and check the headers are set
            correctly. This applies to both non-SSL and SSL-without-cert.
        """
        self.__transport.getPeerCertificate.return_value = None
        self.__auth.render(self.__request)
        self.__headers.addRawHeader.assert_called_with('SSL_CLIENT_VERIFY',
                                                       'NONE')

    @mock.patch("twisted.web.wsgi.WSGIResource.render")
    def test_ssl_client(self, _):
        """ Mock an SSL connection with a client cert and check headers.
        """
        from M2Crypto.X509 import X509_Name
        subject = X509_Name()
        subject.C = "UK"
        subject.ST = "Greater London"
        subject.L = "London"
        subject.O = "Test Org"
        subject.OU = "Security"
        subject.CN = "Test User"
        subject.Email = "test@user.test"
        issuer = X509_Name()
        issuer.C = "ZZ"
        issuer.CN = "Test CA"
        # Configure fake cert object
        cert = mock.MagicMock()
        cert.get_subject.return_value = subject
        cert.get_issuer.return_value = issuer
        self.__transport.getPeerCertificate.return_value = cert
        # Now run the test
        self.__auth.render(self.__request)
        addRawHeader = self.__headers.addRawHeader
        addRawHeader.assert_any_call('SSL_CLIENT_VERIFY', 'SUCCESS')
        addRawHeader.assert_any_call('SSL_CLIENT_S_DN', subject.as_text())
        addRawHeader.assert_any_call('SSL_CLIENT_I_DN', issuer.as_text())
        # One last check... DN with only email and no CN is a special case
        subject = X509_Name()
        subject.Email = "test2@user.test"
        cert.get_subject.return_value = subject
        addRawHeader.reset_mock()
        self.__auth.render(self.__request)
        addRawHeader.assert_any_call('SSL_CLIENT_S_DN', subject.as_text())

class TestWSGIServer(unittest.TestCase):
    """ Test the WSGIServer class. """

    def setUp(self):
        self.__server = WSGIServer()

    @mock.patch("pdm.framework.WSGIServer.reactor")
    def test_add_nonssl_server(self, mock_reactor):
        """ Check that creating a non-SSL app server works. """
        TEST_PORT = 123
        app_server = mock.Mock()
        self.__server.add_server(TEST_PORT, app_server, None, None, None)
        self.assertTrue(mock_reactor.listenTCP.called)
        self.assertFalse(mock_reactor.listenSSL.called)
        port, site = mock_reactor.listenTCP.call_args[0]
        self.assertEqual(port, TEST_PORT)
        self.assertEqual(site.resource._application, app_server)

    @mock.patch("__builtin__.open")
    @mock.patch("pdm.framework.WSGIServer.ssl")
    @mock.patch("pdm.framework.WSGIServer.reactor")
    def test_add_ssl_server(self, mock_reactor, mock_ssl, mock_open):
        """ Check that creating an SSL app server works. """
        TEST_PORT = 321
        CACERT = "/path/to/CA.crt"
        HOSTCERT = "/path/to/hostcert.pem"
        HOSTKEY = "/path/to/hostkey.pem"
        app_server = mock.Mock()
        # Run test with full CA set-up
        self.__server.add_server(TEST_PORT, app_server,
                                 HOSTCERT, HOSTKEY, CACERT)
        self.assertTrue(mock_reactor.listenSSL.called)
        self.assertFalse(mock_reactor.listenTCP.called)
        port, site, ssl_opts = mock_reactor.listenSSL.call_args[0]
        self.assertEqual(port, TEST_PORT)
        self.assertEqual(site.resource._application, app_server)
        self.assertFalse(ssl_opts.requireCertificate)
        self.assertTrue(mock_ssl.PrivateCertificate.loadPEM.called)
        self.assertTrue(mock_ssl.Certificate.loadPEM.called)
        # Run test without CA cert
        mock_reactor.reset_mock()
        mock_ssl.reset_mock()
        self.__server.add_server(TEST_PORT, app_server,
                                 HOSTCERT, HOSTKEY, None)
        port, site, ssl_opts = mock_reactor.listenSSL.call_args[0]
        self.assertTrue(mock_ssl.PrivateCertificate.loadPEM.called)
        self.assertFalse(mock_ssl.Certificate.loadPEM.called)
        # Run test where user & key are in same file
        mock_reactor.reset_mock()
        mock_open.reset_mock()
        mock_ssl.reset_mock()
        self.__server.add_server(TEST_PORT, app_server,
                                 HOSTCERT, HOSTCERT, None)
        port, site, ssl_opts = mock_reactor.listenSSL.call_args[0]
        self.assertTrue(mock_ssl.PrivateCertificate.loadPEM.called)
        self.assertEqual(mock_open.call_count, 1)
        # Check that client_req = True works correctly
        mock_reactor.reset_mock()
        mock_ssl.reset_mock()
        self.__server.add_server(TEST_PORT, app_server,
                                 HOSTCERT, HOSTKEY, CACERT,
                                 client_req=True)
        port, site, ssl_opts = mock_reactor.listenSSL.call_args[0]
        self.assertTrue(ssl_opts.requireCertificate)

    @mock.patch("pdm.framework.WSGIServer.reactor")
    def test_run(self, mock_reactor):
        """ Check that run starts the reactor. """
        self.__server.run()
        self.assertTrue(mock_reactor.run.called)
