Site Service API
================

The site service keeps a database of site information and provides site-domain
authentication. All functions require a user token unless otherwise stated. All
certificates are in PEM format unless otherwise stated.

The auth_type parameter currently accepts two constants:
 - 0 - PLAIN_AUTH, Authentication is done using a vanilla user proxy.
 - 1 - VOMS_AUTH, Authentication expects a VOMS proxy.

If a site has a service CA or user CA, then those are used for all operations.
If both are None, then the CA directory from the config is used. Failing that,
the system level CA certificates will be used to verify connections & users at
the site.

.. function:: GET /service

   Return central service information. The output keys are all optional and
   will only be included if the server is configured to support the relevant
   feature.

   Requires no authentication.

   Returns a dictionary containing:
     - central_ca(str): PEM encoded CA certificate(s) for central services.
     - user_ep(str): The full endpoint for the user service.
     - vos(list): A list of strings of VO names supported by this service.

.. function:: GET /site

   Returns a list of all sites that the current user can see. This will be
   all sites owned by them and all public sites.

   Returns a list of dictonaries containing:
     - site_id(int): The unique site ID.
     - site_name(str): The (unique) short site name.
     - site_desc(str): The longer site description.
     - def_path(str): The default (starting) path to use at this site.
     - public(bool): Set to true if this site is visible to everyone.
     - is_owner(bool): Set to true if the user is the owner of the site.

.. function:: GET /site/<site_id(int)>

   Gets information on a specific site. Only works on sites which the user
   can see (as owner or public), other sites will return 404 even if they exist.

   Returns a dictionary containing:
     - site_id(int): The unique site ID.
     - site_name(str): The site name.
     - site_desc(str): The longer site description.
     - user_ca_cert(str): The CA used for user certificates (or None).
     - service_ca_cert(str): The CA used for site services (or None).
     - auth_type(int): The authentication mode for this site.
     - auth_uri(str): The myproxy endpoint for this site in host:port format.
     - public(bool): If true, site is visible to all users.
     - def_path(str): The default path to use when connecting to this site.
     - is_owner(bool): Set to true if the current user owns this site.
     - endpoints(list of str): List of gridftp endpoints for this site in
                               host:port format.

.. function:: POST /site

   Register a new site.

   Input (POST dictionary):
     Same as get site, but without is_owner. user_ca_cert and service_ca_cert
     are optional and can be ommitted or set to None if unneeded.
   Returns (int):
     The site_id of the registered/updated site.

.. function:: DELETE /site/<site_id(int)>

   Deletes a site. A user can only delete sites that they are the owner of.

   Returns:
     - None.

.. function:: GET /endpoint/<site_id(int)>

   Get a list of endpoints for a given site. Generally configured for
   certificate authentication.

   Returns (list of str):
     Gridftp endpoints for the site in host:port format.

.. function:: DELETE /user/<user_id(int)>

   Deletes all data about the given user ID. A user may only delete themselves.
   This removes all sites and cached credentials belonging to the user.

.. function:: GET /session/<site_id(int)>

   Gets the sessions information for the current user at the given site.
   Optional return paramters may be missing from the dict entriely.

   Returns (dictionary):
     - ok(bool): Set to True if there is a valid credential.
     - username(str, optional): The username for the user at this site.
     - expiry(str-datetime, optional): The expiry time of the credential if one
                                       is registered (may be in the past).

.. function:: POST /session/<site_id(int)>

   Login a user at the given site. If a user is already logged on, their
   credential will be renewed/replaced by the new one if successful.

   Input (POST dictionary):
     - username(str): The site-specific username.
     - password(str): The users' site password.
     - lifetime(int): The time (in hours) to create the credential for.
     - vo(str, optiona): The VO to use in the credential VOMS extension.

   Returns:
     - None

.. function:: DELETE /session/<site_id(int)>

   Logs a user out from a site. If the user doesn't have a session
   then nothing happens and success is still returned.

   Returns:
     - None.

.. function:: GET /cred/<site_id(int)>/<user_id(int)>

   Get the user credential for a given site and central user ID.
   Authentication is ususally done by cert. Returns 404 if user
   doesn't have a credential for the given site.

   Returns:
     - PEM encoded proxy for the user.

