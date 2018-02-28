
from getpass import getpass
from pdm.userservicedesk.HRClient import HRClient

class UserCommand(object):

    def __init__(self, subparsers):
        # register
        user_parser = subparsers.add_parser('register')
        user_parser.add_argument('-e', '--email', type=str, required=True)
        user_parser.add_argument('-n', '--name', type=str)
        user_parser.add_argument('-s', '--surname', type=str)
        user_parser.set_defaults(func=self.register)
        # login
        user_parser = subparsers.add_parser('login')
        user_parser.add_argument('-e', '--email', type=str, required=True)
        user_parser.set_defaults(func=self.login)

        # sub-command functions
    def register(self, args):
        """
        User registration function
        :param parser arguments when called by the master command (pdm)
        :return:
        """
        if not args.name:
            args.name = raw_input("Please enter your given name: ")
        if not args.surname:
            args.surname = raw_input("Please enter your surname: ")

        password = getpass()
        client  = HRClient()
        userdict = {'surname':args.surname, 'name':args.name, 'email':args.email, 'password':password}
        client.add_user(userdict)
        print "User registered %s %s %s " % (args.name, args.surname, args.email)

    def login(self, args):
        """
        User login function
        :return: token
        """
        password = getpass()

        client  = HRClient()
        token = client.login(args.email, password)
        return token

    def passwd(self, args):
        pass

    def whoami(self):
        pass