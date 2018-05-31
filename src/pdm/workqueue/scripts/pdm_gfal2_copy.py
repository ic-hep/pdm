#!/usr/bin/env python
""" PDM gfal2-copy wrapper """
import os
import sys
import argparse
import json
import logging
import gfal2

logging.basicConfig()
_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def event_callback(event):
    """
    gfal-copy event callback. Print event information to sys.stderr
    :param event:
    :return:
    """
    print >> sys.stderr, "[%s] %s %s %s" % \
                         (event.timestamp, event.domain, event.stage, event.description)


def monitor_callback(src, dst, average, instant, transferred, elapsed):  # pylint: disable=too-many-arguments
    """
    gfal-copy monitor callback. Print Monitoring information to sys.stderr
    :param src: source file
    :param dst: dest file
    :param average: average speed in kB/s
    :param instant:
    :param transferred: MB transferred
    :param elapsed: time in seconds
    :return:
    """
    print >> sys.stderr, "MONITOR src: %s [%4d] %.2fMB (%.2fKB/s)\n" % (
        src, elapsed, transferred / 1048576, average / 1024),
    sys.stderr.flush()


def pdm_gfal_copy(copy_dict, s_cred_file=None, t_cred_file=None, overwrite=False, # pylint: disable=too-many-arguments, too-many-locals
                  parent=True, nbstreams=1,
                  verbosity=logging.INFO):
    """
    Copy a single source file to a target file.
    Use separate source and target credentials. Do not overwrite destination by
    default.
    Copy json string is of a form: '{"files":[(source1, dest1), (source2, dest2),...]}'
    """

    # _logger.addHandler(logging.StreamHandler())
    _logger.setLevel(verbosity)

    # copy_dict = json.loads(copy_json)

    copy_list = copy_dict.get('files', [])

    if not copy_list:
        json.dump([], sys.stdout)
        sys.stdout.flush()
        return

    if _logger.isEnabledFor(logging.DEBUG):
        for f_source, f_dest in copy_list:
            _logger.debug("gfal copy source: %s TO dest: %s , overwrite ? %s ",
                          f_source, f_dest, overwrite)

    s_cred = _get_cred(s_cred_file)
    t_cred = _get_cred(t_cred_file)

    if s_cred is None or t_cred is None:
        _logger.fatal("Please provide credential location: source %s, dest %s. ",
                      s_cred, t_cred)
        json.dump({"Reason": "No credentials passed in", "Code": 1, 'id': ''}, sys.stdout)
        sys.stdout.flush()
        return

    ctx = gfal2.creat_context()

    params = ctx.transfer_parameters()
    params.overwrite = overwrite
    params.create_parent = parent
    params.nbstreams = nbstreams
    params.event_callback = event_callback
    params.monitor_callback = monitor_callback

    # unzip:
    _, src_l, dst_l = zip(*copy_list)  # don't care about jobid
    s_root = str(os.path.dirname(os.path.commonprefix(src_l)))
    d_root = str(os.path.dirname(os.path.commonprefix(dst_l)))

    _logger.info("common source prefix: %s ", s_root)
    _logger.info("common dest   prefix: %s ", d_root)

    gfal2.cred_set(ctx, s_root, s_cred)
    gfal2.cred_set(ctx, d_root, t_cred)

    # result = []
    for jobid, source_file, dest_file in copy_list:
        try:
            res = ctx.filecopy(params, str(source_file), str(dest_file))
            json.dump({'Code': res, 'Reason': 'OK', 'id': jobid}, sys.stdout)
            sys.stdout.flush()
        except gfal2.GError as gerror:
            json.dump({'Code': 1, 'Reason': str(gerror), 'id': jobid}, sys.stdout)
            sys.stdout.flush()
            _logger.error(str(gerror))
    return  # result


def _get_cred(cred_file):
    if cred_file:
        cred = gfal2.cred_new('X509_CERT', str(cred_file))
    else:
        return None
    return cred


def main():
    """
    Gfal2 copy wrapper with different source and destination proxies. Works with command line
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("copylist", type=str, help="copylist: {'files':[(s,t), 9s2, t2) ...]}")
    parser.add_argument("-v", "--verbosity", action='store_const',
                        const=logging.DEBUG, default=logging.INFO,
                        help="verbosity, INFO, if omitted")
    parser.add_argument("-s", "--s_cred", default=os.environ.get('X509_USER_PROXY_SRC', None),
                        help="source credential location")
    parser.add_argument("-t", "--t_cred", default=os.environ.get('X509_USER_PROXY_DST', None),
                        help="target credential location")
    parser.add_argument("-o", "--overwrite", action='store_const', const=True, default=False)
    parser.add_argument("-p", "--parent", action='store_const', const=True, default=False)
    parser.add_argument("-n", "--nbstreams", default=1, type=int, help="number of streams")
    args = parser.parse_args()

    pdm_gfal_copy(json.loads(args.copylist), args.s_cred, args.t_cred,
                  args.overwrite, args.parent, args.nbstreams)


def json_input():
    """
    gfal2 wrapper which takes a json doc from stdin.
    :return:
    """

    data = json.load(sys.stdin)
    if 'options' not in data:
        data['options'] = {}
        
    data['options'].setdefault('s_cred_file', os.environ.get('X509_USER_PROXY_SRC', None))
    data['options'].setdefault('t_cred_file', os.environ.get('X509_USER_PROXY_DST', None))
    pdm_gfal_copy(data, **data.get('options', {}))


if __name__ == "__main__":
    json_input()
    # main()
