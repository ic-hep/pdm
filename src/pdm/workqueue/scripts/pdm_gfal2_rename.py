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


def pdm_gfal_rename(data, verbosity=logging.INFO):
    """
    Rename file or directory.
    :param data: json-loaded dict with data {"source": url}
    :param verbosity: mapped from "options":{"verbosity":logging level}
    :return: dict of a form {'Code': return code, 'Reason': reason, 'id': jobid})
    """
    _logger.setLevel(verbosity)

    rename_list = data.get('files',[])
    if not rename_list:
        _logger.warning("No files to rename")
        dump_and_flush({"Reason": "No files to rename passed in", "Code": 1, 'id': ''})
        return

    ctx = gfal2.creat_context()

    for jobid, src, dst in rename_list:
        try:
            res = ctx.rename(str(src), str(dst))
            dump_and_flush({'Code': res, 'Reason': 'OK', 'id': jobid})
        except gfal2.GError as gerror:
            dump_and_flush({'Code': 1, 'Reason': str(gerror), 'id': jobid}, _logger, str(gerror),
                           logging.ERROR)
    return

def json_input():
    """
    gfal-rename  file or directory based on a json document read from stdin.
    :return: None
    """

    data = json.load(sys.stdin)
    pdm_gfal_rename(data, **data.get('options', {}))


if __name__ == "__main__":
    json_input()
