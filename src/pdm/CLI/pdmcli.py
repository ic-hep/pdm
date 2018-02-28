#!/usr/bin/env python

import argparse
import user_subcommand

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    user_subcommand.UserCommand(subparsers)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

