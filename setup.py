# setuptools installation of RecSQL
# Copyright (c) 2007-2010 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License 3 (or higher, your choice)


from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import sys

requirements = ['numpy>=1.0',]

major, minor, patch = sys.version_info[:3]
if major <= 2 and minor <= 5:
    requirements.append("pysqlite")

# Dynamically calculate the version based on VERSION.
version = __import__('recsql').get_version()

setup(name="RecSQL",
      version=version,
      description="Treat SQLlite tables as recarrays",
      long_description="""\
A simple implementation of numpy.recarray-like tables that can
be operated on via SQL. The underlying tables are SQLite tables
that are built from a numpy.recarray or a general iterator.
""",
      author="Oliver Beckstein",
      author_email="orbeckst@gmail.com",
      license="GPLv3",
      url="http://sbcb.bioch.ox.ac.uk/oliver/download/Python/RecSQL",
      keywords="utilities numpy SQLite SQL CSV",
      packages=find_packages(exclude=['tests','extras','doc/examples']),
      install_requires=requirements,
      zip_safe = True,
)

      
