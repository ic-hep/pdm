#!/usr/bin/env python
"""Worker start-up script."""
import os
import sys
TOP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMP_PATH = os.path.join(TOP_PATH, "src")
sys.path.append(IMP_PATH)

from argparse import ArgumentParser

from pdm.utils.config import ConfigSystem
from pdm.workqueue.Worker import Worker

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("conf", help="Worker config file.")
    parser.add_argument("-d", "--debug", action='store_true', default=False,
                               help="Debug mode: Interactive output, don't fork!")
    parser.add_argument("-n", "--n-shot", type=int, default=None,
                               help="N shot mode: Worker will perform n jobs before dying.")

    args = parser.parse_args()
    ConfigSystem.get_instance()\
                .setup(os.path.abspath(os.path.expandvars(os.path.expanduser(args.conf))))
    Worker(debug=args.debug, n_shot=args.n_shot).start()
