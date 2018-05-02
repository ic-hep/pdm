#!/usr/bin/env python
"""
gfal2 based file remover.
"""
import sys
import argparse
import json
import logging
import gfal2

_logger = logging.getLogger(__name__)


def pdm_gfal_rm(rmdict, verbosity=logging.INFO):
    """
    Remove files and directories. Print json string immediately after a file is removed.
    """
    _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    ctx = gfal2.creat_context()

    #rmdict = json.loads(remove_json)
    #result = []

    # files
    file_list = rmdict.get('files', [])
    for elem in file_list:
        try:
            res = ctx.unlink(str(elem))
            print json.dumps({'Code': res, 'Reason': 'OK'})
            #result.append({'Code': res, 'Reason': 'OK'})
        except gfal2.GError as gerror:
            print json.dumps({'Code': 1, 'Reason': str(gerror)})
            #result.append({'Code': 1, 'Reason': str(gerror)})
            _logger.error(str(gerror))

    # directories
    dir_list = rmdict.get('dirs', [])
    for elem in dir_list:
        try:
            ctx.rmdir(elem)
            print json.dumps({'Code': res, 'Reason': 'OK'})
            #result.append({'Code': res, 'Reason': 'OK'})
        except gfal2.GError as gerror:
            #result.append({'Code': 1, 'Reason': str(gerror)})
            print json.dumps({'Code': 1, 'Reason': str(gerror)})
            _logger.error(str(gerror))

    return


def main():
    """
    gfal2 rm command line script.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("rmdict", type=str, help="rmlist: {'files':[file1, file2 ...],"
                                                 " 'dirs':[dir1, dir2, ...]}")
    parser.add_argument("-v", "--verbosity", action='store_const', const=logging.DEBUG,
                        default=logging.INFO, help="verbosity, INFO, if omitted")

    args = parser.parse_args()

    pdm_gfal_rm(json.loads(args.rmdict), args.verbosity)

def json_input():
    """
    gfal-ls directory/file based on a json document read from stdin.
    :return:
    """

    data = json.load(sys.stdin)
    json.dumps(pdm_gfal_rm(data), **data.get('options', {}))

if __name__ == "__main__":
    #main()
    json_input()
