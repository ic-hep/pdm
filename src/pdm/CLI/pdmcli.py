#!/usr/bin/env python
"""
PDM Command Line Interface
"""
import argparse
import os
import logging
import pdm.CLI.user_subcommand as user_subcommand
from pdm.utils.config import ConfigSystem


def main(opt_conf_file=None):  #pylint: disable=too-many-branches
    """
    Main CLI function. Read configuration and add subparsers.
    The order configuration file is search for:
    -c/--config command line switch
    PDM_CLIENT_CONF environment variable
    ~/.pdm/client.conf and /etc/pdm/client.conf
    a file pointed to by the argument passed in

    :param opt_conf_file: an optional config file location
    :return: None
    """

    #_logger = logging.getLogger(__name__)
    _logger = logging.getLogger()
    _logger.addHandler(logging.StreamHandler())

    conf_files = ['~/.pdm/client.conf', '/etc/pdm/client.conf']
    env_var = 'PDM_CLIENT_CONF'

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="config file location")
    parser.add_argument("-v", "--verbosity", action='store_const', const=logging.DEBUG, default=logging.INFO, help="verbosity level")
    subparsers = parser.add_subparsers()
    user_subcommand.UserCommand(subparsers)
    args = parser.parse_args()

    _logger.setLevel(args.verbosity)

    conf_file = None
    # config: user given location first
    if args.config:
        if not os.path.isfile(os.path.expanduser(args.config)):
            _logger.error(" -c/--config: file %s does not exist !", args.config)
            return
        conf_file = args.config

    # environment
    if conf_file is None:
        conf_file = os.environ.get(env_var)
        if conf_file:
            _logger.debug("Trying $%s config pointing to: %s ...",
                          env_var, os.path.expanduser(conf_file))
            if os.path.isfile(os.path.expanduser(conf_file)):
                _logger.debug("... OK")
            else:
                conf_file = None
                _logger.debug("failed (file pointed to by the env. var. does not exist)")

    # other fixed locations
    if conf_file is None:
        for item in conf_files:
            _logger.debug("Trying config at: %s ...", os.path.expanduser(item))
            if os.path.isfile(os.path.expanduser(item)):
                conf_file = os.path.expanduser(item)
                _logger.debug("... OK")
                break
        else:
            _logger.debug("... failed at all fixed locations")

    if conf_file is None and opt_conf_file is not None:
        conf_file = opt_conf_file
        _logger.debug("Will try to use the config file defined programatically by pdm: %s",
                      conf_file)

    if conf_file is None:
        _logger.debug("Will use a built-in config file now...")
        conf_file = os.path.join(os.path.dirname(__file__), '../../../etc/system.client.conf')

    _logger.debug("Config file location used: %s", os.path.abspath(conf_file))
    ConfigSystem.get_instance().setup(conf_file)
    os.chdir(os.path.dirname(conf_file))
    #
    args.func(args)


if __name__ == '__main__':
    main()
