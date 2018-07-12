import logging
import sys
import json


def dump_and_flush(obj, logger=None, log_message='',
                    verbosity=logging.INFO, *args, **kwargs):
    """
    Dump json return info, add a '\n' and flush stdout
    :param obj  object to be JSON-dumped
    :param message log message
    :param logger: logger object if loggins is requires
    :param level: logging level
    :return:
    """
    json.dump(obj, sys.stdout)
    sys.stdout.write('\n')
    if logger:
        logger.log(verbosity, log_message, *args, **kwargs)
    sys.stdout.flush()
