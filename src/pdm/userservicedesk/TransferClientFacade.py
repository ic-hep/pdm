""" The Facade for the TransferClient. Uses URL as an argument to most
    of the methods (rather them its parts)
"""
from urlparse import urlparse
from pdm.userservicedesk.TransferClient import TransferClient


class TransferClientFacade(TransferClient):
    """
    Transfer client facade. Method take URI(s) as parameter(s) rather the its parts.
    """

    def __init__(self, token):
        super(TransferClientFacade, self).__init__(token)

    def list(self, url, **kwargs):
        """
        List the resource specified by URL.
        :param url: URL of the resource
        :param kwargs: additional arguments (like max_tries or priority)
        :return: the resource listing
        """
        parts = urlparse(url)
        if parts.scheme:
            kwargs['protocol'] = parts.scheme
        return super(TransferClientFacade, self).list(parts.netloc, parts.path, **kwargs)

    def copy(self, src_url, dst_url, **kwargs):
        """
        Copy files or directories from one site to another.
        :param src_url: source resource URL
        :param dst_url: destination resource URL
        :param kwargs: addition arguments (like max_tries ot priority)
        :return: copy result message
        """
        dst_parts = urlparse(dst_url)
        src_parts = urlparse(src_url)
        if src_parts.scheme:
            kwargs['protocol'] = src_parts.scheme
        return super(TransferClientFacade, self).copy(src_parts.netloc, src_parts.path,
                                               dst_parts.netloc, dst_parts.path,
                                               **kwargs)

    def remove(self, src_url, **kwargs):
        """
        Remove the resources (file or directory)
        :param src_url: URL of the resource
        :param kwargs: additional arguments (like max_tries or priority)
        :return: remove result message
        """
        src_parts = urlparse(src_url)
        if src_parts.scheme:
            kwargs['protocol'] = src_parts.scheme
        return super(TransferClientFacade, self).remove(src_parts.netloc, src_parts.path, **kwargs)

class MockTransferClientFacade(object):

    def __init__(self, token):
        self.__token = token

    def list(self, url, **kwargs):
        return str(url)

    def remove(self, url, **kwargs):
        parts = urlparse(url)
        return " File %s removed from site %s " % (parts.netloc, parts.path)

    def copy(self, surl, turl, **kwargs ):
        print " Mock copy called with ", surl, turl, kwargs
        return " copy %s to %s succeeded " % (surl, turl)