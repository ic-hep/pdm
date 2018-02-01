#!/usr/bin/env python
""" Standalone WSGI server modules for debugging.
"""

import os

from twisted.web import server, wsgi
from twisted.internet import reactor, ssl

class WSGIAuth(wsgi.WSGIResource):
    """ This class implements a wrapper around the twisted WSGI module to
        implement SSL client certificates based authentication.

        It injects the client DN details into the following HTTP headers
        in the request:
          SSL_CLIENT_S_DN
          SSL_CLIENT_I_DN
          SSL_CLIENT_VERIFY

        The headers follow the Apache format for SSL headers, specifically the
        _DN fields contain the client subject & issuer DNs in OpenSSL format;
        the _VERIFY field contains one of:
          NONE - No client certificate was presented.
          SUCCESS - Client certificate was presented and validated against CA.
          (GENEROUS - Client presented a certificate: Unused)
          FAILED(:reason) - Client certificate problem (Unusued)

        Generally in the case of a bad client certificate, the request is
        aborted without generating a call to the underlying WSGI application.
        (So the GENEROUS and FAILED states are actually unused). If the base
        transport is non-SSL, the _VERIFY state will be NONE.
        When _VERIFY is NONE, the _DN fields will not be present.

        These headers will always be cleared to prevent any client from
        spoofing the authentication.
    """

    @staticmethod
    def __dn_to_str(x509name):
        """ Converts an pyOpenSSL X509Name object to an RFC style
            string representation.
            i.e. C=XX, O=TestOrg, OU=TestUnit, CN=My User
        """
        dn_parts = []
        # E-mail is special as it joins on to CN
        if hasattr(x509name, 'CN'):
            if hasattr(x509name, 'emailAddress'):
                dn_parts.append("CN=%s/emailAddress=%s" % \
                                (x509name.CN, x509name.emailAddress))
            else:
                dn_parts.append("CN=%s" % x509name.CN)
        elif hasattr(x509name, 'emailAddress'):
            dn_parts.append("emailAddress=%s" % x509name.emailAddress)
        # Now do other, more standard, parts...
        for field in ('OU', 'O', 'L', 'ST', 'C'):
            if not hasattr(x509name, field):
                continue
            field_val = getattr(x509name, field)
            if field_val:
                dn_parts.append("%s=%s" % (field, field_val))
        dn_parts.reverse()
        return ', '.join(dn_parts)

    def render(self, request):
        """ Main request handling function.

            Processes the SSL client cert details into the request headers
            and then calls the base WSGI application render function.
            Returns a standard request status.
        """
        # Immediately clear any SSL headers from inbound request for security
        headers = request.requestHeaders
        for hdr in ("SSL_CLIENT_S_DN", "SSL_CLIENT_I_DN", "SSL_CLIENT_VERIFY"):
            headers.removeHeader(hdr)
        # Now we can check whether this is an SSL connection
        transport = request.transport
        valid = False
        client_subject = None
        client_issuer = None
        if hasattr(transport, 'getPeerCertificate'):
            # SSL transport
            cert = transport.getPeerCertificate()
            if cert:
                # SSL transport + client with cert
                valid = True
                client_subject = self.__dn_to_str(cert.get_subject())
                client_issuer = self.__dn_to_str(cert.get_issuer())
        if valid:
            headers.addRawHeader('SSL_CLIENT_VERIFY', 'SUCCESS')
            if client_subject:
                headers.addRawHeader('SSL_CLIENT_S_DN', client_subject)
            if client_issuer:
                headers.addRawHeader('SSL_CLIENT_I_DN', client_issuer)
        else:
            headers.addRawHeader('SSL_CLIENT_VERIFY', 'NONE')
        # Finally call base processor
        return wsgi.WSGIResource.render(self, request)


class WSGIServer(object):
    """ A standalone WSGI server. """

    @staticmethod
    def __load_certs(fnames):
        """ Loads one or more PEM encoded certificate files and returns the
            data as a string.
            fnames - The filename as a string to load one file, or an interable
                     object containing multiple filenames.
            Returns the file data as a single string.
        """
        if isinstance(fnames, str):
            fnames = [fnames]
        data = ""
        for fname in fnames:
            with open(fname, "r") as file_fd:
                data += file_fd.read()
                file_fd.close()
        return data

    def __init__(self):
        """ Initialises this server. """
        pass

    def __build_sslopts(self, cert, key, cafile, client_req):
        """ Creates a twisted SSL opts object with the given parameters.
            See the parameter descriptions for add_server function.
            Returns SSL options object (or None if cert or key are None).
        """
        if not cert or not key:
            return None
        if os.path.realpath(cert) == os.path.realpath(key):
            # Server cert & key files are in the same file
            server_pem = self.__load_certs(cert)
        else:
            server_pem = self.__load_certs((cert, key))
        ssl_key = ssl.PrivateCertificate.loadPEM(server_pem)

        ssl_opts = None
        if cafile:
            ca_pem = self.__load_certs(cafile)
            ca_data = ssl.Certificate.loadPEM(ca_pem)
            ssl_opts = ssl_key.options(ca_data)
            ssl_opts.requireCertificate = client_req
        else:
            ssl_opts = ssl_key.options()
        return ssl_opts

    def add_server(self, port, app_server, cert, key, cafile, client_req=False):
        """ Adds a web/application server on a given port.
            port - The port number to listen on.
            app_server - A WSGI style application server (such as Flask).
            cert - The path to the SSL cert file.
            key - The path to the SSL key file.
            cafile - The path to the CA file for verifying clients.
            client_req - If cafile provided, is a client certificate REQUIRED?
                         If True, clients without a cert will be rejected.
            cert & key are optional (if set to None the server will be HTTP-only)
            cafile is optional, if set to None, client certificate are disabled.
            Returns None.
        """
        # Set-up site/resource
        resource = WSGIAuth(reactor, reactor.getThreadPool(), app_server)
        site = server.Site(resource)
        # Build SSL options (if required)
        ssl_opts = self.__build_sslopts(cert, key, cafile, client_req)
        # Attach everything to a port
        if ssl_opts:
            reactor.listenSSL(port, site, ssl_opts)
        else:
            reactor.listenTCP(port, site)

    @staticmethod
    def run():
        """ Starts the web server(s).
            Only returns on interrupt.
        """
        reactor.run()
