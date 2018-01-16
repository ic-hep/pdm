#!/usr/bin/env python
""" Standalone WSGI server modules for debugging.
"""
from twisted.web import server, wsgi
from twisted.internet import reactor

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
  def __X509Name2DN(x509name):
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
    if hasattr(transport, 'PeerCertificate'):
      # SSL transport
      cert = transport.PeerCertificate()
      if cert:
        # SSL transport + client with cert
        valid = True
        client_subject = self.__X509Name2DN(cert.get_subject())
        client_issuer = self.__X509Name2DN(cert.get_issuer())
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

  def __init__(self, app):
    """ Initialises the web server. """
    self.__resource = WSGIAuth(reactor, reactor.getThreadPool(), app)
    self.__site = server.Site(self.__resource)

  def run(self, port):
    """ Starts the web server on the given port.
        Only returns on interrupt.
    """
    reactor.listenTCP(port, self.__site)
    reactor.run()
