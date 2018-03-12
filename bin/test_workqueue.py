#!/usr/bin/env python

import os
import sys
TOP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMP_PATH = os.path.join(TOP_PATH, "src")
sys.path.append(IMP_PATH)

from pdm.utils.config import ConfigSystem
from pdm.workqueue.Worker import Worker
def main():

    if len(sys.argv) != 2:
        print "Usage: test_demo.py <conf_file>"
        sys.exit(1)

    # We load a config so that the client can find the server
    # via the [location] block
    conf_file = sys.argv[1]
    ConfigSystem.get_instance().setup(conf_file)
    os.chdir(os.path.dirname(conf_file))
    # Create a client and run the hello function
    Worker().start()

#    print client.test()
if __name__ == '__main__':
    main()

