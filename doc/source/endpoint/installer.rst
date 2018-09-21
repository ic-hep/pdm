How to install an Endpoint
=========================
The following instructions assume you are installing PDM in a standard
system-wide configuration with the configurations files located in /etc/pdm.

Requirements
------------

* The account that is used for installation must be registered with the instance you wish to register the endpoint with.

* The installer has currently only been tested on CentOS7.
  
* The following packages should be installed before running the installer script:

   - python-requests
   - globus-gridftp-server-progs
   - globus-gridmap-verify-myproxy-callout
   - myproxy-server
   - wget

* Some of these packages required the EPEL repository to be enabled on the
  node. You can install them with the following commands:
  ::
    yum -y install epel-release
    yum -y install python-requests globus-gridftp-server-progs globus-gridmap-verify-myproxy-callout myproxy-server wget
    
*  System clock must be set correctly (chrony, ntpd).

Install scripts
-----

* Download the configuration scripts:
  ::
    wget https://raw.githubusercontent.com/ic-hep/pdm/master/src/pdm/installer/install_pdm.py
    wget https://raw.githubusercontent.com/ic-hep/pdm/master/src/pdm/installer/build_pdm_ca.sh
    chmod u+x install_pdm.py build_pdm_ca.sh

* System hostname must be set to a publicly resolvable hostname, otherwise use IP address instead of hostname for configuration.

    
Configuration and Installation
-----
To install the services, just create the default config, review it and then run
the installer:
::
  ./install_pdm.py -w
  cat pdm.conf # Check things look OK
  ./install_pdm.py pdm.conf

Note that if you want to register the service with a central PDM instance, you
should set the service details in the config file before running the last
command. Once the services are installed you should ensure inbound ports
49998-50999 are open on any firewalls between the server and the Internet.

Uninstalling
------------
(Not tested yet.)

Stop the services if they are running & disable them:
::
  systemctl stop pdm-gridftpd.service pdm-myproxy.service
  systemctl disable pdm-gridftpd.service pdm-myproxy.service


Remove the systemd unit file and reload systemd:
::
  rm -f /etc/systemd/system/pdm-{gridftpd,myproxy}.service
  systemctl daemon-reload
  
Finally, just remove the configuration directory.
::
  rm -Rf /etc/pdm
