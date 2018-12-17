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
        :return: a dictionary containing user data
        """
        return self.get('users/self')

    def del_user(self):
        """
        Deletes a user.

        :return: None
        """
        return self.delete('users/self')

    def add_user(self, userdict):
        """
        Add a new user.

        :param userdict: user input data dictionary.
        The required fields (strings) are:

        * key: 'email'    value: a valid user email which server as a username
        * key: 'name'     value: user given name e.g. 'John'
        * key: 'surname'  value: user surname e.g. 'Smith'
        * key: 'password' value: password

        :return: Returns a dict with user data for convenience.
        """
        return self.post('users', userdict)

    def verify_user(self, tokendict):
        """
        Verify user's email address.

        :param tokendict: {'mailtoken' : token}. token is a base64 encoded string received by email.
        :return:
        """
        return self.post('verify', tokendict)

    def resend_email(self, userdict):
        """
        (Re)send a verification  email containing the mail token.
        :param userdict: a dict containg a email address to send an email to.
        :return:
        """
        return self.post('resend', userdict)

    def login(self, username, password):
        """
        User login procedure. Gets a token issued by a service.
        The client has to pass the token received to the set_token()
        operation in order to be able to use operations which require
        a token (e.g. get_user() ).

        :param username: email address
        :param password: password
        :return: user token
        """

        cred = {"email": username, "passwd": password}

        return self.post("login", cred)

    def change_password(self, password, newpassword):
        """
        Request user password change.

        :param password: original password
        :param newpassword: new password
        :return: a dictionary with user data
        """
        cred = {"newpasswd": newpassword, "passwd": password}
        return self.put("passwd", cred)

### not for now
#    def get_users(self):
#        """ Returns a dict of users.
#        """
#        return self.get('users')
