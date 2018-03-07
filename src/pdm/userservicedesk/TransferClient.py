"""
RESTful client API for the HRService service
"""

from pdm.framework.RESTClient import RESTClient

class TransferClient(RESTClient):
    """
    RESTful transfer management client API. To list, copy and remove files from remote site.
    """
    def list(self, src_siteid, src_filepath):
        """
        List a given path. As for all clent calls it need a user token set in a request beforehand.
        Args:
            src_siteid (int): The id of the site containing the path to be listed.
            src_filepath (str): The path to list.
        Returns:
            dict: The Python dictionary representin the list of files.
        """



