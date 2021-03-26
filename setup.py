#!/usr/bin/env python

import sys
from setuptools import setup, find_packages

setup(name='pdm',
      version='1.0',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=['m2crypto',
                        'flask',
                        'flask-sqlalchemy',
                        'pyOpenSSL', # ==0.13.1 on RHEL7
                        'requests',
                        'sqlalchemy',
                        'twisted',
                        'python-dateutil',
                        'service_identity'],  # See commit notes: Needed by Twisted.
      include_package_data=True,
      scripts=['src/pdm/bin/pdm'],
     )

