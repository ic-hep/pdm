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


def pdm_gfal_chmod(data, permissions, verbosity=logging.INFO, timeout=None):
    """
    Change directory/file permissions
    :param data: json-loaded dict with data {"source": url}
    :param permissions: permissions mapped from {"options":{"permissions":int}}
    :param verbosity: mapped from {"options":{"verbosity":logging level}}
    :param timeout: global gfal2 timeout for all operations
    :return: dict of a form {'Code': return code, 'Reason': reason, 'id': jobid})
    """
    _logger.setLevel(verbosity)

    chmod_list = data.get('files', [])
    if not chmod_list:
        _logger.warning("No files to set permissions passed in")
        dump_and_flush({"Reason": "No files to set permissions passed in", "Code": 1, 'id': ''})
        return

    ctx = gfal2.creat_context()
    if timeout is not None:
        ctx.set_opt_integer("CORE","NAMESPACE_TIMEOUT", timeout)

    for jobid, src in chmod_list:
        try:
            res = ctx.chmod(str(src), permissions)
            dump_and_flush({'Code': res, 'Reason': 'OK', 'id': jobid})
        except gfal2.GError as gerror:
            dump_and_flush({'Code': 1, 'Reason': str(gerror), 'id': jobid}, _logger, str(gerror),
                           logging.ERROR)
    return


def json_input():
    """
    gfal-mkdir directory based on a json document read from stdin.
    :return: None
    """

    data = json.load(sys.stdin)
    pdm_gfal_chmod(data, **data.get('options', {}))


if __name__ == "__main__":
    json_input()
