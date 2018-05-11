#!/usr/bin/env python
""" An installer script for PDM sites.
"""

import os
import sys
import socket
import ConfigParser
from subprocess import Popen, PIPE
try:
    import requests
except ImportError as err:
    print "ERROR: Could not find python requests library (%s)." % str(err)
    print "Please install this with the standard package manager."
    print "On RHEL7 and similar, the required (root) command is:"
    print "  yum install python-requests"
    print ""
    sys.exit(1)

# Program default options/config
# Updated when the config is loaded
OPTS = {
    "conf_dir": "/etc/pdm",
    "ca_dir": "/etc/pdm/CA",
    "public": False,
    "myproxy_port": 49998,
    "cert_hours": 72,
    "gridftp_port": 49999,
    "gridftp_low": 50000,
    "gridftp_high": 50999,
}
# A path for systemd unit files
SYSTEMD_UNIT_PATH = "/etc/systemd/system"


def usage():
    """ Print the program usage information
        and exit.
    """
    print "Usage: install_pdm.py <config>"
    print "       install_pdm.py -w"
    print ""
    print "Installs a PDM client endpoint when provided with a config file."
    print "The -w option will write a template config file, 'pdm.conf' in"
    print "the current directory."
    print ""
    sys.exit(1)

def write_def_config():
    """ Write the default config file and exit. """
    CONF_FILE = "pdm.conf"
    if os.path.exists(CONF_FILE):
        print "Config file %s already exists! Not overwriting..." % CONF_FILE
        sys.exit(1)
    with open(CONF_FILE, "w") as conf_fd:
        conf_fd.write(INSTALLER_CONF % OPTS)
    print "Default config written to '%s'." % CONF_FILE
    sys.exit(1)

def read_config(fname):
    """ Read the config file 'fname' and update the OPTS dictionary with the
        new values.
    """
    print "[*] Loading config file..."
    conf = ConfigParser.ConfigParser()
    # All options are optional at this point
    for opt in ('conf_dir', 'ca_dir', 'hostname', 'gridftpd_path',
                'myproxy_path', 'service_url', 'sitename',
                'sitedesc'):
        if conf.has_option('DEFAULT', opt):
            OPTS[opt] = conf.get('DEFAULT', opt)
    for opt in ('myproxy_port', 'cert_hours',
                'gridpftp_port', 'gridftp_low', 'gridftp_high'):
        if conf.has_option('DEFAULT', opt):
            OPTS[opt] = conf.getint('DEFAULT', opt)
    if conf.has_option('DEFAULT', 'public'):
        OPTS['public'] = conf.getboolean('DEFAULT', 'public')
    # Detect the auto options if they aren't set
    if 'hostname' not in OPTS:
        hostname = socket.gethostname()
        OPTS['hostname'] = hostname
        print "  Note: Hostname not set in config. Using: %s" % hostname
    # Tidy up
    OPTS['conf_dir'] = os.path.abspath(OPTS['conf_dir'])
    OPTS['ca_dir'] = os.path.abspath(OPTS['ca_dir'])
    print "  Using conf dir: %s" % OPTS['conf_dir']
    print "          ca dir: %s" % OPTS['ca_dir']

def find_bin_helper(prog_name, conf_name, include_loc=False):
    """ Search for prog_name using the following locations:
         - Manually set option in config.
         - $PATH
         - if include_loc is True, in the directory this script is in.
        Prints the location where the binary was found (with message)
        on to stdout.
        Exits with a suitable message if the command isn't found.
        returns the location of the bin and puts it into OPTS
    """
    if conf_name in OPTS:
        # User set path, only use that if it's there
        bin_path = OPTS[conf_name]
        if not os.access(bin_path, os.X_OK):
           print "ERROR: Configured path '%s' for '%s' is not found or exectuable." % \
                 (bin_path, conf_name)
           print "Please review your config file and try again."
           sys.exit(1)
        return bin_path
    # Search the PATH
    paths = os.environ['PATH'].split(':')
    if include_loc:
        my_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        paths.append(my_path)
    for path in paths:
        bin_path = os.path.join(path, prog_name)
        if os.access(bin_path, os.X_OK):
            # Found the binary...
            OPTS[conf_name] = bin_path
            return bin_path
    # Binary wasn't found
    print "ERROR: Failed to find '%s' binary. Please ensure you have all" % prog_name
    print "required packages installed or set the path manually in the"
    print "config file if it isn't in a standard location."
    sys.exit(1)

