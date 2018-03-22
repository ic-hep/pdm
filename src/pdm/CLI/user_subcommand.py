"""
Define pdm subcommands and action functions for them:
Example usage: pdm register -e fred@flintstones.com -n Fred -s Flintstone
"""
from getpass import getpass
from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade
from time import sleep


class UserCommand(object):
    """
    Define user sub-commands and assign actions fro them.
    """

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
        # whoami
        user_parser = subparsers.add_parser('whoami')
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.set_defaults(func=self.whoami)
        # list
        user_parser = subparsers.add_parser('list', help="List remote site.")
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.add_argument('site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int, help='max tries')
        user_parser.add_argument('-p', type=int, help='priority')
        user_parser.set_defaults(func=self.list)
        # remove
        user_parser = subparsers.add_parser('remove', help="remove files from remote site.")
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.add_argument('site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.set_defaults(func=self.remove)
        # copy
        user_parser = subparsers.add_parser('copy',
                                            help="copy files from source to destination site.")
        user_parser.add_argument('-t', '--token', type=str, required=True)
        user_parser.add_argument('src_site', type=str)
        user_parser.add_argument('dst_site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.set_defaults(func=self.copy)


        # sub-command functions

    def register(self, args):  # pylint: disable=no-self-use
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
        client = HRClient()
        userdict = {'surname': args.surname, 'name': args.name,
                    'email': args.email, 'password': password}
        client.add_user(userdict)
        print "User registered %s %s %s " % (args.name, args.surname, args.email)

    def login(self, args):  # pylint: disable=no-self-use
        """
        User login function. Prints out a token obtained from the server.
        """
        password = getpass()

        client = HRClient()
        token = client.login(args.email, password)
        print token

    def passwd(self, args):  # pylint: disable=no-self-use
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

    def whoami(self, args):  # pylint: disable=no-self-use
        """
        get users own data
        """

        token = args.token
        client = HRClient()
        client.set_token(token)
        ret = client.get_user()
        print ret

    def list(self, args):  # pylint: disable=no-self-use
        """
        List files at remote site.
        :param args:
        :return:
        """
        max_iter = 50
        nap = 0.2
        count = 1
        #
        token = self._get_token(args)
        if token:
            client = TransferClientFacade(token)
            # remove None values, position args, func and toke from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None and key not in ('func', 'site', 'token')}
            resp = client.list(args.site, **accepted_args)  # max_tries, priority)
            if resp:
                while resp['status'] not in ('DONE', 'FAILED'):
                    sleep(nap)  # seconds
                    resp = client.list(args.site, **accepted_args)
                    count += 1
                    if not resp:
                        resp = {'status': 'None'}  # to make while-else
                        # below work (no such site)
                    if count >= max_iter: break
                else:
                    if resp['status'] == 'DONE':
                        listing_dict = client.output(resp['id'])
                        listing = listing_dict['listing']
                        print listing
                    elif resp['status'] == 'FAILED':
                        print " Failed to obtain a listing"
                    else:
                        print "Timeout. Last status is %s", resp['status']
            else:
                print " No such site %s ?", args.site

    def remove(self, args):  # pylint: disable=no-self-use
        """
        Remove files at remote site
        :param args:
        :return:
        """
        token = self._get_token(args)
        if token:
            client = TransferClientFacade(token)
            # remove None values, position args, func and toke from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None and key not in ('func', 'site', 'token')}
            client.remove(args.site, **accepted_args)  # max_tries, priority)

    def copy(self, args):  # pylint: disable=no-self-use
        """
        Copy files between sites
        :param args:
        :return:
        """
        token = self._get_token(args)
        if token:
            client = TransferClientFacade(token)
            src_site = args.src_site
            dst_site = args.dst_site
            # remove None values, position args, func and toke from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None
                             and key not in ('func', 'src_site', 'dst_site', 'token')}
            client.copy(src_site, dst_site, **accepted_args)

    def _get_token(self, args):
        # TODO poosible token from a file
        return args.token
