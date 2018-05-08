#!/usr/bin/env python
""" A module for myproxy functions. """

class MyProxyUtils(object):
    """ Util functions for myproxy. """

    @staticmethod
    def logon(myproxy_server, username, password,
              ca_certs=None, voms=None, hours=12):
        # TODO: Implement this
        hostname, port = myproxy_server.split(':', 1)
        myproxy_opts = [ '-s', hostname,     # MyProxy server name
                         '-p', '%u' % port,  # MyProxy port number
                         '-l', username,     # Username at remote site
                         '-t', '%u' % hours, # Lifetime in hours
                         '-o', '-',          # Proxy on stdout
                         '-q',               # Quiet (output only on error)
                         '-S',               # Password on stdin
                       ]
        if voms:
            myproxy_opts.extend(['-m', voms])
        if ca_certs:
            pass
        print myproxy_opts
        pass

    @staticmethod
    def load_voms_list(vomsdir):
        # TODO: Implement this
        return []

    @staticmethod
    def build_ca_dir(ca_list, clear_env=False):
        # TODO: Implement this
        pass
