Using PDM with Grid storage
======================

The PDM software can be used to transfer files into or out of Grid storage as used by the GridPP collaboration and the WLCG. Its use requires the possession of an X509 certificate and membership of appropriate Virtual Organisations. Grid endpoints need to be registered with the PDM central service before they can be used, please see below for instructions as to how to do this. We will use the GridPP Virtual Organisation and Imperial College HEP Group grid site (UKI-LT2-IC-HEP) in an example. The first step is to upload a proxy generated from the certificate to a suitable myproxy server. 

::

  voms-proxy-init --voms gridpp
  myproxy-store -s myproxy.grid.hep.ph.ic.ac.uk
  myproxy-info -s myproxy.grid.hep.ph.ic.ac.uk

Now it should be possible to authenticate with the grid endpoint via the PDM webui using your username (the one used when creating the proxy) and grid certificate password and selecting the relevant VO from the drop-down list. You will find yourself at the top of the VO namespace, in this case /pnfs/hep.ph.ic.ac.uk/data. Change into the VO directory gridpp and then pdm-demo for the example by double clicking on the directory name. It should now be possible to transfer a file or directory from another standard PDM endpoint into this directory in the usual way and visa versa.

It is also possible to transfer files between two Grid storage endpoints, provided they have both been registered with the central PDM service. 

Adding a site to the central service
---------------------------------

In order to add a grid site storage element to a PDM central service you will need to make use of the PDM command line interface. Check out the latest copy from the git repository:

::

  git clone https://github.com/ic-hep/pdm
  cd pdm   

now download a copy of the service details:

::

  wget --no-check-certificate https://pdm00.grid.hep.ph.ic.ac.uk:5445/site/api/v1.0/service

edit the file ‘service’ so it only has the certificate in and no /n. Make a certs directory and move it there, renaming it to CA.crt

::

  mkdir  etc/certs
  mv service etc/certs/CA.crt

edit etc/system.client.conf to replace localhost with the name of the central PDM server (pdm00.grid.hep.ph.ic.ac.uk in this case):

::

  # Main application configuration file

  [endpoints]
  users = "https://pdm00.grid.hep.ph.ic.ac.uk:5444/users/api/v1.0"
  site = "https://pdm00.grid.hep.ph.ic.ac.uk:5445/site/api/v1.0"
  workqueue = "https://pdm00.grid.hep.ph.ic.ac.uk:5446/workqueue/api/v1.0"

  [client]
  timeout = 30
  cafile = "certs/CA.crt"

Now login to the central service and add the new site (UKI-LT2-Brunel):

:: 

  ./bin/pdm login 
  ./bin/pdm addsite -d /dpm/brunel.ac.uk/home -a myproxy.grid.hep.ph.ic.ac.uk:7512 -e dc2-grid-64.brunel.ac.uk:2811 -m 1 UKI-LT2-Brunel 'Brunel University GridPP Site'

The site should now appear in the drop-down list of sites.

