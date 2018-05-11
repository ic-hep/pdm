PDM Site Endpoint Installer Script
==================================

This script allows you to quickly install an endpoint and register it with a PDM central services.

The following instructions assume you are installing PDM in a standard system-wide configuration with config in /etc/pdm.

Requirements
------------
The installer has currently only been tested on CentOS7, the following packages should be installed before running the installer script:
 * python-requests
 * globus-gridftp-server-progs
 * globus-gridmap-verify-myproxy-callout
 * myproxy-server

Some of these packages required the EPEL repository to be enabled on the node. You can install them with the following commands:
```
yum -y install epel-release
yum -y install python-requests globus-gridftp-server-progs globus-gridmap-verify-myproxy-callout myproxy-server
```

Usage
-----

To install the services, just create the default config, review it and then run the installer:
```
./install_pdm.py -w
cat pdm.conf # Check things look OK
./install_pdm.py pdm.conf
```
Note that if you want to register the service with a central PDM instance, you should set the service details in the config file before running the last command. Once the services are install you should ensure inbound ports 49998-50999 are open on any firewalls between the server and the Internet.

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
