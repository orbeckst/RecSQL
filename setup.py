# $Id: setup.py 3489 2009-05-26 21:55:54Z root $
# setuptools installation of RecSQL
# Copyright (c) 2007-2009 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License 3 (or higher, your choice)


from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(name="RecSQL",
      version="0.4",
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
      keywords="utilities numpy SQLite SQL",
      packages=find_packages(exclude=['tests','extras','doc/examples']),
      install_requires=['numpy>=1.0',
                        'pysqlite',
                        ],
)

      
