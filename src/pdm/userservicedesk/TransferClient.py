"""
Client API for the file transfer management
"""
from copy import deepcopy
from pdm.site.SiteClient import SiteClient
from pdm.workqueue.WorkqueueClient import WorkqueueClient
from pdm.userservicedesk.HRService import HRService


# from pdm.workqueue.WorkqueueDB import JobProtocol


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

        self.__user_token = user_token
        # endpoint
        self.__site_client = SiteClient()
        self.__site_client.set_token(user_token)
        self.__sitelist = self.__site_client.get_sites()
        # get user id
        self.__user_id = HRService.get_token_userid(user_token)
        # work queue client
        self.__wq_client = WorkqueueClient()
        self.__wq_client.set_token(user_token)

    def list(self, src_site, src_filepath, **kwargs):
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
            response = self.__wq_client.list(src_siteid[0], src_filepath, **kwargs)
            # max_tries, priority, protocol=JobProtocol.GRIDFTP)
            return response
        return src_siteid  # an empty list

    def output(self, job_id, attempt=None):
        """
        Get job output
        :param job_id: job id
        :return: output as specified by workqueue client
        """
        response = self.__wq_client.output(job_id, attempt)
        return response

    def status(self, job_id):
        """
        Return status of a job.
        :param job_id: job id to get the status of.
        :return:
        """
        response = self.__wq_client.status(job_id)
        return response

    def list_sites(self):
        """
        Get list of sites
        :return: list of dictionaries with all keys but 'site_id'.
        """
        filtered_sites = deepcopy(self.__sitelist)
        for elem in filtered_sites:
            elem.pop('site_id', None)
        return filtered_sites

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
                                         dst_filepath, **kwargs)

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
                                           # pylint: disable=too-many-arguments
                                           **kwargs)
        return response

    def mkdir(self, site, dirpath, **kwargs):
        """
        Create a new directory at
        :param site:  site name
        :param dirpath: directory path
        :param kwargs: max_tries:
                       priority:
                       protocol:
        :return: workqueue client response
        """

        src_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == site]
        if not src_siteid:
            return None

        response = self.__wq_client.mkdir(src_siteid[0], dirpath,
                                          # pylint: disable=too-many-arguments
                                          **kwargs)
        return response

    def rename(self, site, oldname, newname, **kwargs):
        """
        Rename a file or directory (?) within site.
        :param site: site name
        :param oldname: old file name
        :param newname: new file name
        :param kwargs: max_tries:
                       priority:
                       protocol:
        :return: workqueue client response
        """

        src_siteid = [elem['site_id'] for elem in self.__sitelist if elem['site_name'] == site]
        if not src_siteid:
            return None

        response = self.__wq_client.rename(src_siteid[0], oldname, newname,
                                           **kwargs)

        return response
