Server Installation
===================

These instructions are for installing the core service and website. They
currently refer to the development version.

Prerequisites
-------------

This guide assumes you are installing on a CentOS7 compatible machine and have
root access via sudo for installations.

Ensure you have the Extra Packages for Enterprise Linux (EPEL) repository and
the CentOS extras repository enabled::

    sudo yum -y install epel-release
    sudo yum-config-manager --enable extras

Next install all of the required dependencies::

    sudo yum -y install git python-twisted-web python-flask python2-flask-sqlalchemy python-requests python-enum34
    sudo yum -y install myproxy myproxy-voms gfal2 gfal2-python gfal2-plugin-gridftp

Ensure that ports 5443 - 5446 are open on the firewall::

    <system specific, write firewalld docs here>

Create a user to run the PDM processes and switch to that account::

    useradd -m pdm
    passwd -l pdm
    su - pdm

All further commands should be run as the pdm user unless otherwise specified.

Installing PDM server
---------------------

Get the source code from the PDM github page::

    git clone https://github.com/ic-hep/pdm.git
    cd pdm

Configure the local CA::

    cd etc
    sed -e "s/localhost/`hostname`/" -i build_ca.sh
    ./build_ca.sh
    cd ..

Prepare the config file and start the server::

    # TODO: Update system.auth too.
    # TODO: CA certs needs for worker.
    sed -e "s/localhost/`hostname`/" -i etc/system.server.conf
    ./bin/test_server.py -d -t etc/system.server.conf &
    sed -e "s/localhost/`hostname`/" -i etc/system.worker.conf
    ./bin/start_worker.py -dvv etc/system.worker.conf &

