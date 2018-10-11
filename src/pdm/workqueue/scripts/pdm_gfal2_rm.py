#!/usr/bin/env python
"""
gfal2 based file remover.
"""
import sys
import os
import json
import logging
import gfal2
import imp

dump_and_flush = imp.load_module('stdout_dump_helper',
                                 *imp.find_module('stdout_dump_helper',
                                                  [os.path.dirname(__file__)])).dump_and_flush

logging.basicConfig()
_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def pdm_gfal_rm(rmdict, verbosity=logging.INFO, timeout=None):
    """
    Remove files and directories. Print json string immediately after a file is removed.
    :param rmdict: json-loaded dict with data {"source": url}
    :param verbosity: mapped from "options":{"verbosity":logging level}
    :param timeout: global gfal2 timeout for all operations
    """
    # _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    ctx = gfal2.creat_context()
    if timeout is not None:
        ctx.set_opt_integer("CORE","NAMESPACE_TIMEOUT", timeout)

    # files
    file_list = rmdict.get('files', [])  # list of dublets: (jobid, filename)
    for jobid, elem in file_list:
        try:
            res = ctx.unlink(str(elem))
            dump_and_flush({'Code': res, 'Reason': 'OK', 'id': jobid})
        except gfal2.GError as gerror:
            dump_and_flush({'Code': 1, 'Reason': str(gerror), 'id': jobid}, _logger, str(gerror))

    # directories
    dir_list = rmdict.get('dirs', [])
    for jobid, elem in dir_list:
        try:
            res = ctx.rmdir(str(elem))
            dump_and_flush({'Code': res, 'Reason': 'OK', 'id': jobid})
        except gfal2.GError as gerror:
            dump_and_flush({'Code': 1, 'Reason': str(gerror), 'id': jobid}, _logger, str(gerror))

    return


def json_input():
    """
    gfal-rm directory/file based on a json document read from stdin.
    :return: None
    """

    data = json.load(sys.stdin)
    pdm_gfal_rm(data, **data.get('options', {}))


if __name__ == "__main__":
    json_input()
