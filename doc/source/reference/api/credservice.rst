Credential Service API
======================

All functions return HTTP code 200 on success, 404 if a given object is not
found or 500 with a suitable error string in an exception case.

.. function:: GET /ca

   Returns the CA certificate used to issue user certificates.

   Returns (Dictionary):
      - ca(str): The PEM encoded CA certificate.

.. function:: POST /user

   Creates a set of credentials for the specified user in the database.
   If the user already exists, a renewal of the user's credentials will
   be attempted. The credentials will be encrypted with user_key which will
   be required to issue any derived credentials. A different key may be used
   when renewing an existing set of credentials.

   Input (POST Dictionary):
      - user_id(int): The unique user ID.
      - user_key(str): A key to encrypt the credentials with.
   Returns:
      - None

.. function:: DELETE /user/<user_id(int)>

   Removes all credentials for the given user from the database. This includes
   derived credentials for the user.
      
   Returns:
      - None

.. warning:: User credentials (particularly proxies) stored outside of this
             service may remain valid until their natural expiry date.

.. function:: GET /user/<user_id(int)>

   Gets details of the user credentials.

   Returns (Dictionary):
      - valid_until(datetime): The expiry date of the credentials.

.. function:: POST /cred

   Creates a new derived credential (proxy) for a specific job.

   Input (Dictionary):
      - user_id(int): The user identifier.
      - user_key(str): The user's unique key.
      - cred_type(int): The type of credential to create:
         - 0: X.509 compatible proxy certificate.
         - 1: SSH compatible key.
      - max_lifetime(int): The number of seconds that this credential should
        be renewable for.

   Returns (Dictionary):
      - token(str): An opaque identifier for the new credentials.

.. function:: DELETE /cred/<cred_token(str)>

   Destroys a given credential from the database.

   Returns:
      - None

.. function:: GET /cred/<cred_token(str)>

   Gets a credential associated with a token. For X.509 types, the output keys
   will be PEM encoded, for SSH keys the encoding will be standard OpenSSH
   format keys.

   Return (Dictionary):
      - cred_type(int): The type of credential (using the same mapping as
        POST /cred).
      - pub_key(str): The public part of this credential.
      - priv_key(str): The private part of this credential.
