#!/usr/bin/env python

import argparse
import os
import user_subcommand
from pdm.utils.config import ConfigSystem

def main():
    # config
    conf_file = "../etc/users.conf"
    ConfigSystem.get_instance().setup(conf_file)
    os.chdir(os.path.dirname(conf_file))
    #
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    user_subcommand.UserCommand(subparsers)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

