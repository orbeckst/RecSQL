# $Id$
"""
:mod:`recsql.rest_table` --- Parse a simple reST table
======================================================

Turn a restructured text simple table into a numpy array.

Limitations
-----------

* All data on a single line.
* Headings must be single words as they are used as column names.
* The delimiters are used to extract the fields. Only data within the range of 
  the '=====' markers is used.
* Markers must be separated by at least two spaces.
* The keyword 'Table' must precede the first marker line.

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
  rec.array([(u'A. Einstein', 42, 1921), (u'P. Dirac', 31, 1933),
       (u'R. P. Feynman', 47, 1965)], 
      dtype=[('name', '<U52'), ('age', '<i4'), ('year', '<i4')])

"""



import re
import numpy

# search expression
re_FLAGS = re.VERBOSE | re.DOTALL | re.MULTILINE
TABLE = re.compile("""
                   ^[ \t]*Table(\[(?P<name>\w*)\])?:\s*(?P<title>[^\n]*)[ \t]*$     # title line required
                   [\n]+
                   ^(?P<toprule>[ \t]*==+[ \t=]+)[ \t]*$     # top rule
                   [\n]+
                   ^(?P<fields>[\w\t ]+?)$                # field names (columns), must only contain A-z0-9_
                   [\n]+
                   ^(?P<midrule>[ \t]*==+[ \t=]+)[ \t]*$     # mid rule
                   [\n]+
                   (?P<data>.*?)                    # all data across multiple lines
                   [\n]+
                   ^(?P<botrule>[ \t]*==+[ \t=]+)[ \t]*$     # bottom rule
                   """,  re_FLAGS)

# HEADER = re.compile("""
#                    ^[ \t]*Table(\[(?P<name>\w*)\])?:\s*(?P<title>[^\n]*)[ \t]*$     # title line required
#                    [\n]+
#                    ^(?P<rest>[^\n]+)$
#                     """, re_FLAGS)

# RULE = re.compile("""
#                    ^(?P<botrule>[ \t]*==+[ \t=]+)[ \t]*$     # bottom rule
#                    """,  re_FLAGS)


class ParseError(Exception):
    """Signifies a failure to parse."""

class Table2array(object):
    """Primitive parser that converts a simple reST table into numpy.rearray.

    The table must be the only table in the text. It must look similar to the
    example below (variable parts in angle brackets, optional in double
    brackets, everything else must be there, matching is case sensitive, '....'
    signfies repetition in kind)::

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

    .. method:: Table2array(string) --> parser
    .. attribute:: tablename
            <NAME> of the table.
    .. attribute:: caption
            <CAPTION> of the table.
    .. attribute:: records
            parsed table as records
    """
    def __init__(self, string):
        self.string = string
        m = TABLE.search(string)
        if m is None:
            raise ParseError('Table cannot be parsed.')
        self.t = m.groupdict()
        self.tablename = self.t['name']
        self.caption = self.t['title']

    def parse(self):
        """Parse the string into records."""

        self.parse_fields()
        records = []
        for line in self.t['data'].split('\n'):
            row = [besttype(line[start_field:end_field+1])
                   for start_field, end_field in self.fields]
            records.append(tuple(row))
        self.records = records

    def recarray(self):
        """Return a recarray from the (parsed) string."""

        if not hasattr(self, 'records'):
            self.parse()
        return numpy.rec.fromrecords(self.records, names=self.names)

    def parse_fields(self):
        """Determine the start and end columns and names of the fields."""

        rule = self.t['toprule']    # hope that they are all the same...
        names = self.t['fields'].split()
        nfields = len(rule.split())
        if nfields != len(names):
            raise ParseError('number of field names does not match number of fields')
        fields = []     #  list of tuples (first,last) column of the field
        ifield = 0
        is_field = rule.startswith('=')  # state
        len_rule = len(rule)
        start_field = 0
        end_field = 0
        for c in xrange(len_rule):
            char = rule[c]
            if char == '=' and not is_field:
                start_field = c
                is_field = True
            if (char == ' ' or c == len_rule-1) and is_field:
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
    
