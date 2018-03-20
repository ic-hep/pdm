#!/usr/bin/env python
"""Worker start-up script."""
import os
from argparse import ArgumentParser

from pdm.utils.config import ConfigSystem
from pdm.workqueue.Worker import Worker

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("conf", help="Worker config file.")
    parser.add_argument("-d", "--debug", action='store_true', default=False,
                               help="Debug mode: Interactive output, don't fork!")
    parser.add_argument("-o", "--one-shot", action='store_true', default=False,
                               help="One shot mode: Worker will perform one job before dying.")

    args = parser.parse_args()
    ConfigSystem.get_instance()\
                .setup(os.path.abspath(os.path.expandvars(os.path.expanduser(args.conf))))
    Worker(debug=args.debug, one_shot=args.one_shot).start()
