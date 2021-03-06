#!/usr/bin/env python

import os
import sys
TOP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMP_PATH = os.path.join(TOP_PATH, "src")
sys.path.append(IMP_PATH)

from pdm.framework.Startup import ExecutableServer

def main():
    exe = ExecutableServer()
    exe.run()

if __name__ == '__main__':
    main()

