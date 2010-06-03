# RecSQL -- a simple mash-up of sqlite and numpy.recsql
# Copyright (C) 2007-2010 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License, version 3 or higher (your choice)
"""
================
 RecSQL package
================

RecSQL is a simple module that provides a numpy.record array frontend
to an underlying SQLite table.

The :class:`SQLarray` object populates a SQL table from a numpy record array, a
iterable that supplies table records, or a string that contains an
especially simple reStructured text table. The SQL table is held in memory
and functions are provided to run SQL queries and commands on the
underlying database. Queries return record arrays if possible (although a
flag can explicitly change this).

Query results are cached to improve performance. This can be disabled
(which is recommened for large data sets).

The SQL table is named on initialization. Later one can refer to this table
by the name or the magic name *__self__* in SQL statements. Additional
tables can be added to the same database (by using the connection keyword
of the constructor)

The :mod:`recsql.rest_table` module uses the base functionality to
parse a restructured text table from a string (such as a doc string)
and returns a nicely structured table. This allows for use of
parameters that are documented in the doc strings.

.. SeeAlso:: PyTables_ is a high-performance interface to table
             data. In most cases you will probably better off in the
             long run using PyTables than recSQL.

.. _PyTables: http://www.pytables.org


Important functions and classes
===============================

A :class:`SQLarray` can be constructed by either reading data from a
CSV file or reST table with the :func:`SQLarray_fromfile` function or
constructed directly from a :class:`numpy.recarray` via the
:class:`SQLarray` constructor.

.. autofunction:: SQLarray_fromfile
.. autoclass:: SQLarray
   :members:

Example
=======
(to be written)


Additional SQL functions
========================

Note that the SQL database that is used as the backend for
:class:`SQLarray` has a few additional functions defined in addition
to the `standard SQL available in sqlite`_. These can be used in
``SELECT`` statements and often avoid post-processing of record arrays
in python. It is relatively straightforward to add new functions (see
the source code and in particular the
:meth:`recsql.sqlarray.SQLarray._init_sql_functions` method; the
functions themselves are defined in the module :mod:`recsql.sqlfunctions`).

.. _standard SQL available in sqlite: http://www.sqlite.org/lang.html


Simple SQL functions
--------------------

Simple functions transform a single input value into a single output value:

=====================   =============================================
Expression              SQL equivalent
=====================   =============================================
  y = f(x)               SELECT f(x) AS y
=====================   =============================================

Two additional simple functions have been defined:

=====================   =============================================
Simple SQL f()           description
=====================   =============================================
sqrt(x)                  square root math.sqrt(x)
fformat(format,x)        string formatting of a single value format % x
=====================   =============================================


Aggregate SQL functions
-----------------------

Aggregate functions combine data from a query; they are typically used with
a 'GROUP BY col' clause. They can be thought of as numpy ufuncs:

=====================   =============================================
Expression              SQL equivalent
=====================   =============================================
  y = f(x1,x2,...xN)     SELECT f(x) AS y ... GROUP BY x
=====================   =============================================

For completeness, the tablke also lists sqlite built-in aggregate
functions:

=====================   =============================================
Simple aggregate f()     description
=====================   =============================================
avg(x)                   mean [sqlite builtin]
std(x)                   standard deviation (using N-1 variance)
median(x)                median of the data (see ``numpy.median``)
min(x)                   minimum [sqlite builtin]
max(x)                   maximum [sqlite builtin]
=====================   =============================================


PyAggregate SQL functions
-------------------------

PyAggregate functions act on a list of data points in the same way as
ordinary aggregate functions but they return python objects such as numpy
arrays, or tuples of numpy arrays (eg bin edges and histogram). In order to
make this work, specific types have to be declared when returning the
results:

For instance, the histogram() function returns a python Object, the tuple
(histogram, edges)::

   a.sql('SELECT histogram(x) AS "x [Object]" FROM __self__', asrecarray=False)

The return type ('Object') needs to be declared with the ``'AS "x [Object]"'``
syntax (note the quotes). (See more details in the `sqlite documentation`_
under `adapters and converters`_.) The following table lists all *PyAggregate*
functions that have been defined:

.. _sqlite documentation: http://docs.python.org/library/sqlite3.html
.. _adapters and converters: 
   http://docs.python.org/library/sqlite3.html#using-adapters-to-store-additional-python-types-in-sqlite-databases

===============  ==============  ==============================================================
PyAggregate      type            signature; description
===============  ==============  ==============================================================
array             NumpyArray     array(x);
                                 a standard numpy array

histogram         Object         histogram(x,nbins,xmin,xmax); 
                                 histogram x in nbins evenly spaced bins between xmin and xmax

distribution      Object         distribution(x,nbins,xmin,xmax);
                                 normalized histogram whose integral gives 1

meanhistogram     Object         meanhistogram(x,y,nbins,xmin,xmax); 
                                 histogram data points y along x and average all y in each bin

stdhistogram      Object         stdhistogram(x,y,nbins,xmin,xmax); 
                                 give the standard deviation (from N-1 variance)
                                 std(y) = sqrt(Var(y)) with Var(y) = <(y-<y>)^2>

medianhistogram   Object         medianhistogram((x,y,nbins,xmin,xmax);
                                 median(y)

minhistogram      Object         minhistogram((x,y,nbins,xmin,xmax);
                                 min(y)

maxhistogram      Object         maxhistogram((x,y,nbins,xmin,xmax);
                                 max(y)

zscorehistogram   Object         zscorehistogram((x,y,nbins,xmin,xmax);
                                 <abs(y-<y>)>/std(y)
===============  ==============  ==============================================================



Examples of using types in tables
=================================

The following show how to use the special types.

Declare types as 'NumpyArray'::

   a.sql("CREATE TABLE __self__(a NumpyArray)")

Then you can simply insert python objects (type(my_array) == numpy.ndarray)::

   a.sql("INSERT INTO __self__(a) values (?)", (my_array,))

When returning results of declared columns one does not have to do anything ::

   (my_array,) = a.sql("SELECT a FROM __self__")

although one can also do ::

   (my_array,) = q.sql('SELECT a AS "a [NumpyArray]" FROM __self__')

but when using a PyAggregate the type *must* be declared::

   a.sql('SELECT histogram(x,10,0.0,1.5) as "hist [Object]" FROM __self__')
"""
VERSION = 0,7,3

__all__ = ['sqlarray']

from sqlarray import SQLarray, SQLarray_fromfile

def get_version():
    """Return current package version as a string."""
    return ".".join(map(str,VERSION))

def get_version_tuple():
    """Return current package version as a (MAJOR,MINOR,PATCHLEVEL)."""
    return tuple(VERSION)
