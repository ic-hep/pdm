"""
RESTful client API for the HRService service
"""

from pdm.framework.RESTClient import RESTClient


class HRClient(RESTClient):
    """
    RESTful user management client API
    """
    def __init__(self):
        super(HRClient, self).__init__('users')
        #RESTClient.__init__(self, 'users')

    def hello(self):
        """ Call the hello function on the server and return the result.
        """
        return self.get('hello')

    def get_user(self):
        """
        Get user's own data
        :return:
        """
        return self.get('users/self')

    def del_user(self):
        """ Deletes a user by username.
            Returns None
        """
        return self.delete('users/self')

    def add_user(self, userdict):
        """ Adds a user.
            Returns user data.
        """
        return self.post('users', userdict)

    def login(self, username, password):
        """
        User login procedure. Gets a token issued by a service.
        The client has to passed the token received to the set_token()
        operation in order to be able to use operations which require
        a token (e.g. get_user() )
        :param username: email address
        :param password: password
        :return: user token
        """

        cred = {"email": username, "passwd": password}

        return self.post("login", cred)

    def change_password(self, password, newpassword):
        """
        Request user password change
        :param password: original password
        :param newpassword: new password
        :return:
        """
        cred = {"newpasswd": newpassword, "passwd": password}
        return self.put("passwd", cred)

### not for now
#    def get_users(self):
#        """ Returns a dict of users.
#        """
#        return self.get('users')
