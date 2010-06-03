"""
:mod:`recsql.csv_table` --- Parse a simple CSV table
====================================================

Turn a CSV table into a numpy array. 

Uses :mod:`csv` (requires python 2.6 or better).

.. autoclass:: Table2array
   :members: __init__, recarray
.. autofunction:: make_python_name
"""

try:
    # needs python >= 2.6
    import csv
except ImportError:
    import warnings
    warnings.warn("csv module not available (needs python >=2.6)", category=ImportWarning)
    # ... just go ahead and fail later miserably ...
import numpy
import re

from convert import Autoconverter

def make_python_name(s, default=None, number_prefix='N'):
    """Returns a unicode string that can be used as a legal python identifier.

    :Arguments:
      *s*
         string
      *default*
         use *default* if *s* is ``None``
      *number_prefix*
         string to prepend if *s* starts with a number
    """
    if s in ('', None):
        s = default
    s = str(s)
    s = re.sub("[^a-zA-Z0-9_]", "_", s)
    if not re.match('\d', s) is None:
        s = number_prefix+s
    return unicode(s)
    
class Table2array(object):
    def __init__(self, filename, name="CSV", **kwargs):
        """
        :Arguments:
           *filename*
              CSV file
           *name*
              name of the table
           *autoconvert*
              EXPERIMENTAL. ``True``: replace certain values
              with special python values (see :class:`convert.Autoconverter`) and possibly 
              split values into lists (see *sep*).
              ``False``: leave everything as it is (numbers as numbers and strings 
              as strings).
           *mode*
              mode of the :class:`~convert.Autoconverter`
        """
        self.name = name
        self.autoconvert = Autoconverter(**kwargs).convert
        csvtab = csv.reader(open(filename, "rb"))
        self.names = [make_python_name(s,default=n) for n,s in enumerate(csvtab.next())]
        # read the rest after the column headers
        self.records = [tuple(map(self.autoconvert, line)) for line in csvtab if len(line) > 0]

    def recarray(self):
        """Returns data as :class:`numpy.recarray`."""
        return numpy.rec.fromrecords(self.records, names=self.names)
