#!/usr/bin/env python
""" Site service client module. """

from pdm.framework.RESTClient import RESTClient

class SiteClient(RESTClient):
    """ Client class for the SiteService service.
        See SiteService API documentation for description
        of parameters & return values.
    """

    def __init__(self):
        """ Create the site client. """
        super(SiteClient, self).__init__('site')

    def get_service_info(self):
        """ Get information about the service.
        """
        return self.get('service')

    def get_sites(self):
        """ Gets a list of all visible sites.
        """
        return self.get('site')

    def get_site(self, site_id):
        """ Gets all details about a specific site. """
        return self.get('site/%u' % site_id)

    def add_site(self, site_info):
        """ Adds a site to the database.
            site_info is a dictionary of details.
        """
        return self.post('site', site_info)

    def del_site(self, site_id):
        """ Deletes a site. """
        self.delete('site/%u' % site_id)

    def get_endpoints(self, site_id):
        """ Gets a list of site gridftp endpoints. """
        return self.get('endpoint/%u' % site_id)

    def del_user(self, user_id):
        """ Deletes all data relating to user_id. """
        self.delete('user/%u' % user_id)

    def get_session_info(self, site_id):
        """ Get session info for user at site. """
        return self.get('session/%u' % site_id)

    # pylint: disable=too-many-arguments
    def logon(self, site_id, username, password, lifetime=36, voms=None):
        """ Create a user session at the given site. """
        data = {'username': username,
                'password': password,
                'lifetime': lifetime}
        if voms:
            data['vo'] = voms
        self.post('session/%u' % site_id, data)

    def logoff(self, site_id):
        """ Destroys user session credentials. """
        self.delete('session/%u' % site_id)

    def get_cred(self, site_id, user_id):
        """ Gets a credential for a user at a site. """
        return self.get('cred/%u/%u' % (site_id, user_id))
