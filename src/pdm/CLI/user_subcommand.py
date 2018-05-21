"""
Define pdm subcommands and action functions for them:
Example usage: pdm register -e fred@flintstones.com -n Fred -s Flintstone
"""
import os
import errno
from getpass import getpass
from time import sleep
from datetime import datetime
from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade


class UserCommand(object):
    """
    Define user sub-commands and assign actions fro them.
    """

    def __init__(self, subparsers):  # pylint: disable=too-many-statements

        # some constants:
        self.__max_iter = 50
        self.__nap = 0.5
        self.__count = 1

        # register
        user_parser = subparsers.add_parser('register')
        user_parser.add_argument('-e', '--email', type=str, required=True)
        user_parser.add_argument('-n', '--name', type=str)
        user_parser.add_argument('-s', '--surname', type=str)
        user_parser.set_defaults(func=self.register)
        # login
        user_parser = subparsers.add_parser('login', help="User login procedure")
        user_parser.add_argument('-e', '--email', type=str, required=True)
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help="optional token file location (default=~/.pdm/token)")

        user_parser.set_defaults(func=self.login)
        # change password
        user_parser = subparsers.add_parser('passwd')
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.set_defaults(func=self.passwd)
        # whoami
        user_parser = subparsers.add_parser('whoami')
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.set_defaults(func=self.whoami)
        # list
        user_parser = subparsers.add_parser('list', help="List remote site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int, help='max tries')
        user_parser.add_argument('-p', '--priority', type=int, help='priority')
        user_parser.add_argument('-s', '--protocol', type=str, help='protocol')
        user_parser.add_argument('-d', '--depth', type=int, default=0,
                                 help='listing depths. Default: current level')
        user_parser.set_defaults(func=self.list)
        # remove
        user_parser = subparsers.add_parser('remove', help="remove files from remote site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.add_argument('-b', '--block', action='store_true')
        user_parser.add_argument('-s', '--protocol', type=str, help='protocol')
        user_parser.set_defaults(func=self.remove)
        # copy
        user_parser = subparsers.add_parser('copy',
                                            help="copy files from source to destination site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('src_site', type=str)
        user_parser.add_argument('dst_site', type=str)
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.add_argument('-b', '--block', action='store_true')
        user_parser.add_argument('-s', '--protocol', type=str, help='protocol')
        user_parser.set_defaults(func=self.copy)
        # site list
        user_parser = subparsers.add_parser('sites',
                                            help="list available sites")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.set_defaults(func=self.sitelist)
        # status
        user_parser = subparsers.add_parser('status',
                                            help="get status of a job/task")
        user_parser.add_argument('job', type=str, help="job id as obtained"
                                                       " from copy or remove")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        st_help = "periodically check the job status (up to %d times)" % (self.__max_iter,)
        user_parser.add_argument('-b', '--block', action='store_true', help=st_help)
        user_parser.set_defaults(func=self.status)
        # log
        user_parser = subparsers.add_parser('log',
                                            help="get log of a job/task")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('job', type=int, help="job id as obtained"
                                                       " from copy, remove or list")
        user_parser.add_argument('-a', '--attempt', default=-1,
                                 help="Attempt number, leave out for the last attempt")
        user_parser.set_defaults(func=self.log)

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
        conf_pass = getpass(prompt='Confirm password: ')
        if password != conf_pass:
            print "Passwords don't match. Aborted"
            return

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

        filename = os.path.expanduser(args.token)
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                print os.strerror(exc.errno)
                raise

        with open(filename, "w") as f:
            os.chmod(filename, 0o600)
            f.write(token)

        print token

    def passwd(self, args):  # pylint: disable=no-self-use
        """ Change user password """

        token = UserCommand._get_token(args.token)

        password = getpass(prompt='Old Password: ')
        newpassword = getpass(prompt='New Password: ')
        newpassword1 = getpass(prompt='Confirm New Password: ')

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

        token = UserCommand._get_token(args.token)

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
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            # remove None values, position args, func and toke from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None and key not in ('func', 'site', 'token',
                                                               'config', 'verbosity')}
            resp = client.list(args.site, **accepted_args)  # max_tries, priority, depth)
            # resp and status both carry job id:
            if resp:
                status = client.status(resp['id'])
                while status['status'] not in ('DONE', 'FAILED'):
                    sleep(nap)  # seconds
                    status = client.status(resp['id'])
                    count += 1
                    if count >= max_iter:
                        break

                if status['status'] == 'DONE':
                    listing_dict = client.output(resp['id'])
                    listing = listing_dict['listing']
                    self._print_formatted_listing(listing)
                elif resp['status'] == 'FAILED':
                    print " Failed to obtain a listing for job %d " % (resp['id'],)
                else:
                    print "Timeout. Last status is %s for job id %d" % \
                          (status['status'], resp['id'])
            else:
                print " No such site: %s ?" % (args.site,)
        else:
            print "No token. Please login first"

    def sitelist(self, args):
        """
        Print list of available sites
        :param args: carry a user token
        :return: None
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            sites = client.list_sites()
            print '-' + 91 * '-' + '-'
            print '|{0:40}|{1:50}|'.format('site:', 'description:')
            print '|' + 91 * '-' + '|'
            for elem in sites:
                print '|{site_name:40s}|{site_desc:50s}|'.format(**elem)
        else:
            print "No token. Please login first"

    def _print_formatted_listing(self, listing):  # pylint: disable=no-self-use
        """
        Print formatted file listing.
        :param listing: listing (dictionary) to be pretty-printed a'la ls -l
        :return: None
        """
        size_len = len(str(max(d['size'] for d in listing)))
        links_len = max(d['nlinks'] for d in listing)
        uid_s = max(len(d['userid']) for d in listing)
        gid_s = max(len(d['groupid']) for d in listing)

        fmt = '{permissions:12s}{nlinks:>%dd} {userid:%ds} {groupid:%ds} ' \
              '{size:%dd} {datestamp:20s} {name:s}' % (links_len, uid_s, gid_s, size_len)
        # print fmt
        for elem in listing:
            print fmt.format(**dict(elem,
                                    datestamp=str(datetime.utcfromtimestamp(elem['datestamp']))))

    def status(self, args):
        """
        Get and print status of a job (task)
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        block = args.block
        job_id = int(args.job)
        if token:
            client = TransferClientFacade(token)
            self._status(job_id, client, block=block)
        else:
            print "No token. Please login first"

    def _status(self, job_id, client, block=False):

        status = client.status(job_id)
        sleep(self.__nap)  # seconds

        if block:
            while status['status'] not in ('DONE', 'FAILED'):
                sleep(self.__nap)  # seconds
                status = client.status(job_id)
                self.__count += 1
                if self.__count >= self.__max_iter:
                    print "Timeout .."
                    break
                print "(%2d) job id: %d status: %s " % (self.__count, job_id, status['status'])

        print "Job id: %d status: %s " % (job_id, status['status'])
        return status

    def remove(self, args):  # pylint: disable=no-self-use
        """
        Remove files at remote site
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            # remove None values, position args, func and token from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None and key not in ('func', 'site', 'token', 'block',
                                                               'config', 'verbosity')}
            response = client.remove(args.site, **accepted_args)  # max_tries, priority)
            self._status(response['id'], client, block=args.block)
        else:
            print "No token. Please login first"

    def copy(self, args):  # pylint: disable=no-self-use
        """
        Copy files between sites
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            src_site = args.src_site
            dst_site = args.dst_site
            # remove None values, position args, func and token from the kwargs:
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None
                             and key not in ('func', 'src_site', 'dst_site', 'token', 'block',
                                             'config', 'verbosity')}
            response = client.copy(src_site, dst_site, **accepted_args)
            self._status(response['id'], client, block=args.block)
        else:
            print "No token. Please login first"

    def log(self, args):
        """
        Get job log
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            job_id = int(args.job)
            client = TransferClientFacade(token)
            status = self._status(job_id, client, block=True)
            attempts = status['attempts']
            #
            if args.attempt == -1:
                print "Job log - last attempt %d" % (attempts,)
                log_listing = client.output(job_id)['log']
            else:
                log_listing = client.output(job_id, args.attempt)['log']
            print log_listing
        else:
            print "No token. Please login first"

    @staticmethod
    def _get_token(tokenfile):

        with open(os.path.expanduser(tokenfile)) as f:
            token = f.read()
            return token
