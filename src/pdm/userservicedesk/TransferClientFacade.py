
from pdm.userservicedesk.TransferClient import TransferClient
from urlparse import urlparse

class TransferClientFacade(TransferClient):
    """
    Transfer client facade. Method take URI(s) as parameter(s) rather the its parts.
    """

    def __init__(self, token):
        super(TransferClientFacade, self).__init__(token)

    def list(self, url, max_tries=2, priority=5):
        parts = urlparse(url)
        super(TransferClientFacade, self).list(parts.netloc, parts.path, max_tries, priority, parts.scheme)

    def copy(self, src_url, dst_url, max_tries=2, priority=5):
        dst_parts = urlparse(dst_url)
        src_parts = urlparse(src_url)
        super(TransferClientFacade, self).copy(src_parts.netloc, src_parts.path, dst_parts.netloc, dst_parts.path, max_tries, priority)
        
    def remove(self, src_url, max_tries=2, priority=5):
        src_parts = urlparse(src_url)
        super(TransferClientFacade, self).remove(src_parts.netloc, src_parts.path, max_tries, priority)
    