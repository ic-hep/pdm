#!/bin/sh

source /cvmfs/grid.cern.ch/umd-c7ui-latest/etc/profile.d/setup-c7-ui-example.sh

gfal-copy -v "${SRC_PATH}" "${DST_PATH}"
