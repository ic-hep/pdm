"""
Define pdm subcommands and action functions for them:
Example usage: pdm register -e fred@flintstones.com -n Fred -s Flintstone
"""
import os
import errno
import stat
import logging
from pprint import pprint
from getpass import getpass
from time import sleep
from datetime import datetime
from pdm.userservicedesk.HRClient import HRClient
from pdm.userservicedesk.TransferClientFacade import TransferClientFacade
from pdm.site.SiteClient import SiteClient
from pdm.CLI.filemode import filemode
from pdm.userservicedesk.HRUtils import HRUtils
from pdm.framework.RESTClient import RESTException


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
        user_parser = subparsers.add_parser('register', help="Register a user with the PDM.")
        user_parser.add_argument('-e', '--email', type=str, required=True)
        user_parser.add_argument('-n', '--name', type=str)
        user_parser.add_argument('-s', '--surname', type=str)
        user_parser.set_defaults(func=self.register)
        # unregister
        user_parser = subparsers.add_parser('unregister', help="Delete a user from the PDM.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        # TODO due to a bug in the SiteService, commented out
        # user_parser.set_defaults(func=self.unregister)
        user_parser.set_defaults(func=self.not_implemented)
        # login
        user_parser = subparsers.add_parser('login', help="User login procedure.")
        user_parser.add_argument('email', nargs='?', type=str)
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help="optional token file location (default=~/.pdm/token)")

        user_parser.set_defaults(func=self.login)
        # logoff
        user_parser = subparsers.add_parser('logoff',
                                            help="User logoff procedure (deletes the token.)")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help="optional token file location (default=~/.pdm/token)")
        user_parser.set_defaults(func=self.logoff)
        # change password
        user_parser = subparsers.add_parser('passwd', help="Change user password.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.set_defaults(func=self.passwd)
        # whoami
        user_parser = subparsers.add_parser('whoami', help='List user data.')
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
        # rename
        user_parser = subparsers.add_parser('rename',
                                            help="rename a file. pdm rename site:path newpath")
        user_parser.add_argument('oldname', type=str, help="site:path_to_file to rename from")
        user_parser.add_argument('newname', type=str, help="path_to_file to rename to")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.add_argument('-b', '--block', action='store_true')
        user_parser.add_argument('-s', '--protocol', type=str, help='protocol')
        user_parser.set_defaults(func=self.rename)
        # mkdir
        user_parser = subparsers.add_parser('mkdir',
                                            help="create a new directory at a site.")
        user_parser.add_argument('site', type=str)
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('-m', '--max_tries', type=int)
        user_parser.add_argument('-p', '--priority', type=int)
        user_parser.add_argument('-b', '--block', action='store_true')
        user_parser.add_argument('-s', '--protocol', type=str, help='protocol')
        user_parser.set_defaults(func=self.mkdir)
        # status
        user_parser = subparsers.add_parser('status',
                                            help="get status of a job/task.")
        user_parser.add_argument('job', type=str, help="job id as obtained"
                                                       " from copy or remove.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        st_help = "periodically check the job status (up to %d times)" % (self.__max_iter,)
        user_parser.add_argument('-b', '--block', action='store_true', help=st_help)
        user_parser.set_defaults(func=self.status)
        # jobs
        user_parser = subparsers.add_parser('jobs',
                                            help="get status of user jobs")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('-l', '--long', action='store_true', help='Long listingjobs')
        user_parser.set_defaults(func=self.jobs)
        # log
        user_parser = subparsers.add_parser('log',
                                            help="get log of a job/task.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('job', type=int, help="job id as obtained"
                                                       " from copy, remove or list.")
        user_parser.set_defaults(func=self.log)
        # site list
        user_parser = subparsers.add_parser('sites',
                                            help="list available sites.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.set_defaults(func=self.sitelist)
        # get site information
        user_parser = subparsers.add_parser('site', help="list site information. "
                                                         "Includes user session info.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('name', type=str, help='site name')
        user_parser.set_defaults(func=self.get_site)
        # get user session information
        user_parser = subparsers.add_parser('session',
                                            help="get user session info for a site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('name', type=str, help='site name.')
        user_parser.set_defaults(func=self.get_session)
        # add a site
        user_parser = subparsers.add_parser('addsite', help="add a site to the PDM.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('site_name', type=str, help="site name")
        user_parser.add_argument('-d', '--def_path', type=str, default='/~',
                                 help="The default (starting) path to use at this site.")
        user_parser.add_argument('site_desc', type=str, help="site description.")
        user_parser.add_argument('-a', '--auth_uri', type=str, required=True,
                                 help='myproxy endpoint host:port')
        # auth_type == 1 : VOMS login
        user_parser.add_argument('-m', '--auth_type', type=int, default=0,
                                 help='The authentication mode for this site.')
        # user_parser.add_argument('-d', '--default_path', default ='/~',
        #                         help='The default path to use when connecting to this site')
        user_parser.add_argument('-e', '--endpoints', nargs='+', required=True,
                                 help='List of gridftp endpoints for this '
                                      'site in host:port format.')
        user_parser.add_argument('-p', '--public', action='store_true')
        user_parser.add_argument('-u', '--user_ca_cert', help='File holding the CA '
                                                              'used for user certificates')
        user_parser.add_argument('-s', '--service_ca_cert', help='File holding the CA '
                                                                 'used for site services')
        user_parser.set_defaults(func=self.add_site)
        # delete site
        user_parser = subparsers.add_parser('delsite', help="Delete a site from the PDM.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('name', type=str, help="site name")
        user_parser.set_defaults(func=self.del_site)
        # site logon
        user_parser = subparsers.add_parser('sitelogin', help="login to a site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('name', type=str, help="site name")
        user_parser.add_argument('-u', '--user', type=str, help="site specific username")
        user_parser.add_argument('-l', '--lifetime', type=int, default=36,
                                 help="The time (in hours) to create the credential for")
        user_parser.add_argument('-V', '--voms', type=str, default=None,
                                 help="the VO to use in the credential VOMS extension")

        user_parser.set_defaults(func=self.site_login)
        # site logoff
        user_parser = subparsers.add_parser('sitelogoff', help="logoff from a site.")
        user_parser.add_argument('-t', '--token', type=str, default='~/.pdm/token',
                                 help='optional token file location (default=~/.pdm/token)')
        user_parser.add_argument('name', type=str, help="site name")
        user_parser.set_defaults(func=self.site_logoff)
        # sub-command functions

    def not_implemented(self, args):
        """
        Not Implemented yet placeholder
        :param args:
        :return:
        """

        print " Operation not implemented yet ..."

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

    def unregister(self, args):
        """
        DEletes a user from the pdm user database. A user can only delete himself.
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = HRClient()
            client.set_token(token)
            client.del_user()
            os.remove(args.token)
            print "User unregistered. Token deleted."
        else:
            print "Unregister operation failed."

    def login(self, args):  # pylint: disable=no-self-use
        """
        User login function. Stores a token obtained from the server in a file.
        """
        token = UserCommand._get_token(args.token, check_validity=False)  # expired or not

        password = None
        if token:
            # username from token
            try:
                username = HRUtils.get_token_username_insecure(token)
                # a valid token should normally have a username, but to be safe:
                if username:
                    password = getpass(prompt=str(username) + "'s password: ")
            except ValueError as ve:
                # corrupted or empty token
                print ve.message

        if not password:
            # username from the command line
            if not args.email:
                args.email = raw_input("Please enter your email address: ")
                if not args.email:
                    print "No email provided. Exiting .."
                    exit(1)
            username = args.email
            password = getpass()

        client = HRClient()
        token = client.login(username, password)

        filename = os.path.expanduser(args.token)
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                print os.strerror(exc.errno)
                raise

        with open(filename, "w") as token_file:
            os.chmod(filename, 0o600)
            token_file.write(token)

        print "User {} logged in".format(username)

    def logoff(self, args):
        """
        User logoff. Just delete a token if present.
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token, check_validity=False)  # expired or not
        if token:
            # username from token
            username = ''
            try:
                username = HRUtils.get_token_username_insecure(token)
            except ValueError as ve:
                print ve.message
            finally:
                os.remove(os.path.expanduser(args.token))
                print "Token deleted, user {} is now logged off".format(str(username))
        else:
            print "No token found, no one to log off."

    def passwd(self, args):  # pylint: disable=no-self-use
        """ Change user password """

        token = UserCommand._get_token(args.token)
        if token:
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
        if token:
            client = HRClient()
            client.set_token(token)
            ret = client.get_user()
            UserCommand._print_formatted_user_info(ret)

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
            # remove None values, position args, func and token from the kwargs:
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
                    listing_output = client.output(resp['id'])[0]  # listing is element 0
                    listing_d_value = listing_output['listing']
                    root, listing = listing_d_value.items()[0]  # top root
                    self._print_formatted_listing(root, listing_d_value)
                elif resp['status'] == 'FAILED':
                    print " Failed to obtain a listing for job %d " % (resp['id'],)
                else:
                    print "Timeout. Last status is %s for job id %d" % \
                          (status['status'], resp['id'])
            elif isinstance(resp, list) and not resp:
                print "No such site: %s " % (args.site,)

    def sitelist(self, args):  # pylint disable-no-self-use
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
            print '-' + 91 * '-' + '-'

    def _print_formatted_listing(self, root, full_listing, level=0):  # pylint: disable=no-self-use
        """
        Print formatted file listing.
        :param listing: listing (a list dictionaries) to be pretty-printed a'la ls -l
        for a single level listing
        :return: None
        """
        # level = len(getouterframes(currentframe(1)))
        indent = 4

        listing = full_listing[root]

        size_len = len(str(max(d['st_size'] for d in listing)))
        links_len = max(d['st_nlink'] for d in listing)
        uid_s = len(str(max(d['st_uid'] for d in listing)))
        gid_s = len(str(max(d['st_gid'] for d in listing)))

        fmt = '{st_mode:12s} {st_nlink:>%dd} {st_uid:%dd} {st_gid:%dd} ' \
              '{st_size:%dd} {st_mtime:20s} {name:s}' % (links_len, uid_s, gid_s, size_len)

        for elem in listing:
            # filter ot bits we don't want:
            filtered_elem = {key: value for (key, value) in elem.iteritems() if
                             value is not None
                             and key not in ('st_atime', 'st_ctime', 'st_ino', 'st_dev')}
            print level * indent * ' ', fmt. \
                format(**dict(filtered_elem,
                              st_mode=filemode(elem['st_mode']),
                              st_mtime=str(datetime.utcfromtimestamp(elem['st_mtime']))))

            if stat.S_ISDIR(elem['st_mode']):
                if os.path.join(root, elem['name']) in full_listing:
                    self._print_formatted_listing(os.path.join(root, elem['name']),
                                                  full_listing, level=level + 1)

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

    def mkdir(self, args):
        """
        Create a new directory at a site.
        :param args: site - the new directory in a form site:path
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None and key not in ('func', 'site', 'token', 'block',
                                                               'config', 'verbosity')}
            response = client.mkdir(args.site, **accepted_args)  # max_tries, priority
            self._status(response['id'], client, block=args.block)

    def rename(self, args):
        """
        Rename a file at a site. It's like a copy, but with the source and destination
        site being the same.
        :param args: old name: site:path, new name: path.
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            accepted_args = {key: value for (key, value) in vars(args).iteritems() if
                             value is not None
                             and key not in ('func', 'token', 'block',
                                             'config', 'verbosity', 'oldname', 'newname')}
        response = client.rename(args.oldname, args.newname, **accepted_args)  # max_tries, priority
        self._status(response['id'], client, block=args.block)

    def log(self, args):
        """
        Get job log of a complete finished job. Use -v to get complete job info.
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            job_id = int(args.job)
            client = TransferClientFacade(token)
            status = self._status(job_id, client, block=True)
            for element in client.output(job_id):
                log_listing = element['log']
                if args.verbosity == logging.DEBUG:
                    pprint(element)
                else:
                    print log_listing

    def jobs(self, args):
        """
        Get user jobs' info
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            client = TransferClientFacade(token)
            jobs = client.jobs()
            UserCommand._print_formatted_jobs_info(jobs, long=args.long)

    def get_site(self, args):
        """
        Get site information from the Site Service
        :param args: parser arguments, in particular site name.
        :return: None
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_client, site_id = UserCommand._get_site_id(args.name, token)
            if site_id:
                try:
                    siteinfo = site_client.get_site(site_id)
                    UserCommand._print_formatted_siteinfo(siteinfo)
                    session_info = site_client.get_session_info(site_id)
                    UserCommand._print_formatted_session_info(session_info)
                except RESTException as res_ex:
                    print str(res_ex)
            else:
                print "site %s not found !" % (args.name,)

    def get_session(self, args):
        """
        Get user session information from the Site Service for a given site
        :param args: parser arguments, in particular site name
        :return: None
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_client, site_id = UserCommand._get_site_id(args.name, token)
            if site_id:
                session_info = site_client.get_session_info(site_id)
                UserCommand._print_formatted_session_info(session_info, attach=False)
            else:
                print "site %s not found !" % (args.name,)

    def add_site(self, args):
        """
        Add a site to the database
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_info = {key: value for (key, value) in vars(args).iteritems() if
                         value is not None and key not in ('func', 'token',
                                                           'config', 'verbosity',
                                                           'service_ca_cert', 'user_ca_cert')}
            if args.user_ca_cert:
                user_cert = UserCommand._get_cert(args.user_ca_cert)
                if user_cert:
                    site_info['user_ca_cert'] = user_cert
                else:
                    return None
            if args.service_ca_cert:
                service_cert = UserCommand._get_cert(args.service_ca_cert)
                if service_cert:
                    site_info['service_ca_cert'] = service_cert
                else:
                    return None
            print site_info
            site_client = SiteClient()
            site_client.set_token(token)
            site_client.add_site(site_info)
            return None

    def del_site(self, args):
        """
        Delete a site
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_client, site_id = UserCommand._get_site_id(args.name, token)
            if site_id:
                site_client.del_site(site_id)
            else:
                print "site %s not found !" % (args.name,)

    def site_login(self, args):
        """
        User site logon
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_client, site_id = UserCommand._get_site_id(args.name, token)
            if site_id:
                session_info = site_client.get_session_info(site_id)
                # determine the user
                if args.user:
                    user = args.user
                else:
                    user = session_info.get('username')
                    if not user:
                        user = raw_input("Please enter username for site {}:".format(args.name))

                password = getpass("User [{}], "
                                   "please enter password for site {}:".format(user, args.name))

                try:
                    site_client.logon(site_id, user, password,
                                      lifetime=args.lifetime, voms=args.voms)
                    print " user %s logged in at site %s (valid for %d hours)" \
                          % (user, args.name, args.lifetime)
                except RESTException as res_ex:
                    print str(res_ex)
            else:
                print "site %s not found !" % (args.name,)

    def site_logoff(self, args):
        """
        User site logoff
        :param args:
        :return:
        """
        token = UserCommand._get_token(args.token)
        if token:
            site_client, site_id = UserCommand._get_site_id(args.name, token)
            if site_id:
                try:
                    site_client.logoff(site_id)
                    print "Logged out from site %s" % (args.name,)
                except RESTException as res_ex:
                    print str(res_ex)
            else:
                print "site %s not found !" % (args.name,)

    @staticmethod
    def _get_site_id(name, token):
        site_client = SiteClient()
        site_client.set_token(token)
        sitelist = site_client.get_sites()
        site_id = [elem['site_id'] for elem in sitelist if elem['site_name'] == name]
        if site_id:
            return site_client, site_id[0]
        return site_client, None

    @staticmethod
    def _print_formatted_siteinfo(siteinfo):
        if not siteinfo:
            print " Nothing to print"
            return
        print '-' + 91 * '-' + '-'
        print '|{0:20}|{1:70}|'.format('site property:', 'value:')
        print '|' + 91 * '-' + '|'
        for key, value in siteinfo.iteritems():
            if key.endswith('cert'):
                continue
            if isinstance(value, list):
                for item in value:
                    print '|{0:20}|{1:70}|'.format(key, str(item))
                    key = ' '
            else:
                print '|{0:20}|{1:70}|'.format(key, str(value))
        print '-' + 91 * '-' + '-'

    @staticmethod
    def _print_formatted_session_info(usersession, attach=True):
        if not usersession:
            print " Nothing to print"
            return
        if not attach:
            print '-' + 91 * '-' + '-'
        print '|{0:20}|{1:70}|'.format('user session:', 'value:')
        print '|' + 91 * '-' + '|'
        for key, value in usersession.iteritems():
            print '|{0:20}|{1:70}|'.format(key, str(value))
        print '-' + 91 * '-' + '-'

    @staticmethod
    def _print_formatted_user_info(userinfo):
        if not userinfo:
            print " Nothing to print"
            return
        print '-' + 91 * '-' + '-'
        print '|{0:20}|{1:70}|'.format('user property:', 'value:')
        print '|' + 91 * '-' + '|'
        for key, value in userinfo.iteritems():
            print '|{0:20}|{1:70}|'.format(key, str(value))
        print '-' + 91 * '-' + '-'

    @staticmethod
    def _print_formatted_jobs_info(jobs, long=True):

        lkeys = [('id', 10), ('status', 10), ('type', 8), ('user_id', 20), ('timestamp', 20),
                 ('priority', 8), ('src_siteid', 12), ('src_filepath', 20), ('dst_siteid', 12),
                 ('dst_filepath', 20), ('protocol', 8), ('extra_opts', 30)]
        skeys = [('id', 10), ('status', 10), ('type', 8), ('src_siteid', 12), ('src_filepath', 60),
                 ('dst_siteid', 12), ('dst_filepath', 60)]
        if long:
            keys = lkeys
        else:
            keys = skeys

        fmt = '|'
        fmth = '|'
        nchars = len(keys) + 1
        for i, elem in enumerate(keys):
            fmt += '{%s:^%d}|' % elem
            fmth += '{%d:^%d}|' % (i, elem[1])
            nchars += elem[1]
        print nchars * '-'
        print fmth.format(*zip(*keys)[0])
        print nchars * '-'
        for job in jobs:
            print fmt.format(
                **dict(job, timestamp=job['timestamp'][:19],
                       src_filepath=None if job['src_filepath'] is None
                       else job['src_filepath'][-dict(keys)['src_filepath']:]
                       if len(job['src_filepath']) <= dict(keys)['src_filepath']
                       else '...' + job['src_filepath'][-dict(keys)['src_filepath'] + 3:],
                       dst_filepath=None if job['dst_filepath'] is None
                       else job['dst_filepath'][-dict(keys)['dst_filepath']:]
                       if len(job['dst_filepath']) <= dict(keys)['dst_filepath']
                       else '...' + job['dst_filepath'][-dict(keys)['dst_filepath'] + 3:]))
        print nchars * '-'

    @staticmethod
    def _get_token(tokenfile, check_validity=True):
        """
        Get a token from a file, expired or not.
        :param tokenfile: file containing a token
        :return: token or None if tokenfile not present or empty
        """
        if os.path.isfile(os.path.expanduser(tokenfile)):
            with open(os.path.expanduser(tokenfile)) as token_file:
                token = token_file.read()
                if not token:
                    print "No token at requested location. Please login first."
                    return None
                if check_validity:
                    if HRUtils.is_token_expired_insecure(token):
                        print "Token expired. Please log in again."
                        return None
                return token
        if check_validity:
            print "No token at requested location. Please login first."
        return None

    @staticmethod
    def _get_cert(certfile):
        if os.path.isfile(certfile):
            with open(os.path.expanduser(certfile)) as cert_file:
                cert = cert_file.read()
                if not cert:
                    print "No certificate at requested location. Please check and try again."
                return cert
        print "%s does not exist or it is not a file. Please check and try again." % (certfile,)
        return None
