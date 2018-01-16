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
    """ Converts an pyOpenSSL X509Name object to an OpenSSL style
        string representation.
        i.e. CN=My User,OU=TestUnit,O=TestOrg,C=XX
    """
    dn_parts = []
    for field in ('emailAddress', 'CN', 'OU', 'O', 'L', 'ST', 'C'):
      if not hasattr(x509name, field):
        continue
      field_val = getattr(x509name, field)
      if field_val:
        dn_parts.append("%s=%s" % (field, field_val))
    return ','.join(dn_parts)

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
      with open(fname, "r") as fd:
        data += fd.read()
        fd.close()
    return data

  def __init__(self, port, app):
    """ Initialises the web server. """
    self.__port = port
    self.__resource = WSGIAuth(reactor, reactor.getThreadPool(), app)
    self.__site = server.Site(self.__resource)
    self.__ssl_opts = None

  def enable_ssl(self, cert, key, cafile=None, client_req=False):
    """ Enable SSL-only connections on this server.
        cert & key should be paths to PEM encoded X509 certs for the server.
        Setting cafile enables client cert authentication.
        If client_req is false, client certificates become optional (this only
        has an affect if cafile was set).
        cert and key may point to the same file for a combined file with
        both entitites in.
        Returns None.
    """
    if os.path.realpath(cert) == os.path.realpath(key):
      # Server cert & key files are in the same file
      server_pem = self.__load_certs(cert)
    else:
      server_pem = self.__load_certs((cert, key))
    server_key = ssl.PrivateCertificate.loadPEM(server_pem)

    ca_data = None
    if cafile:
      ca_pem = self.__load_certs(cafile)
      ca_data = ssl.Certificate.loadPEM(ca_pem)

    if ca_data:
      # We accept client certificates
      self.__ssl_opts = server_key.options(ca_data)
      self.__ssl_opts.requireCertificate = client_req
    else:
      # Normal server-cert-only SSL
      self.__ssl_opts = server_key.options()

  def disable_ssl(self):
    """ Disable SSL on this server. Returns None.
    """
    self.__ssl_opts = None

  def run(self):
    """ Starts the web server on the given port.
        Only returns on interrupt.
    """
    if self.__ssl_opts:
      reactor.listenSSL(self.__port, self.__site, self.__ssl_opts)
    else:
      reactor.listenTCP(self.__port, self.__site)
    reactor.run()

