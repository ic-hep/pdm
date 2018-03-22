#!/bin/sh

LIST_PATH="$1"

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
source /cvmfs/grid.cern.ch/umd-c7ui-latest/etc/profile.d/setup-c7-ui-example.sh

gfal-ls -l "${LIST_PATH}"
