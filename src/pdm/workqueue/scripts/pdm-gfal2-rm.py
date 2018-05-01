#!/usr/bin/env python
import os
import sys
import argparse
import json
import logging
import gfal2

_logger = logging.getLogger(__name__)


def pdm_gfal_rm(remove_json, verbosity=logging.INFO):
    """
    Remove files and directories.
    """
    _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    ctx = gfal2.creat_context()

    rmdict = json.loads(remove_json)
    result = []

    # files
    file_list = rmdict.get('files', [])
    for elem in file_list:
        try:
            res = ctx.unlink(str(elem))
            result.append({'Code': res, 'Reason': 'OK'})
        except gfal2.GError as ge:
            result.append({'Code': 1, 'Reason': str(ge)})
            _logger.error(str(ge))

    # directories
    dir_list = rmdict.get('dirs', [])
    for elem in dir_list:
        try:
            ctx.rmdir(elem)
            result.append({'Code': res, 'Reason': 'OK'})
        except gfal2.GError as ge:
            result.append({'Code': 1, 'Reason': str(ge)})
            _logger.error(str(ge))

    return result


def main():
    """
    Gfal2 rm wrapper.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("rmdict", type=str, help="rmlist: {'files':[file1, file2 ...],"
                                                 " 'dirs':[dir1, dir2, ...]}")
    parser.add_argument("-v", "--verbosity", action='store_const', const=logging.DEBUG,
                        default=logging.INFO, help="verbosity, INFO, if omitted")

    args = parser.parse_args()

    print json.dumps(pdm_gfal_rm(args.rmdict, args.verbosity))


if __name__ == "__main__":
    main()
