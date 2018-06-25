#!/usr/bin/env python
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


def pdm_gfal_mkdir(data, permissions=0o755, verbosity=logging.INFO):
    """
    Create a new directory.
    :param data: json-loaded dict with data {"dir": url}
    :param permissions: directory permissions mapped from {"options":{"permissions":int}}
    :param verbosity: mapped from {"options":{"verbosity":logging level}}
    :return: dict of a form {'Code': return code, 'Reason': reason, 'id': jobid})
    """

    _logger.setLevel(verbosity)

    ctx = gfal2.creat_context()
    dirname = data.get('dir', '')
    jobid = data.get('jobid', None)
    if dirname:
        try:
            res = ctx.mkdir(str(dirname), permissions)
            dump_and_flush({'Code': res, 'Reason': 'OK', 'id': jobid})
        except gfal2.GError as gerror:
            dump_and_flush({'Code': 1, 'Reason': str(gerror), 'id': jobid}, _logger, str(gerror),
                           logging.ERROR)
    else:
        dump_and_flush({'Code': 1, 'Reason': 'No directory name provided', 'id': jobid})


def json_input():
    """
    gfal-mkdir directory based on a json document read from stdin.
    :return: None
    """

    data = json.load(sys.stdin)
    pdm_gfal_mkdir(data, **data.get('options', {}))


if __name__ == "__main__":
    json_input()
