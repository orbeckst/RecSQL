# setuptools installation of RecSQL
# Copyright (c) 2007-2011 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License 3 (or higher, your choice)


from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import sys

requirements = ['numpy>=1.0',]

major, minor, patch = sys.version_info[:3]
if major == 1 or (major == 2 and minor < 5):
    requirements.append("pysqlite")

# Dynamically calculate the version based on VERSION.
version = __import__('recsql').get_version()

setup(name="RecSQL",
      version=version,
      description="Treat SQLite tables as recarrays",
      long_description="""\
A simple implementation of numpy.recarray-like tables that can
be operated on via SQL. The underlying tables are SQLite tables
that are built from a numpy.recarray or a general iterator.
""",
      author="Oliver Beckstein",
      author_email="orbeckst@gmail.com",
      license="GPLv3",
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Science/Research',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Libraries',
                   'Topic :: Text Processing',
                   'Topic :: Database',
                   ],
      url="https://github.com/orbeckst/RecSQL",
      keywords="utilities numpy SQLite SQL CSV",
      packages=find_packages(exclude=['tests','extras','doc/examples']),
      install_requires=requirements,
      zip_safe = True,
)

      
