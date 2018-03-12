
from getpass import getpass
from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.TransferClient import TransferClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade


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
        # change password
        user_parser = subparsers.add_parser('passwd')
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.set_defaults(func=self.passwd)
        #whoami
        user_parser = subparsers.add_parser('whoami')
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.set_defaults(func=self.whoami)
        #list
        user_parser = subparsers.add_parser('list', help = "List remote site.")
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.add_argument('url', type=str)
        user_parser.add_argument('-m', type=int, help = 'max tries')
        user_parser.add_argument('-p', type=int, help = 'priority')
        user_parser.set_defaults(func=self.list)
        #remove
        user_parser = subparsers.add_parser('remove', help = "remove files from remote site.")
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.add_argument('url', type=str)
        user_parser.add_argument('-m', type=int)
        user_parser.add_argument('-p', type=int)
        user_parser.set_defaults(func=self.list)

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
        User login function. Prints out a token obtained from the server.
        """
        password = getpass()

        client  = HRClient()
        token = client.login(args.email, password)
        print token

    def passwd(self, args):
        """ Change user password """

        token = args.token

        password = getpass(prompt='Old Password')
        newpassword = getpass(prompt='New Password')
        newpassword1 = getpass(prompt='New Password')

        if newpassword != newpassword1:
            print "Passwords don't match. Aborted"
            return

        client = HRClient()
        client.set_token(token)
        ret = client.change_password(password, newpassword)
        print ret

    def whoami(self, args):
        """
        get users own data
        """

        token = args.token
        client = HRClient()
        client.set_token(token)
        ret = client.get_user()
        print ret

    def list(self, args):
        token = args.token
        if args.token:
            client = TransferClientFacade(token)
            client.list(args.url) # max_tries, priority)

    def remove(self, args):
        token = args.token
        if args.token:
            client = TransferClientFacade(token)
            client.remove(args.url) # max_tries, priority)

    def copy(selfself, args):
        pass