#!/usr/bin/env python
""" Endpoint/Site service client module. """

from copy import deepcopy
from pdm.framework.RESTClient import RESTClient

class EndpointClient(RESTClient):
    """ Client cleass for EndpointService service. """

    def __init__(self):
        """ Create the endpoint client. """
        super(EndpointClient, self).__init__('endpoint')

    def get_sites(self):
        """ Gets a list of all sites.
            Returns a list of site dictionaries containing:
              - site_id - Int, unique id
              - site_name - Str, short site name
              - site_desc - Str, site description
        """
        return self.get('site')

    def add_site(self, site_name, site_desc):
        """ Adds a site.
            site_name/site_desc are strings.
            Returns int - ID of new site.
        """
        data = {}
        data['site_name'] = site_name
        data['site_desc'] = site_desc
        return self.post('site', data)

    def get_site(self, site_id):
        """ Gets site info incl. endpoints.
            site_id - int - Id of the site to lookup.
            Returns a dictionary of site information:
              site_id - The site ID.
              site_name - The name of the site.
              site_desc - Description of the site.
              endpoints - Dictonary of site endpoints:
                          key is endpoint id (int)
                          value is endpoint URI (str)
        """
        site_info = self.get('site/%u' % site_id)
        # Make sure endpoint keys get converted back to int
        endpoints = site_info['endpoints']
        endpoints = {int(x): endpoints[x] for x in endpoints}
        site_info['endpoints'] = endpoints
        return site_info

    def del_site(self, site_id):
        """ Deletes a site and all associated data
            (endpoints, mappings, etc...)
            Returns nothing.
        """
        self.delete('site/%u' % site_id)

    def add_endpoint(self, site_id, ep_uri):
        """ Adds an endpoint to a site.
            site_id - int - The site to add the EP to.
            ep_uri - str - The endpoint URI string.
            Returns the new endpoint ID, int.
        """
        data = {'ep_uri': ep_uri}
        return self.post('site/%u' % site_id, data)

    def del_endpoint(self, site_id, ep_id):
        """ Deletes a specific endpoint at a site.
            site_id and ep_id are ints.
            Returns None.
        """
        self.delete('site/%u/%u' % (site_id, ep_id))

    def get_mappings(self, site_id):
        """ Gets all mappings for a given site.
            site_id is the ID of the site.
            Return value is a dict:
              - key is int ep_id.
              - value is endpoint URI str.
        """
        mappings = self.get('sitemap/%u' % site_id)
        # One complication is that JSON returns strings
        # instead of ints if used for keys, so convert them back.
        return {int(ep_id): ep_uri for ep_id, ep_uri in mappings.iteritems()}

    def add_mapping(self, site_id, user_id, user_name):
        """ Add a mapping for a user_id to a username at
            a site.
            site_id and user_id are ints.
            user_name is the local user name at the site, str.
            Returns None.
        """
        data = {}
        data['user_id'] = user_id
        data['local_user'] = user_name
        self.post('sitemap/%u' % site_id, data)

    def del_mapping(self, site_id, user_id):
        """ Deletes a mapping for a user_id at a site.
            site_id and user_id are ints.
            Returns None.
        """
        self.delete('sitemap/%u/%u' % (site_id, user_id))

    def del_user(self, user_id):
        """ Delete the user mappings for a user at all sites.
            user_id - int - The user ID to delete.
            Returns None.
        """
        self.delete('sitemap/all/%u' % user_id)


class MockEndpointClient(object):
    """ Mock version of EndpointClient class.
        Stores all data in memory.
    """

    def __init__(self):
        """ Create the endpoint client. """
        self.__sites = {}
        self.__next_siteid = 1
        self.__endpoints = {}
        self.__next_epid = 1
        self.__mappings = {}

    def get_sites(self):
        """ Gets a list of all sites.
            Returns a list of site dictionaries containing:
              - site_id - Int, unique id
              - site_name - Str, short site name
              - site_desc - Str, site description
        """
        return deepcopy(self.__sites.values())

    def add_site(self, site_name, site_desc):
        """ Adds a site.
            site_name/site_desc are strings.
            Returns int - ID of new site.
        """
        for site in self.__sites.itervalues():
            if site['site_name'] == site_name:
                # Site already exists
                raise RuntimeError("Request failed with code 409.")
        new_id = self.__next_siteid
        self.__next_siteid += 1
        new_site = {'site_id': new_id,
                    'site_name': site_name,
                    'site_desc': site_desc}
        self.__sites[new_id] = new_site
        self.__endpoints[new_id] = {}
        self.__mappings[new_id] = {}
        return new_id

    def get_site(self, site_id):
        """ Gets site info incl. endpoints.
            site_id - int - Id of the site to lookup.
            Returns a dictionary of site information:
              site_id - The site ID.
              site_name - The name of the site.
              site_desc - Description of the site.
              endpoints - Dictonary of site endpoints:
                          key is endpoint id (int)
                          value is endpoint URI (str)
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        site_info = deepcopy(self.__sites[site_id])
        endpoints = deepcopy(self.__endpoints[site_id])
        site_info['endpoints'] = endpoints
        return site_info

    def del_site(self, site_id):
        """ Deletes a site and all associated data
            (endpoints, mappings, etc...)
            Returns nothing.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        del self.__sites[site_id]
        del self.__endpoints[site_id]
        del self.__mappings[site_id]

    def add_endpoint(self, site_id, ep_uri):
        """ Adds an endpoint to a site.
            site_id - int - The site to add the EP to.
            ep_uri - str - The endpoint URI string.
            Returns the new endpoint ID, int.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        ep_id = self.__next_epid
        self.__next_epid += 1
        self.__endpoints[site_id][ep_id] = ep_uri
        return ep_id

    def del_endpoint(self, site_id, ep_id):
        """ Deletes a specific endpoint at a site.
            site_id and ep_id are ints.
            Returns None.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        if not ep_id in self.__endpoints[site_id]:
            raise RuntimeError("Request failed with code 404.")
        del self.__endpoints[site_id][ep_id]

    def get_mappings(self, site_id):
        """ Gets all mappings for a given site.
            site_id is the ID of the site.
            Return value is a dict:
              - key is int ep_id.
              - value is endpoint URI str.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        return deepcopy(self.__mappings[site_id])

    def add_mapping(self, site_id, user_id, user_name):
        """ Add a mapping for a user_id to a username at
            a site.
            site_id and user_id are ints.
            user_name is the local user name at the site, str.
            Returns None.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        if user_id in self.__mappings[site_id]:
            raise RuntimeError("Request failed with code 409.")
        self.__mappings[site_id][user_id] = user_name

    def del_mapping(self, site_id, user_id):
        """ Deletes a mapping for a user_id at a site.
            site_id and user_id are ints.
            Returns None.
        """
        if not site_id in self.__sites:
            raise RuntimeError("Request failed with code 404.")
        if not user_id in self.__mappings[site_id]:
            raise RuntimeError("Request failed with code 404.")
        del self.__mappings[site_id][user_id]

    def del_user(self, user_id):
        """ Delete the user mappings for a user at all sites.
            user_id - int - The user ID to delete.
            Returns None.
        """
        for mappings in self.__mappings.itervalues():
            if user_id in mappings:
                del mappings[user_id]