def find_bins():
    """ Find all of the required binaries on $PATH if they weren't specified
        in the config file.
    """
    print "[*] Locating program/daemon files..."
    res = find_bin_helper("globus-gridftp-server", "gridftpd_path")
    print "  Found globus-gridftp-server at '%s'." % res
    res = find_bin_helper("myproxy-server", "myproxy_path")
    print "  Found myproxy-server at '%s'." % res
    res = find_bin_helper("build_pdm_ca.sh", "ca_builder", True)
    print "  Found build_pdm_ca.sh helper script at '%s'." % res

def check_conf():
    """ Check that the config has all required options.
    """
    print "[*] Verifying config options..."
    for opt in ('conf_dir', 'ca_dir', 'hostname', 'gridftpd_path',
                'myproxy_path', 'myproxy_port', 'cert_hours',
                'gridftp_port', 'gridftp_low', 'gridftp_high'):
        if not opt in OPTS:
            print "ERROR: Config option '%s' was not found." % opt
            print "Please review your config file and try again."
            sys.exit(1)
    # Check optional sections
    if 'service_url' in OPTS:
        for opt in ('sitename', 'sitedesc', 'public'):
            if not opt in OPTS:
                print "ERROR: service_url was set to enable registration,"
                print "however option '%s' was missing from the config file." % opt
                print "Please review your config file and try again."
                sys.exit(1)

def create_ca_dir():
    """ Create system CA files.
    """
    print "[*] Creating CA files..."
    print "  This may take some time, please be patient..."
    # Just run the CA helper
    cmd_args = [OPTS['ca_builder'], OPTS['ca_dir'], OPTS['hostname']]
    proc = Popen(cmd_args, stdout=PIPE, stderr=PIPE, shell=False)
    stdout, stderr = proc.communicate()
    if proc.returncode:
       print "ERROR: Building CAs failed, stderr:"
       print stderr
       print "stdout:"
       print stdout
       sys.exit(1)

def install_services():
    """ Create the config files for all of the PDM services.
    """
    print "[*] Creating PDM configuration files..."
    for fname, ftemp in (('gridftpd.conf', GRIDFTP_CONF),
                         ('myproxy.conf', MYPROXY_CONF),
                         ('myproxy_authz.conf', GRIDFTP_AUTH_CONF)):
        full_path = os.path.join(OPTS['conf_dir'], fname)
        try:
            with open(full_path, 'w') as conf_fd:
                conf_fd.write(ftemp % OPTS)
        except Exception as err:
           print "ERROR: Failed to write config '%s' (%s)." % (full_path, str(err))
           sys.exit(1)

def register_systemd():
    """ Create the systemd config file to start the relevant services
        at system boot.
    """
    print "[*] Creating systemd unit files..."
    for fname, ftemp in (('pdm-gridftpd.service' , GRIDFTP_SYSTEMD),
                         ('pdm-myproxy.service', MYPROXY_SYSTEMD)):
        full_path = os.path.join(SYSTEMD_UNIT_PATH, fname)
        try:
            with open(full_path, 'w') as conf_fd:
                conf_fd.write(ftemp % OPTS)
        except Exception as err:
           print "ERROR: Failed to write unit file '%s' (%s)." % (full_path, str(err))
           sys.exit(1)
    print "  Reloading systemd to pick up new files..."
    proc = Popen(['systemctl', 'daemon-reload'], stdout=PIPE, stderr=PIPE, shell=False)
    proc.communicate()

def start_services():
    """ Start & check the daemons.
    """
    print "[*] Starting services..."
    for service_name in ('pdm-gridftpd.service', 'pdm-myproxy.service'):
        print "    Starting & enabling %s." % service_name
        for cmd in (['systemctl', '-q', 'start', service_name],
                    ['systemctl', '-q', 'enable', service_name]):
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=False)
            stdout, stderr = proc.communicate()
            if proc.returncode:
                print "ERROR: Failed to run '%s':" % " ".join(cmd)
                print stdout, stderr
                print "For furter details, try running:"
                print "  systemctl status %s" % service_name
                print "and:"
                print "  journalctl -u %s" % service_name
                sys.exit(1)

