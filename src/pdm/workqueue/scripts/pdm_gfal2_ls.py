#!/usr/bin/env python
""" pdm gfal-ls wrapper """
import os
import sys
import inspect
import stat
import argparse
from collections import OrderedDict
import json
import logging
import pprint as pp
import gfal2

_logger = logging.getLogger(__name__) #pylint: disable=invalid-name

def pdm_gfal_ls(root, max_depth=-1, verbosity=logging.INFO):
    """
    Get a directory listing of a given depth. Depth = -1 list the filesystem for all levels
    """

    _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    _logger.info("gfal listing root: %s at max depth: %d", root, max_depth)

    max_depth = max(-1, max_depth)

    ctx = gfal2.creat_context()
    result = OrderedDict()
    # determine if the path point to a file, no recursion if True
    try:
        a = ctx.stat(root)
    except Exception as e:
        _logger.error("Error when obtaining ctx.stat(%s) \n %s", root, e)
        print {'Reason': str(e), 'Code': 1}
        sys.exit(1)

    b = {k: getattr(a, k) for k, _ in inspect.getmembers(a.__class__,
                                                         lambda x: isinstance(x, property))}

    if stat.S_ISDIR(b['st_mode']):
        pdm_gfal_long_list_dir(ctx, root, result, max_depth)
    else:
        _logger.debug("Top path points to a file ...")
        pdm_gfal_list_file(b, root, result)

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
        a = ((item, ctx.stat(os.path.join(root, item))) for item in ctx.listdir(root))
    except Exception as e:
        _logger.error("Error when analysing %s \n %s", root, e)
        print {'Reason': str(e), 'Code': 1}
        sys.exit(1)

    b = [dict(((k, getattr(j, k))
               for k, l in inspect.getmembers(j.__class__,
                                              lambda x: isinstance(x, property))), name=i)
         for i, j in a]

    result[root] = b

    if depth >= max_depth and max_depth != -1:
        return

    # sub directories of root
    subdirs = [elem['name'] for elem in b if stat.S_ISDIR(elem['st_mode'])]
    if not subdirs:
        # we reached the bottom
        return
    for subdir in subdirs:
        pdm_gfal_list_dir(ctx, os.path.join(root, subdir), result, max_depth, depth=depth + 1)


def pdm_gfal_long_list_dir(ctx, root, result, max_depth=-1, depth=1):
    """
    Recursively list files and directories of root (if root is a directory).
    Use opendir method, so file or directory names are obtained together
    with their stat information in one go.
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
            dir_entry = {k: getattr(stats, k) for k, _ in
                         inspect.getmembers(stats.__class__, lambda x: isinstance(x, property))}
            dir_entry['name'] = dirent.d_name
            dir_entries.append(dir_entry)

        result[root] = dir_entries
    except Exception as e:
        _logger.error("Error when analysing %s \n %s", root, e)
        print {'Reason': str(e), 'Code': 1}
        sys.exit(1)

    if depth >= max_depth and max_depth != -1:
        return

    # sub directories of root
    subdirs = [elem['name'] for elem in dir_entries if stat.S_ISDIR(elem['st_mode'])]

    for subdir in subdirs:
        pdm_gfal_list_dir(ctx, os.path.join(root, subdir), result, max_depth, depth=depth + 1)


def main():
    """
    Directory listing with the commad line options
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("topdir", type=str, help="filename or a top directory to list")
    parser.add_argument("-v", "--verbosity", action='store_const', const=logging.DEBUG,
                        default=logging.INFO,
                        help="verbosity level")
    parser.add_argument("-d", "--depth", default=-1, type=int, help="depth")
    args = parser.parse_args()
    print json.dumps(pdm_gfal_ls(args.topdir,
                                 max_depth=max(-1, args.depth), verbosity=args.verbosity))


def json_input():
    """
    gfal-ls directory/file based on a json document read from stdin.
    :return:
    """

    data = json.load(sys.stdin)
    print json.dumps(pdm_gfal_ls(str(data.get('files')[0]), **data.get('options', {})))


if __name__ == "__main__":
    # main()
    json_input()
