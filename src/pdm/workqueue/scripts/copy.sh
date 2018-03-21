#!/bin/sh

SRC_PATH="$1"
DST_PATH="$2"

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
source /cvmfs/grid.cern.ch/umd-c7ui-latest/etc/profile.d/setup-c7-ui-example.sh

gfal-copy -v "${SRC_PATH}" "${DST_PATH}"

