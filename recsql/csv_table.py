"""
:mod:`recsql.csv_table` --- Parse a simple CSV table
====================================================

Turn a CSV table into a numpy array.

Uses :mod:`csv` (requires python 2.6 or better).

.. autoclass:: Table2array
   :members: __init__, recarray
.. autofunction:: make_python_name

"""
from __future__ import with_statement

# notes on csv (from http://farmdev.com/talks/unicode/)
# encode temp. to utf-8
#   s_bytes = s_uni.encode('utf-8')
#   do stuff
#   s_bytes.decode('utf-8')

try:
    # needs python >= 2.6
    import csv
except ImportError:
    import warnings
    warnings.warn("csv module not available (needs python >=2.6)", category=ImportWarning)
    # ... just go ahead and fail later miserably ...
import numpy
import re

from .convert import Autoconverter

# from the csv examples: http://docs.python.org/library/csv.html#csv-examples
import codecs

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


def make_python_name(s, default=None, number_prefix='N',encoding="utf-8"):
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
    return unicode(s, encoding)

class Table2array(object):
    """Read a csv file and provide conversion to a :class:`numpy.recarray`.

    * Depending on the arguments, autoconversion of values can take
      place. See :class:`recsql.convert.Autoconverter` for details.

    * Table column headers are always read from the first row of the file.

    * Empty rows are discarded.
    """
    def __init__(self, filename=None, tablename="CSV", encoding="utf-8", **kwargs):
        """Initialize the class.

        :Arguments:

           *filename*
              CSV file (encoded with *encoding*)
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
        if filename is None:
            raise TypeError("filename is actually required")
        self.tablename = tablename
        self.autoconvert = Autoconverter(**kwargs).convert
        csvtab = UnicodeReader(open(filename, "rb"), encoding=encoding)
        self.names = [make_python_name(s,default=n,encoding=encoding) for n,s in enumerate(csvtab.next())]
        # read the rest after the column headers
        self.records = [tuple(map(self.autoconvert, line)) for line in csvtab \
                            if len(line) > 0 and not numpy.all(numpy.array(line) == '')]

    def recarray(self):
        """Returns data as :class:`numpy.recarray`."""
        return numpy.rec.fromrecords(self.records, names=self.names)

