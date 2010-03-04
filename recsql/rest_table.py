# $Id$
"""
:mod:`recsql.rest_table` --- Parse a simple reST table
======================================================

Turn a `restructured text simple table`_ into a numpy array. See the Example_
below for how the table must look like. The module allows inclusion of
parameters and data in the documentation itself in a natural way. Thus the
parameters are automatically documented and only exist in a single place. The
idea is inspired by `literate programming`_ and is embodied by the DRY_ ("Do not
repeat yourself") principle.

.. _restructured text simple table:
    http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#simple-tables
.. _literate programming:
    http://en.wikipedia.org/wiki/Literate_programming
.. _DRY:
    http://c2.com/cgi/wiki?DontRepeatYourself

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
* Autoconversion of list fields might not always work...


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

The only class that the user really needs to know anything about is
:class:`recsql.rest_table.Table2array`.

.. autoclass:: Table2array
   :members: __init__, recarray

.. autoclass:: Autoconverter
   :members: __init__
.. function:: Autoconverter.convert(x)
 
              Convert *x* (if in the active state)
.. attribute:: Autoconverter.active

               If set  to ``True`` then conversion takes place; ``False`` 
               just returns :func:`besttype` applid to the value.

.. autofunction:: besttype

.. autoexception:: ParseError

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

    If a value is quote with single or double quotation marks then the
    outermost quotation marks are stripped and the enclosed value treated as a string.

    .. Note:: Values such as 001 must be quoted as '001' or they will be
              interpreted as integers (1 in this case).
    """
    
    def __init__(self, string, autoconvert=False, automapping=None, sep=None):
        """Table2array(string) --> parser

        :Arguments:
           *string*
              string to be parsed
           *autoconvert*
              EXPERIMENTAL. ``True``: replace certain values
              with special python values (see :class:`Autoconvert`) and possibly 
              split values into lists (see *sep*).
              ``False``: leave everything as it is (numbers as numbers and strings 
              as strings).
           *sep*
              If set and *autoconvert* = ``True`` then split field values on the
              separator (using :func:`split`) before possible autoconversion.
        """
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

        self.autoconvert = Autoconverter(active=autoconvert, mapping=automapping, sep=sep).convert

    def parse(self):
        """Parse the table data string into records."""

        self.parse_fields()
        records = []
        for line in self.t['data'].split('\n'):
            if EMPTY_ROW.match(line):
                continue
            row = [self.autoconvert(line[start_field:end_field+1])
                   for start_field, end_field in self.fields]
            records.append(tuple(row))
        self.records = records

    def recarray(self):
        """Return a recarray from the (parsed) string."""

        if self.records is None:
            self.parse()
        try:
            # simple
            return numpy.rec.fromrecords(self.records, names=self.names)
        except ValueError:
            # complicated because fromrecords cannot deal with records of lists
            # Quick hack: use objects for lists etc (instead of building the proper
            # data types (see docs for numpy.dtype , eg dtype('coord', (float, 3)) )

            D = numpy.empty(len(self.records[0]), dtype=object)    # number of fileds from first record
            types = numpy.array([map(type, r) for r in self.records])  # types of all fields
            for icol, isSame in enumerate([numpy.all(col) for col in types.T]):
                if isSame:
                    D[icol] = types[0][icol]
                else:
                    D[icol] = object
            dtype = numpy.dtype(zip(self.names, D))
            # from numpy.rec.records (for debugging...)
            retval = numpy.array(self.records, dtype=dtype)
            res = retval.view(numpy.recarray)
            ## res.dtype = numpy.dtype((numpy.rec.record, res.dtype))  # fails -- but we don't need it
            return res

    def parse_fields(self):
        """Determine the start and end columns and names of the fields."""

        rule = self.t['toprule'].rstrip()  # keep leading space for correct columns!!
        if not (rule == self.t['midrule'].rstrip() and rule == self.t['botrule'].rstrip()):
            raise ParseError("Table rules differ from each other (check white space).")
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

class Autoconverter(object):
    """Automatically convert an input value to a special python object.

    The :meth:`Autoconverter.convert` method turns the value into a special
    python value and casts strings to the "best" type (see :func:`besttype`). 

    The defaults for the conversion of a input field value to a
    special python value are:

      ===========  ===============
      value        python
      ===========  ===============
        '---'       ``None``
        'none'
        'None'
        ''

        'True'      ``True``
        'x'
        'X'
        'yes'

        'False'     ``False``
        '-'
        'no'
      ===========  ===============

    If the *sep* keyword is set to a string instead of ``False`` then
    values are split into tuples. Probably the most convenient way to
    use this is to set *sep* = ``True`` (or ``None``) because this
    splits on all white space whereas *sep* = ' ' would split multiple
    spaces.

    **Example**
       - With *sep* = ``True``: 'foo bar 22  boing ---' --> ('foo', 'boing', 22, None)
       - With *sep* = ',':       1,2,3,4 --> (1,2,3,4) 
   
    """

    def __init__(self, mapping=None, active=True, sep=False):
        """Initialize the converter.

        :Arguments:
        - *mapping*: any dict-like mapping that supports lookup. If
          ``None`` then the hard-coded defaults are used.
        - *active* = True. initial state of the
          :attr:`Autoconverter.active` toggle.
        - *sep*: character to split on (produces lists);
                 use ``True`` or ``None`` (!) to split on all white space.
        """
        if mapping is None:
            mapping = {'---': None, 'None':None, 'none':None, '':None,
                       'True':True, 'x': True, 'X':True, 'yes':True,
                       'False':False, 'no': False, '-':False}
        self.mapping = mapping
        self.__active = None
        self.active = active
        if sep is True:
            sep = None   # split on *all* white space, sep=' ' splits spaces!
        self.sep = sep

    def active():
        doc = """Toggle the state of the Autoconverter."""
        def fget(self):
            return self.__active
        def fset(self, x):
            self.__active = x
            if self.__active:
                self.convert = self._convert   # py types + bools + lists 
            else:
                self.convert = besttype        # always convert to int/float/str
        return locals()
    active = property(**active())

    def _convert(self, field):
        """Convert to a list (sep != None) and convert list elements."""
        if self.sep is False:
            return self._convert_singlet(field)
        else:
             x = tuple([self._convert_singlet(s) for s in field.split(self.sep)])
             if len(x) == 0:
                 x = ''
             elif len(x) == 1:
                 x = x[0]
             return x

    def _convert_singlet(self, s):
        x = besttype(s)
        try:
             return self.mapping[x]
        except KeyError:
             return x

def besttype(x):
    """Convert string x to the most useful type, i.e. int, float or   str.

    If x is a quoted string (single or double quotes) then the quotes
    are stripped and the enclosed string returned.
    """
    try:
        x = x.strip()
    except AttributeError:
        pass
    m = re.match(r"""['"](?P<value>.*)["']$""", str(x))
    if m is None:
        # not a quoted string, try different types
        for converter in int, float, str:   # try them in increasing order of lenience
            try:
                return converter(x)
            except ValueError:
                pass
    else:
        # quoted string
        x = str(m.group('value'))
    return x
    
