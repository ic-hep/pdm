from pdm.userservicedesk.TransferClient import TransferClient
from urlparse import urlparse


class TransferClientFacade(TransferClient):
    """
    Transfer client facade. Method take URI(s) as parameter(s) rather the its parts.
    """

    def __init__(self, token):
        super(TransferClientFacade, self).__init__(token)

    def list(self, url, **kwargs):
        parts = urlparse(url)
        if parts.scheme:
            kwargs['protocol'] = parts.scheme
        return super(TransferClientFacade, self).list(parts.netloc, parts.path, **kwargs )

    def copy(self, src_url, dst_url, **kwargs):
        dst_parts = urlparse(dst_url)
        src_parts = urlparse(src_url)
        if src_parts.scheme:
            kwargs['protocol'] = src_parts.scheme
        super(TransferClientFacade, self).copy(src_parts.netloc, src_parts.path, dst_parts.netloc, dst_parts.path,
                                               **kwargs)
    def remove(self, src_url, **kwargs):
        src_parts = urlparse(src_url)
        if src_parts.scheme:
            kwargs['protocol'] = src_parts.scheme
        super(TransferClientFacade, self).remove(src_parts.netloc, src_parts.path, **kwargs)
