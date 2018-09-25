PDM Site Endpoint Installer Script
==================================

This script allows you to quickly install an endpoint and register it with a PDM central service. 

The following instructions assume you are installing PDM in a standard system-wide configuration with config in /etc/pdm.

Requirements
------------
You (the installer) must be registered with the central instance you wish to register the endpoint with.

The installer has currently only been tested on CentOS7, the following packages should be installed before running the installer script:
 * python-requests
 * globus-gridftp-server-progs
 * globus-gridmap-verify-myproxy-callout
 * myproxy-server
 * wget

Some of these packages require the EPEL repository to be enabled on the node. You can install them with the following commands:
```
yum -y install epel-release
yum -y install python-requests globus-gridftp-server-progs globus-gridmap-verify-myproxy-callout myproxy-server wget
```

Getting started
----------
* System hostname must be set to a publicly resolvable hostname, otherwise use IP address instead of hostname for configuration.
* System clock must be set correctly (chrony, ntpd).
* Download the configuration scripts:
```
wget https://raw.githubusercontent.com/ic-hep/pdm/master/src/pdm/installer/install_pdm.py
wget https://raw.githubusercontent.com/ic-hep/pdm/master/src/pdm/installer/build_pdm_ca.sh
chmod u+x install_pdm.py build_pdm_ca.sh
```

Usage
-----

Create the default config and review it:
```
./install_pdm.py -w
cat pdm.conf 
```
You may wish to leave many of the default settings unchanged; edit site specific settings by uncommenting them. For example if you want to register the service with a central PDM instance, you should set the service details in the config file. Here is a simple example:
```
# PDM Node Config
# This file configures how PDM is deployed at this site.
# All entries set to <none> must be specified.

[DEFAULT]
#conf_dir = /etc/pdm
#ca_dir = /etc/pdm/CA
hostname = xxx.xxx.xxx.xxx
#gridftpd_path = <auto>
#myproxy_path = <auto>

# specify central server, e.g. 
# https://example.grid.hep.ph.ic.ac.uk:5445/site/api/v1.0
service_url = https://example.grid.hep.ph.ic.ac.uk:5445/site/api/v1.0

# Specify your site name, e.g. 
# IMPERIAL-HEP
sitename = test-pdm02

# Site description, e.g. "Imperial Test Endpoint"
sitedesc = test pdm 02

# Set this to True if Endpoint should be visible to others
#public = False

#myproxy_port = 49998
#cert_hours = 72

#gridftp_port = 49999
#low_port = 50000
#high_port = 50999

```
When you are happy with the configuration run the installer:
```
./install_pdm.py pdm.conf
```
Once the services are installed you should ensure inbound ports 49998-50999 are open on any firewalls between the server and the Internet.

Uninstalling
------------
Stop the services if they are running & disable them:
```
systemctl stop pdm-gridftpd.service pdm-myproxy.service
systemctl disable pdm-gridftpd.service pdm-myproxy.service
```

Remove the systemd unit file and reload systemd:
```
rm -f /etc/systemd/system/pdm-{gridftpd,myproxy}.service
systemctl daemon-reload
```

Finally, just remove the configuration directory.
```
rm -Rf /etc/pdm
```
