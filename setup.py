#!/usr/bin/env python

import sys
from setuptools import setup, find_packages

setup(name='pdm',
      version='1.0',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=['m2crypto',
                        'flask==0.10.1',
                        'flask-sqlalchemy==2.0',
                        'pyOpenSSL', # ==0.13.1 on RHEL7
                        'requests==2.31.0',
                        'sqlalchemy==0.9.8',
                        'twisted==12.1.0',
                        'enum34==1.0.4',
                        'python-dateutil==1.5'],
      include_package_data=True,
      scripts=['src/pdm/bin/pdm'],
     )

