=========
 INSTALL
=========

RecSQL uses python's setuptools, and specifically, `easy_install`_

You can install to the latest version directly from the internet (via
the Python Package index, where RecSQl is listed as
http://pypi.python.org/pypi/RecSQL) with ::

  easy_install RecSQL

or ::

  pip install RecSQL


You can also download the source manually from
https://github.com/orbeckst/RecSQL/tags and unpack
it. Install from the unpacked source with ::

    cd RecSQL-0.7.7
    python setup.py install

See the `easy_install`_ documentation for details, in particular if
you are interested in installing into non-standard locations.

The latest sources can be obtained by cloning the `RecSQL github repository`_ ::

  git clone git://github.com/orbeckst/RecSQL.git

and installing from the source as above.

Additional requirements are numpy_ and pysqlite_. `easy_install`_ will
automatically attempt to download appropriate versions if none are
currently installed.

.. URLs:
.. _easy_install: 
    http://peak.telecommunity.com/DevCenter/EasyInstall
.. _numpy:
    http://numpy.scipy.org
.. _pysqlite:
    http://pysqlite.org/
.. _RecSQL github repository: 
    https://github.com/orbeckst/RecSQL