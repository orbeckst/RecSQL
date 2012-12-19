"""
:mod:`recsql.convert` --- converting entries of tables and arrays
=================================================================

.. autoclass:: Autoconverter
   :members: __init__

   .. function:: convert(x)

                 Convert *x* (if in the active state)

   .. attribute:: active

                 If set  to ``True`` then conversion takes place; ``False``
                 just returns :func:`besttype` applid to the value.

.. autofunction:: besttype
.. autofunction:: to_unicode
.. autofunction:: irecarray_to_py
.. autofunction:: pyify
.. autofunction:: to_pytypes
"""

import re

def to_unicode(obj, encoding='utf-8'):
    """Convert obj to unicode (if it can be be converted)

    from http://farmdev.com/talks/unicode/"""
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

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

    .. rubric:: Example

    - With *sep* = ``True``: 'foo bar 22  boing ---' --> ('foo', 'boing', 22, None)
    - With *sep* = ',':       1,2,3,4 --> (1,2,3,4)

    """

    def __init__(self, mode="fancy",  mapping=None, active=True, sep=False, **kwargs):
        """Initialize the converter.

        :Arguments:

          *mode*
             defines what the converter does

                "simple"
                    convert entries with :func:`besttype`
                "singlet"
                    convert entries with :func:`besttype` and apply
                    mappings
                "fancy"
                    first splits fields into lists, tries mappings,
                    and does the stuff that "singlet" does
                "unicode"
                    convert all entries with :func:`to_unicode`

          *mapping*
              any dict-like mapping that supports lookup. If ``None`` then the
              hard-coded defaults are used
          *active* or *autoconvert*
              initial state of the :attr:`Autoconverter.active` toggle.
              ``False`` deactivates any conversion. [``True``]
           *sep*
              character to split on (produces lists); use ``True`` or ``None``
              (!) to split on all white space.
           *encoding*
              encoding of the input data [utf-8]
           *percentify*
              convert "34.4%" into 0.344 [``True``]

        """
        self._convertors = {'unicode': unicode,
                            'simple': besttype,
                            'singlet': self._convert_singlet,
                            'fancy': self._convert_fancy,
                            }
        self.convert = None  # convertor function; set when self.active <-- True.
        if mapping is None:
            mapping = {'---': None, 'None':None, 'none':None, '':None,
                       'True':True, 'x': True, 'X':True, 'yes':True,
                       'False':False, 'no': False, '-':False}
        self.mapping = mapping
        self.encoding = kwargs.pop('encoding', "utf-8")
        self.percentify = kwargs.pop('percentify', True)
        self.mode = mode
        self.__active = None
        self.active = kwargs.pop('autoconvert', active)   # 'autoconvert' is a "strong" alias of 'active'
        if sep is True:
            sep = None   # split on *all* white space, sep=' ' splits single spaces!
        self.sep = sep

    def active():
        doc = """Toggle the state of the Autoconverter. ``True`` uses the mode, ``False`` does nothing"""
        def fget(self):
            return self.__active
        def fset(self, x):
            self.__active = x
            if self.__active:
                self.convert = self._convertors[self.mode]
            else:
                self.convert = lambda x: x     # do nothing
        return locals()
    active = property(**active())

    def _convert_singlet(self, s):
        x = besttype(s, encoding=self.encoding, percentify=self.percentify)
        try:
            return self.mapping[x]
        except KeyError:
            return x

    def _convert_fancy(self, field):
        """Convert to a list (sep != None) and convert list elements."""
        if self.sep is False:
            x = self._convert_singlet(field)
        else:
            x = tuple([self._convert_singlet(s) for s in field.split(self.sep)])
            if len(x) == 0:
                x = ''
            elif len(x) == 1:
                x = x[0]
        #print "%r --> %r" % (field, x)
        return x

def besttype(x, encoding="utf-8", percentify=True):
    """Convert string x to the most useful type, i.e. int, float or unicode string.

    If x is a quoted string (single or double quotes) then the quotes are
    stripped and the enclosed string returned. The string can contain any
    number of quotes, it is only important that it begins and ends with either
    single or double quotes.

    *percentify* = ``True`` turns "34.4%" into the float 0.344.

    .. Note:: 

       Strings will be returned as Unicode strings (using
       :func:`unicode`), based on the *encoding* argument, which is
       utf-8 by default.

    """
    def unicodify(x):
        return to_unicode(x, encoding)
    def percent(x):
        try:
            if x.endswith("%"):
                x = float(x[:-1]) / 100.
            else:
                raise ValueError
        except (AttributeError, ValueError):
            raise ValueError
        return x

    x = unicodify(x)  # make unicode as soon as possible
    try:
        x = x.strip()
    except AttributeError:
        pass
    m = re.match(r"""(?P<quote>['"])(?P<value>.*)(?P=quote)$""", x)  # matches "<value>" or '<value>' where <value> COULD contain " or '!
    if m is None:
        # not a quoted string, try different types
        for converter in int, float, percent, unicodify:   # try them in increasing order of lenience
            try:
                return converter(x)
            except ValueError:
                pass
    else:
        # quoted string
        x = unicodify(m.group('value'))
    return x


def to_int64(a):
    """Return view of the recarray with all int32 cast to int64."""
    # build new dtype and replace i4 --> i8
    def promote_i4(typestr):
        if typestr[1:] == 'i4':
            typestr = typestr[0]+'i8'
        return typestr

    dtype = [(name, promote_i4(typestr)) for name,typestr in a.dtype.descr]
    return a.astype(dtype)

def pyify(typestr):
    """Return a Python :class:`type` that most closely represents the type encoded by *typestr*"""
    if typestr[1] in 'iu':
        return int
    elif typestr[1] == 'f':
        return float
    elif typestr[1] == 'S':
        return str
    return lambda x: x

def to_pytypes(a):
    """Return array *a* with all types set to basic Python types.

    :func:`pyify` is applied to all ``dtypes`` of the
    :class:`numpy.ndarray` and then recast with
    :meth:`numpy.ndarray.astype`. This approach can loose precision.
    """
    dtype = [(name, pyify(typestr)) for name,typestr in a.dtype.descr]
    return a.astype(dtype)

def irecarray_to_py(a):
    """Slow conversion of a recarray into a list of records with python types.

    Get the field names from :attr:`a.dtype.names`.

    :Returns: iterator so that one can handle big input arrays
    """
    pytypes = [pyify(typestr) for name,typestr in a.dtype.descr]
    def convert_record(r):
        return tuple([converter(value) for converter, value in zip(pytypes,r)])
    return (convert_record(r) for r in a)
