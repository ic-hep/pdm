Site Service API
================

The site service keeps a database of site information and provides site-domain
authentication.

.. function:: GET /service

   Return central service information.

   Returns a dictionary containing:
     - central_ca(str): PEM encoded CA certificate(s) for central services.

.. function:: GET /site

   Returns a list of all sites that the current user can see. This will be
   all sites owned by them and all public sites.

   Requires a user token header.

   Returns a list of dictonaries containing:
     - site_id(int): The unique site ID.
     - site_name(str): The (unique) short site name.
     - site_desc(str): The longer site description.

.. function:: GET /site/<site_id(int)>

   Gets information on a specific site. Only works on sites which the user
   can see, other sites will return 404 even if they exist.

   Requires a user token header.

   Returns a dictionary containing:
     - site_id(int): The unique site ID.
     - site_name(str): The site name.
     - site_desc(str): The longer site description.
     - ca_cert(str): The CA cert used to issue hostcerts for this site. PEM format.
     - myproxy(str): The "host:port" of the myproxy server for this site.
     - gridftpds(list of str): List of "host:port" of gridftpd servers for the site.
     - public(bool): Whether an endpoint should be publically visible.

.. function:: DELETE /site/<site_id(int)>

   Deletes a site. A user can only delete sites that they are the owner of.

   Requires a user token header.

   Returns:
     - None.

.. function:: POST /site

   Register or update a site.

   Requires a user token header.

   Input (POST dictionary):
     - site_name(str): The unique site name.
     - site_desc(str): A description of this site.
     - ca_cert(str): The CA cert used to issue hostcerts for this site. PEM format.
     - myproxy(str): The "host:port" of the myproxy server for this site.
     - gridftpds(list of str): List of "host:port" of gridftpd servers for the site.
     - public(bool): Whether an endpoint should be publically visible.
   Returns (int):
     The site_id of the registered/updated site.

.. function:: POST /site/<site_id(int)>/login

   Login a user at the given site.

   Requires a user token header.

   Input (POST dictionary):
     - username(str): The site-specific username.
     - password(str): The users' site password.

   Returns:
     - None

.. function:: GET /site/<site_id(int)>/credential

   Get the user credential for a given site and central user ID.

   Requires a user token header.

   Returns:
     - PEM encoded proxy for the user.

