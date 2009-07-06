# $Id$
"""
:mod:`recsql.rest_table` --- Parse a simple reST table
======================================================

Turn a `restructured text simple table`_ into a numpy array. See the Example_
below for how the table must look like. The module allows inclusion of
parameters and data in the documentation itself in a natural way. Thus the
parameters are automatically documented and only exist in a single place. The
idea is inspired by `literate programming`_.

.. _restructured text simple table:
    http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#simple-tables
.. _literate programming:
    http://en.wikipedia.org/wiki/Literate_programming

Limitations
-----------

Note that not the full specifications of the original `restructured
text simple table`_ are supported. In order to keep the parser simple,
the following additional restriction apply:

* All row data must be on a single line.
* Column spans are not supported.
* Headings must be single legal SQL and python words as they are used
  as column names.
* The delimiters are used to extract the fields. Only data within the
  range of the '=====' markers is used. Thus, each column marker
  *must* span the whole range of input. Otherwise, data will be lost.  
* The keyword 'Table' must precede the first marker line and the table
  name must be provided in square brackets; the table name should be a
  valid SQL identifier.
* Currently, only a *single* table can be present in the string.


Example
-------

The following table is converted::

  Table[laureates]: Physics Nobel prize statistics.
  =============  ==========  =========
  name           age         year
  =============  ==========  =========
  A. Einstein    42          1921
  P. Dirac       31          1933
  R. P. Feynman  47          1965
  =============  ==========  =========  

with

  >>> import recsql.rest_table as T
  >>> P = T.Table2array(T.__doc__)
  >>> P.recarray()
  rec.array([(u'A. Einstein', 42, 1921), (u'P. Dirac', 31, 1933),
       (u'R. P. Feynman', 47, 1965)], 
      dtype=[('name', '<U52'), ('age', '<i4'), ('year', '<i4')])


Module content
--------------
.. See the autogenerated content in the online docs or the source code.
"""



import re
import numpy

# search expressions
# ------------------

#: Python regular expression that finds a *single* table in a multi-line string.
TABLE = re.compile("""
                   ^[ \t]*Table(\[(?P<name>\w*)\])?:\s*(?P<title>[^\n]*)[ \t]*$     # 'Table[name]:' is required
                   [\n]+
                   ^(?P<toprule>[ \t]*==+[ \t=]+)[ \t]*$  # top rule
                   [\n]+
                   ^(?P<fields>[\w\t ]+?)$                # field names (columns), must only contain A-z0-9_
                   [\n]+
                   ^(?P<midrule>[ \t]*==+[ \t=]+)[ \t]*$  # mid rule
                   [\n]+
                   (?P<data>.*?)                          # all data across multiple lines
                   [\n]+
                   ^(?P<botrule>[ \t]*==+[ \t=]+)[ \t]*$  # bottom rule
                   """,  re.VERBOSE | re.DOTALL | re.MULTILINE)
#: Python regular expression that detects a empty (non-data) line in a reST table. It acts
#: on a single input line and not a multi-line string.
EMPTY_ROW = re.compile("""
                   ^[-\s]*$       # white-space lines or '----' dividers are ignored (or '-- - ---')
                   """, re.VERBOSE)


class ParseError(Exception):
    """Signifies a failure to parse."""

class Table2array(object):
    """Primitive parser that converts a simple reST table into ``numpy.recarray``.

    The table must be the only table in the text. It must look similar to the
    example below (variable parts in angle brackets, optional in double
    brackets, everything else must be there, matching is case sensitive, '....'
    signifies repetition in kind)::

      Table[<NAME>]: <<CAPTION>>
      ============  ===========  ======================  ....
      <COLNAME 1>   <COLNAME 2>  ....                    ....
      ============  ===========  ======================  ....
      <VALUE>       <VALUE>      <VALUE> <VALUE> ....
      ....
      ....
      ============  ===========  ======================  ....

    Rows may *not* span multiple lines. The column names must be single words
    and legal python names (no spaces, no dots, not starting with a number).

    Field values are converted to one of the following python types: *int*,
    *float*, or *str*.
    """
    
    def __init__(self, string):
        """Table2array(string) --> parser"""
        self.string = string
        m = TABLE.search(string)  # extract table from string with regular expression
        if m is None:
            raise ParseError('Table cannot be parsed.')
        self.t = m.groupdict()
        #: <NAME> of the table
        self.tablename = self.t['name']
        #: <CAPTION> of the table.
        self.caption = self.t['title']
        #: parsed table as records (populate with :meth:`Table2array.parse`)
        self.records = None

    def parse(self):
        """Parse the table data string into records."""

        self.parse_fields()
        records = []
        for line in self.t['data'].split('\n'):
            if EMPTY_ROW.match(line):
                continue
            row = [besttype(line[start_field:end_field+1])
                   for start_field, end_field in self.fields]
            records.append(tuple(row))
        self.records = records

    def recarray(self):
        """Return a recarray from the (parsed) string."""

        if self.records is None:
            self.parse()
        return numpy.rec.fromrecords(self.records, names=self.names)

    def parse_fields(self):
        """Determine the start and end columns and names of the fields."""

        rule = self.t['toprule']
        if not (rule == self.t['midrule'] and rule == self.t['botrule']):
            raise ParseError("Table rules differ from each other.")
        names = self.t['fields'].split()
        nfields = len(rule.split())
        if nfields != len(names):
            raise ParseError("number of field names (%d) does not match number of fields (%d)"
                             % (nfields, len(names)))
        fields = []     #  list of tuples (first,last) column of the field
        ifield = 0
        is_field = rule.startswith('=')  # state
        len_rule = len(rule)
        start_field = 0
        end_field = 0
        for c in xrange(len_rule):
            char = rule[c]
            if not is_field and char == '=':
                start_field = c
                is_field = True
            if is_field and (char == ' ' or c == len_rule-1):
                # finished field
                fields.append((start_field, c))
                ifield += 1
                is_field = False
        self.names = names
        self.fields = fields

def besttype(x):
    """Convert string x to the most useful type, i.e. int, float or str."""
    try:
        x = x.strip()
    except AttributeError:
        pass
    for converter in int, float, str:   # try them in increasing order of lenience
        try:
            return converter(x)
        except ValueError:
            pass
    return x
    
