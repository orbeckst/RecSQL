=========
 README
=========

RecSQL's basic idea is to treat numpy record arrays like SQL
tables. What it does, in fact, is to represent the arrays as real SQL
tables (using SQLite) and provide convenience functions to return
recarrays on demand.

This works ok for small tables but less so if you want to access
gigabytes of data as recarrays.


Example
-------

  >>> from recsql import SQLarray
  >>> import numpy
  >>> a = numpy.rec.fromrecords(numpy.arange(100).reshape(25,4), names='a,b,c,d')
  >>> Q = SQLarray('my_name', a)
  >>> print repr(Q.recarray)
  rec.array([(0, 1, 2, 3), (4, 5, 6, 7), (8, 9, 10, 11), (12, 13, 14, 15),
	 (16, 17, 18, 19), (20, 21, 22, 23), (24, 25, 26, 27),
	 (28, 29, 30, 31), (32, 33, 34, 35), (36, 37, 38, 39),
	 (40, 41, 42, 43), (44, 45, 46, 47), (48, 49, 50, 51),
	 (52, 53, 54, 55), (56, 57, 58, 59), (60, 61, 62, 63),
	 (64, 65, 66, 67), (68, 69, 70, 71), (72, 73, 74, 75),
	 (76, 77, 78, 79), (80, 81, 82, 83), (84, 85, 86, 87),
	 (88, 89, 90, 91), (92, 93, 94, 95), (96, 97, 98, 99)], 
	dtype=[('a', '<i4'), ('b', '<i4'), ('c', '<i4'), ('d', '<i4')])
  >>> Q.SELECT('*', 'WHERE a < 10 AND b > 5')
  rec.array([(8, 9, 10, 11)], 
      dtype=[('a', '<i4'), ('b', '<i4'), ('c', '<i4'), ('d', '<i4')])
  # creating new SQLarrays:  
  >>> R = Q.selection('a < 20 AND b > 5')
  >>> print R
  <recsql.sqlarray.SQLarray object at 0x...>



Availability
------------

The latest version of the package is being made available via the
internet at https://github.com/orbeckst/RecSQL or from the direct
download URI (for ``easy_install``) https://github.com/orbeckst/RecSQL/tags

RecSQL is also listed on PyPi http://pypi.python.org/pypi/RecSQL and
can thus be installed with ::

  easy_install RecSQL

or ::

  pip install RecSQL

See :doc:`INSTALL` for further installation instructions.

A git repository of the package is hosted at
http://github.com/orbeckst/RecSQL .


Contact
-------

Oliver Beckstein <orbeckst@gmail.com>

