#!/usr/bin/env python
"""
gfal2 based file remover.
"""
import sys
import argparse
import json
import logging
import gfal2

logging.basicConfig()
_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def pdm_gfal_rm(rmdict, verbosity=logging.INFO):
    """
    Remove files and directories. Print json string immediately after a file is removed.
    """
    # _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    ctx = gfal2.creat_context()

    # files
    file_list = rmdict.get('files', [])  # list of dublets: (jobid, filename)
    for jobid, elem in file_list:
        try:
            res = ctx.unlink(str(elem))
            json.dump({'Code': res, 'Reason': 'OK', 'id': jobid}, sys.stdout)
            sys.stdout.flush()
        except gfal2.GError as gerror:
            json.dump({'Code': 1, 'Reason': str(gerror), 'id': jobid}, sys.stdout)
            _logger.error(str(gerror))
            sys.stdout.flush()

    # directories
    dir_list = rmdict.get('dirs', [])
    for jobid, elem in dir_list:
        try:
            res = ctx.rmdir(str(elem))
            json.dump({'Code': res, 'Reason': 'OK', 'id': jobid}, sys.stdout)
            sys.stdout.flush()
        except gfal2.GError as gerror:
            json.dump({'Code': 1, 'Reason': str(gerror), 'id': jobid}, sys.stdout)
            _logger.error(str(gerror))
            sys.stdout.flush()


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
    :return: None
    """

    data = json.load(sys.stdin)
    pdm_gfal_rm(data, **data.get('options', {}))


if __name__ == "__main__":
    # main()
    json_input()
