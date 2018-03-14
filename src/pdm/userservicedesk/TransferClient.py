"""
Client API for the file transfer management
"""

from pdm.endpoint.EndpointClient import EndpointClient
from pdm.cred.CredClient import CredClient
from pdm.framework.Tokens import TokenService
from pdm.workqueue.WorkqueueClient import WorkqueueClient
#from pdm.workqueue.WorkqueueDB import JobProtocol


class TransferClient(object):
    """
    Transfer management client API. To list, copy and remove files from remote site.
    """

    def __init__(self, user_token):
        """
        Constructor initialises all service clients involved in the transfer management:
        EndpointService, CredService and finally the WorkqueueService.
        :param user_token: user token
        """

        # endpoint
        self.__endp_client = EndpointClient()
        self.__endp_client.set_token(user_token)
        self.__sitelist = self.__endp_client.get_sites()
        # CS client setup
        unpacked_user_token = TokenService.unpack(user_token)
        cs_key = unpacked_user_token['key']
        cred_client = CredClient()
        cred_client.set_token(user_token)
        self.__credentials = cred_client.get_cred(cs_key)
        # work queue client
        self.__wq_client = WorkqueueClient()
        self.__wq_client.set_token(user_token)

    def list(self, src_site, src_filepath, **kwargs ):  #max_tries=2, priority=5, protocol=JobProtocol.GRIDFTP):
        """
        List a given path. As for all client calls it need a user token set in a request beforehand.
        Args:
            src_site (string): The name of the site containing the path to be listed.
            src_filepath (str): The path to list.
            kwargs: keyword arguments containing: protocol, max_tries and priority
        Returns:
            dict: The Python dictionary representing the list of files.
        """
        # sort out the site ID first:
        src_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == src_site]
        if src_siteid:
            # list
            response = self.__wq_client.list(src_siteid[0], src_filepath, self.__credentials, **kwargs)
                                            # max_tries, priority, protocol=JobProtocol.GRIDFTP)
            return response
        else:
            return None

    def copy(self, src_site, src_filepath, dst_site,  # pylint: disable=too-many-arguments
             dst_filepath, **kwargs):
        """
        Copy files between sites.

        :param src_site:
        :param src_filepath:
        :param dst_site:
        :param dst_filepath:
        :param kwargs: max_tries:
                       priority:
                       protocol:
        :return:
        """

        src_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == src_site]
        dst_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == dst_site]

        if not (src_siteid and dst_siteid):
            return None

        response = self.__wq_client.copy(src_siteid[0], src_filepath, dst_siteid[0],
                                         # pylint: disable=too-many-arguments
                                         dst_filepath, self.__credentials, **kwargs)

        return response

    def remove(self, src_site, src_filepath, **kwargs):
        """
        Remove files from a given site
        :param src_site: the site to contact
        :param src_filepath: the path to be removed
        :param kwargs: max_tries:
                       priority:
                       protocol:
        :return:
        """

        src_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == src_site]

        if not src_siteid:
            return None

        response = self.__wq_client.remove(src_siteid[0], src_filepath,
                                           self.__credentials,  # pylint: disable=too-many-arguments
                                           **kwargs)
        return response
