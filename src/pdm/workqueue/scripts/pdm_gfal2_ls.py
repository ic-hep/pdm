#!/usr/bin/env python
""" pdm gfal-ls wrapper """
import os
import sys
import inspect
import stat
from collections import OrderedDict
import json
import logging
import pprint as pp
import gfal2
import imp

dump_and_flush = imp.load_module('stdout_dump_helper',
                                 *imp.find_module('stdout_dump_helper',
                                                  [os.path.dirname(__file__)])).dump_and_flush

logging.basicConfig()
_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

ID = None


def pdm_gfal_ls(root, depth=-1, verbosity=logging.INFO, timeout=None):
    """
    Get a directory listing of a given depth. Depth = -1 list the filesystem for all levels.
    core_timeout is a global timeout for all gfal operations.
    """

    # _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    _logger.info("gfal listing root: %s at max depth: %d", root, depth)

    max_depth = max(-1, depth)

    ctx = gfal2.creat_context()
    if timeout is not None:
        _logger.info("timeout is: %d", timeout)
        ctx.set_opt_integer("CORE","NAMESPACE_TIMEOUT", timeout)
    result = OrderedDict()
    # determine if the path point to a file, no recursion if True
    try:
        stat_tup = ctx.stat(root)
    except Exception as gfal_exc:
        _logger.error("Error when obtaining ctx.stat(%s) \n %s", root, gfal_exc)
        dump_and_flush({'Reason': str(gfal_exc), 'Code': 1, 'id': ID})
        sys.exit(1)

    stat_dict = {k: getattr(stat_tup, k)
                 for k, _ in inspect.getmembers(stat_tup.__class__,
                                                lambda x: isinstance(x, property))}

    if stat.S_ISDIR(stat_dict['st_mode']):
        pdm_gfal_long_list_dir(ctx, root, result, max_depth)
    else:
        _logger.debug("Top path points to a file ...")
        pdm_gfal_list_file(stat_dict, root, result)

    if verbosity == logging.DEBUG:
        pp.pprint(result, stream=sys.stderr)
    return result


def pdm_gfal_list_file(props, root, result):
    """
    List a file with its properties in the case the root is a file
    """
    listing = props.copy()
    listing['name'] = os.path.split(root)[1]
    result[os.path.split(root)[0]] = [listing]


def pdm_gfal_list_dir(ctx, root, result, max_depth=-1, depth=1):
    """
    Recursively list files and directories of root (if root is a directory)
    :param ctx: gfal2 context
    :param root: root directory to start from
    :param result: result dictionary for root:
    {root:[{'name':filename,... stat dict entries ...},{..}]}
    :param max_depth: maximum recursion depth:
    positive integer or -1 for a max depth (0 is equivalent to -1)
    :param depth: current depth. Used internally for recursion (leave out)
    :return: None
    """

    _logger.debug("gfal listing root: %s at depth: %d", root, depth)

    try:
        stat_tup = ((item, ctx.stat(os.path.join(root, item))) for item in ctx.listdir(root))
    except Exception as gfal_exc:
        _logger.error("Error when analysing %s \n %s", root, gfal_exc)
        dump_and_flush({'Reason': str(gfal_exc), 'Code': 1, 'id': ID})
        sys.exit(1)

    stat_d_list = [dict(((k, getattr(j, k))
                         for k, l in inspect.getmembers(j.__class__,
                                                        lambda x: isinstance(x, property))),
                        name=i)
                   for i, j in stat_tup]

    result[root] = stat_d_list

    if depth >= max_depth and max_depth != -1:
        return

    # sub directories of root
    subdirs = [elem['name'] for elem in stat_d_list if stat.S_ISDIR(elem['st_mode'])]
    if not subdirs:
        # we reached the bottom
        return
    for subdir in subdirs:
        pdm_gfal_list_dir(ctx, os.path.join(root, subdir), result, max_depth, depth=depth + 1)


def pdm_gfal_long_list_dir(ctx, root, result, max_depth=-1, depth=1):
    """
    Recursively list files and directories of root (if root is a directory).
    Use opendir method, so file or directory names are obtained together
    with their stat information in one go. Skip '.' and '..' directories.
    :param ctx: gfal2 context
    :param root: root directory to start from
    :param result: result dictionary for root:
    {root:[{'name':filename,... stat dict entries ...},{..}]}
    :param max_depth: maximum recursion depth:
    positive integer or -1 for a max depth (0 is equivalent to -1)
    :param depth: current depth. Used internally for recursion (leave out)
    :return: None

    """

    dir_entries = []
    try:
        dirp = ctx.opendir(root)

        while True:
            (dirent, stats) = dirp.readpp()
            if dirent is None:
                break
            if dirent.d_name =='.' or dirent.d_name =='..':
                continue
            dir_entry = {k: getattr(stats, k) for k, _ in
                         inspect.getmembers(stats.__class__, lambda x: isinstance(x, property))}
            dir_entry['name'] = dirent.d_name
            dir_entries.append(dir_entry)

        result[root] = dir_entries
    except Exception as gfal_exc:
        _logger.error("Error when analysing %s \n %s", root, gfal_exc)
        dump_and_flush({'Reason': str(gfal_exc), 'Code': 1, 'id': ID})
        sys.exit(1)

    if depth >= max_depth and max_depth != -1:
        return

    # sub directories of root
    subdirs = [elem['name'] for elem in dir_entries if stat.S_ISDIR(elem['st_mode'])]

    for subdir in subdirs:
        pdm_gfal_long_list_dir(ctx, os.path.join(root, subdir), result, max_depth, depth=depth + 1)


def json_input():
    """
    gfal-ls directory/file based on a json document read from stdin.
    :return:
    """

    data = json.load(sys.stdin)
    global ID  # pylint: disable=global-statement
    ID = data.get('files')[0][0]  # (id, file)
    # json.dump({'Reason': 'OK', 'Code': 0, 'id': ID,
    #           'Listing': pdm_gfal_ls(str(data.get('files')[0][1]), **data.get('options', {}))},
    #          sys.stdout)
    # sys.stdout.write('\n')
    # sys.stdout.flush()
    obj = {'Reason': 'OK', 'Code': 0, 'id': ID,
           'Listing': pdm_gfal_ls(str(data.get('files')[0][1]), **data.get('options', {}))}
    dump_and_flush(obj)


if __name__ == "__main__":
    json_input()
