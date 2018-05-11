Endpoint Service API
====================

The site/endpoint database performs two primary functions:
  - To keep a list of sites & endpoints for transferring files.
  - To store mappings of service users to local users at each site.

All calls return usual HTTP error codes:
  - 200 on success & object creation.
  - 400 for a malformed request (such as missing parameters).
  - 404 on item not found.
  - 409 if the item already exists (in the case of duplicate
    mappings or short site names).
  - 500 on unexpected errors.

.. function:: GET /site

  Returns a list of all sites.

  Returns (List of dictionaries containing):
    - site_id(int): The unique site ID.
    - site_name(str): The short site name.
    - site_desc(str): Longer description for this site.

.. function:: POST /site

  Adds a site.

  Input (POST dictionary):
    - site_name(str): The short site name.
    - site_desc(str): The longer site description.
  Returns (int):
    The new site_id.

.. function:: GET /site/<site_id(int)>

  Gets a description of a site, including configured endpoints.

  Returns (dictionary):
    - site_id(int): The unique site ID.
    - site_name(str): The short side name.
    - site_desc(str): Longer description for this site.
    - endpoints (dict):

      - key(int): ep_id
      - value(str): Full endpoint URI.

.. function:: DELETE /site/<site_id(int)>

  Deletes a site (and all endpoints & mappings for the site).

  Returns:
    - None

.. function:: POST /endpoint/<site_id(int)>

  Adds an endpoint to a site.

  Input (POST dictionary):
    - ep_uri(str): Endpoint URI.
  Returns (int):
    - New ep_id.

.. function:: DELETE /endpoint/<site_id(int)>/<ep_id(int)>

  Deletes an endpoint from a site.

  Returns:
    - None

.. function:: GET /sitemap/<site_id(int)>

  Gets the list of all configured user mappings for the given site.

  Returns (dictionary):
    - key(int): user_id
    - value(str): The local_user name for this user at this site.

.. note:: JSON dict key values are generally converted to strings, so user_id
          will be a string representation of an int.

.. function:: POST /sitemap/<site_id(int)>

  Adds a local user mapping to a site.

  Input (POST dictionary):
    - local_user(str): The local (to the site) user name.
    - user_id(int): The UID for the user on this service.
  Returns:
    - None

.. function:: DELETE /sitemap/<site_id(int)>/<user_id(int)>

  Removes a local user mapping from a site.

  Returns:
    - None

.. function:: DELETE /sitemap/all/<user_id(int)>

  Removes a local user mapping from all sites. For use when a user
  is completely deleted.

  Returns:
    - None
