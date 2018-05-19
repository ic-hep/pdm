#!/usr/bin/env python
""" A module for myproxy functions. """

import os
import copy
import shutil
from subprocess import Popen, PIPE
from pdm.utils.X509 import X509Utils

class MyProxyUtils(object):
    """ Util functions for myproxy. """

    # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
    @staticmethod
    def logon(myproxy_server, username, password,
              ca_certs=None, voms=None, hours=12,
              myproxy_bin=None, vomses=None, log=None):
        """ Runs the myproxy-logon command with the various parameters.
            myproxy_server - Server to contact in hostname:port format.
            username - Username to use a remote site.
            password - Password to use at remote site.
            ca_certs - Either None to use the system CA,
                       A string to use as the path to a CA dir,
                       Or a list of strings containing individual PEM files
                       to use as the CA(s).
            voms - An optional VO name to request a VOMS extension for.
            hours - Number of hours to request as the lifetime of the new
                    credential.
            myproxy_bin - Location of the myproxy-logon executable to use,
                          if unset, $PATH will be searched instead.
            vomses - Location of the vomses directory to use if issuing a VOMS
                     proxy. Inherited from parent process otherwise.
            log - Optional logger object to write debug information to.
            Returns a string with the new credential PEM. Raises a
            RuntimeError exception if anything goes wrong.
        """
        hostname, port = myproxy_server.split(':', 1)
        myproxy_opts = ['myproxy-logon',    # Exectuable name
                        '-s', hostname,     # MyProxy server name
                        '-p', '%s' % port,  # MyProxy port number
                        '-l', username,     # Username at remote site
                        '-t', '%u' % hours, # Lifetime in hours
                        '-o', '-',          # Proxy on stdout
                        '-q',               # Quiet (output only on error)
                        '-S',               # Password on stdin
                       ]
        if myproxy_bin:
            myproxy_opts[0] = myproxy_bin
        if voms:
            myproxy_opts.extend(['-m', voms])
        env = copy.deepcopy(os.environ)
        ca_dir = None
        if ca_certs:
            if isinstance(ca_certs, str):
                # CA certs is a path to a cert dir
                env["X509_CERT_DIR"] = ca_certs
            else:
                # ca_certs is a list of PEM strings
                ca_dir = X509Utils.add_ca_to_dir(ca_certs, None)
                env["X509_CERT_DIR"] = ca_dir
        if vomses:
            env["X509_VOMS_DIR"] = vomses
        # Actually run the command
        if log:
            log.debug("Running myproxy-logon with: %s", " ".join(myproxy_opts))
        proc = Popen(myproxy_opts, shell=False, stdin=PIPE, stdout=PIPE,
                     stderr=PIPE, env=env)
        try:
            stdout, stderr = proc.communicate('%s\n' % password)
        except Exception as err:
            if log:
                log.warn("myproxy-logon command failed: %s", str(err))
            raise RuntimeError("Logon error: Failed to run myproxy-logon")
        finally:
            # Make sure we tidy up the CA dir if we created one
            if ca_dir:
                shutil.rmtree(ca_dir, ignore_errors=True)
        # Check the return code
        if proc.returncode != 0:
            # Command failed, attempt to infer the reason
            error_str = "Unknown myproxy failure"
            if "invalid password" in stderr:
                error_str = "Incorrect password"
            elif "Unable to connect to" in stderr:
                error_str = "Connection error"
            elif "No credentials exist for username" in stderr:
                error_str = "Unrecognised user"
            elif "Error in service module" in stderr:
                error_str = "Unrecognised user/config error"
            if log:
                log.warn("myproxy-logon command failed with code %u (%s)",
                         proc.returncode, error_str)
                log.debug("myproxy-logon stderr: %s", stderr)
            raise RuntimeError("Logon error: %s" % error_str)
        return stdout # Proxy is just a string on stdout

    @staticmethod
    def load_voms_list(vomsdir):
        """ Loads a list of supported VOs from a vomses directory. """
        vo_list = []
        for filename in os.listdir(vomsdir):
            fullpath = os.path.join(vomsdir, filename)
            try:
                with open(fullpath, "r") as vo_file:
                    vo_line = vo_file.readline()
                    vo_name, _ = vo_line.split(" ", 1)
                    vo_name = vo_name.replace('"', '')
                    vo_list.append(vo_name)
            except Exception:
                continue # Unreadable file => Ignore it
        # Return a de-duplicated & sorted list
        vo_list = list(set(vo_list))
        vo_list.sort()
        return vo_list
