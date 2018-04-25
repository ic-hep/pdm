#!/usr/bin/env python
""" Default config file templates for site services. """

INSTALLER_CONF = """\
# PDM Node Config
# This file configures how PDM is deployed at this site.

[general]
#conf_dir = /etc/pdm
#ca_dir = /etc/pdm/CA
#hostname = <auto>
#gridftpd_path = <auto>
#myproxy_path = <auto>

[system]
#service_url = <none>
#sitename = <none>
#sitedesc = <none>
#public = False

[myproxy]
#port = 49998
#cert_hours = 72

[gridftp]
#port = 49999
#low_port = 50000
#high_port = 50999
"""

MYPROXY_CONF = """\
pam "required"
pam_id "login"
certificate_issuer_cert %(CA_DIR)s/user/ca_crt.pem
certificate_issuer_key %(CA_DIR)s/user/ca_key.pem
certificate_serialfile %(CA_DIR)s/user/serial
certificate_out_dir %(CA_DIR)s/user/certs
certificate_mapapp %(CA_DIR)s/user/mapper
max_cert_lifetime %(CERT_HOURS)u
cert_dir %(CA_DIR)s/certificates
disable_usage_stats 1
"""

MYPROXY_SYSTEMD = """\
[Unit]
Description=MyProxy service for PDM
After=network.target

[Service]
Type=forking
User=root
Environment=X509_USER_CERT=%(CA_DIR)s/host/certs/%(HOST)s.crt
Environment=X509_USER_KEY=%(CA_DIR)s/host/keys/%(HOST)s.key
Environment=X509_CERT_DIR=%(CA_DIR)s/certificates
ExecStart=%(MYPROXY_BIN)s -c %(CONF_DIR)s/myproxy.conf -p %(MYPROXY_PORT)u -P /var/run/myproxy-pdm.pid
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/var/run/myproxy-pdm.pid

[Install]
WantedBy=multi-user.target
"""

GRIDFTP_CONF = """\
$X509_CERT_DIR "%(CA_DIR)s/certificates"
$GLOBUS_MYPROXY_CA_CERT "%(CA_DIR)s/user/ca_crt.pem"
$GSI_AUTHZ_CONF "%(CONF_DIR)s/myproxy_authz.conf"
$GLOBUS_TCP_PORT_RANGE %(GRIDFTP_LOPORT)u,%(GRIDFTP_HIPORT)u
port %(GRIDFTP_PORT)u
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
Environment=X509_USER_CERT=%(CA_DIR)s/host/certs/%(HOST)s.crt
Environment=X509_USER_KEY=%(CA_DIR)s/host/keys/%(HOST)s.key
Environment=X509_CERT_DIR=%(CA_DIR)s/certificates
ExecStart=%(GRIDFTP_BIN)s -no-detach -config-base-path %(CONF_DIR)s -c %(CONF_DIR)s/gridftpd.conf
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
"""