def register_service():
    """ Register this endpoint with the central system,
        if service_url is set.
    """
    if 'service_url' not in OPTS:
        return # Registration not configured, skip this step
    print "[*] Registering with central server..."
    # TODO: Write central registration code
    pass

def main():
    """ Main script entry point. """
    if os.getuid() != 0:
       print "ERROR: This program required root access."
       sys.exit(1)
    if len(sys.argv) != 2:
        usage()
    if sys.argv[1] in ('-h', '-?', '--help'):
        usage()
    if sys.argv[1] == '-w':
        write_def_config()
    conf_file = sys.argv[1]
    if not os.path.isfile(conf_file):
        print "Could not find config file '%s'." % conf_file
        sys.exit(1)
    read_config(conf_file)
    find_bins()
    check_conf()
    create_ca_dir()
    install_services()
    register_systemd()
    start_services()
    register_service()
    print "Congratulations: Configuration finished successfully."


# The following are all of the config file templates
INSTALLER_CONF = """\
# PDM Node Config
# This file configures how PDM is deployed at this site.

[DEFAULT]
#conf_dir = %(conf_dir)s
#ca_dir = %(ca_dir)s
#hostname = <auto>
#gridftpd_path = <auto>
#myproxy_path = <auto>

#service_url = <none>
#sitename = <none>
#sitedesc = <none>
#public = %(public)s

#myproxy_port = %(myproxy_port)u
#cert_hours = %(cert_hours)u

#gridftp_port = %(gridftp_port)u
#low_port = %(gridftp_low)u
#high_port = %(gridftp_high)u
"""

MYPROXY_CONF = """\
pam "required"
pam_id "login"
certificate_issuer_cert %(ca_dir)s/user/ca_crt.pem
certificate_issuer_key %(ca_dir)s/user/ca_key.pem
certificate_serialfile %(ca_dir)s/user/serial
certificate_out_dir %(ca_dir)s/user/certs
certificate_mapapp %(ca_dir)s/user/mapper
max_cert_lifetime %(cert_hours)u
cert_dir %(ca_dir)s/certificates
disable_usage_stats 1
"""

MYPROXY_SYSTEMD = """\
[Unit]
Description=MyProxy service for PDM
After=network.target

[Service]
Type=forking
User=root
Environment=X509_USER_CERT=%(ca_dir)s/host/certs/%(hostname)s.crt
Environment=X509_USER_KEY=%(ca_dir)s/host/keys/%(hostname)s.key
Environment=X509_CERT_DIR=%(ca_dir)s/certificates
ExecStart=%(myproxy_path)s -c %(conf_dir)s/myproxy.conf -p %(myproxy_port)u -P /var/run/myproxy-pdm.pid
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/var/run/myproxy-pdm.pid

[Install]
WantedBy=multi-user.target
"""

GRIDFTP_CONF = """\
$X509_CERT_DIR "%(ca_dir)s/certificates"
$GLOBUS_MYPROXY_CA_CERT "%(ca_dir)s/user/ca_crt.pem"
$GSI_AUTHZ_CONF "%(conf_dir)s/myproxy_authz.conf"
$GLOBUS_TCP_PORT_RANGE %(gridftp_low)u,%(gridftp_high)u
port %(gridftp_port)u
log_single /var/log/gridftpd-pdm.log
log_level ERROR,INFO
disable_usage_stats 1
"""

GRIDFTP_AUTH_CONF = """\
globus_mapping libglobus_gridmap_verify_myproxy_callout globus_gridmap_verify_myproxy_callout
"""

GRIDFTP_SYSTEMD = """\
[Unit]
Description=GridFTP service for PDM
After=network.target

[Service]
Type=simple
User=root
Environment=X509_USER_CERT=%(ca_dir)s/host/certs/%(hostname)s.crt
Environment=X509_USER_KEY=%(ca_dir)s/host/keys/%(hostname)s.key
Environment=X509_CERT_DIR=%(ca_dir)s/certificates
ExecStart=%(gridftpd_path)s -no-detach -config-base-path %(conf_dir)s -c %(conf_dir)s/gridftpd.conf
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    main()
