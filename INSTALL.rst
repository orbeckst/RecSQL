=========
 INSTALL
=========

You can install to the latest version directly from the internet (via
the Python Package index, where RecSQl is listed as
http://pypi.python.org/pypi/RecSQL) with ::

  pip install RecSQL


You can also download the source manually from
https://github.com/orbeckst/RecSQL/tags and unpack
it. Install from the unpacked source with ::

    cd RecSQL-0.7.11
    python setup.py install

The latest sources can be obtained by cloning the `RecSQL github
repository`_ ::

  git clone git://github.com/orbeckst/RecSQL.git

and installing from the source as above.

Additional requirements are numpy_ and pysqlite_. `pip`_ will
automatically attempt to download appropriate versions if none are
currently installed.

.. URLs:
.. _numpy:
    http://numpy.scipy.org
.. _pysqlite:
    http://pysqlite.org/
.. _RecSQL github repository: 
    https://github.com/orbeckst/RecSQL
.. _pip: https://pip.pypa.io/en/stable/
