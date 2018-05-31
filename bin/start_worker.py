#!/usr/bin/env python
"""Worker start-up script."""
import os
import sys
import logging
from argparse import ArgumentParser
TOP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMP_PATH = os.path.join(TOP_PATH, "src")
sys.path.append(IMP_PATH)

from pdm.utils.config import ConfigSystem
from pdm.workqueue.Worker import Worker

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("conf", help="Worker config file.")
    parser.add_argument("-d", "--debug", action='store_true', default=False,
                        help="Debug mode: Interactive output, don't fork!")
    parser.add_argument("-n", "--n-shot", type=int, default=None,
                        help="N shot mode: Worker will perform n jobs before dying.")
    parser.add_argument('-v', '--verbose', action='count',
                        help="Increase the logged verbosite, can be used twice")

    args = parser.parse_args()
    ConfigSystem.get_instance()\
                .setup(os.path.abspath(os.path.expandvars(os.path.expanduser(args.conf))))
    Worker(debug=args.debug,
           n_shot=args.n_shot,
           loglevel=max(logging.WARNING - 10 * (args.verbose or 0), logging.DEBUG)).start()
