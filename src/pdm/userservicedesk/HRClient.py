__author__ = 'martynia'

from pdm.framework.RESTClient import RESTClient

class HRClient(RESTClient):
    def __init__(self):
        RESTClient.__init__(self, 'users')

    def hello(self):
        """ Call the hello function on the server and return the result.
        """
        return self.get('hello')

    def get_users(self):
        """ Returns a dict of users.
        """
        return self.get('users')

    def get_user(self, uid):
        uri = 'users/%s' % uid
        return self.get(uri)

    def del_user(self, tid):
        """ Deletes a user by username.
            Returns None
        """
        target = 'users/%u' % tid
        return self.delete(target)

    def add_user(self, userdict):
        """ Adds a user.
            Returns user data.
        """
        return self.post('users', userdict)

    def login(self, username, password):
        """
        :param username: username or email address
        :param password: password
        :return: user token
        """

        cred = {"username":username, "passwd": password}

        return self.post("login", cred)

