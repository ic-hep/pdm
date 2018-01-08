#!/usr/bin/env python

import sys
from setuptools import setup, find_packages

setup(name='pdm',
      version='1.0',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=[],
     )

