"""
:mod:`recsql.convert` --- converting entries of tables
======================================================

.. autoclass:: Autoconverter
   :members: __init__
.. function:: Autoconverter.convert(x)
 
              Convert *x* (if in the active state)
.. attribute:: Autoconverter.active

               If set  to ``True`` then conversion takes place; ``False`` 
               just returns :func:`besttype` applid to the value.

.. autofunction:: besttype

"""
import re

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
                 and does the stuff that "singlet does [TODO]
             "unicode"
                 convert all entries with :func:`unicode`             

         *mapping*
              any dict-like mapping that supports lookup. If``None`` then the
              hard-coded defaults are used.
         *active* or *autoconvert*
              initial state of the :attr:`Autoconverter.active` toggle.
             ``False`` deactivates any conversion. [``True``]
          *sep*
              character to split on (produces lists); use ``True`` or ``None``
              (!) to split on all white space.
        """
        self._convertors = {'unicode': unicode,
                            'simple': besttype,
                            'singlet': self._convert_singlet,
                            'fancy': self._convert_fancy,
                            }

        if mapping is None:
            mapping = {'---': None, 'None':None, 'none':None, '':None,
                       'True':True, 'x': True, 'X':True, 'yes':True,
                       'False':False, 'no': False, '-':False}
        self.mapping = mapping
        self.mode = mode
        self.__active = None
        self.active = kwargs.pop('autoconvert', active)   # 'autoconvert' is a "strong" alias or 'active'
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
        x = besttype(s)
        try:
             return self.mapping[x]
        except KeyError:
             return x

    def _convert_fancy(self, field):
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

def besttype(x):
    """Convert string x to the most useful type, i.e. int, float or   str.

    If x is a quoted string (single or double quotes) then the quotes
    are stripped and the enclosed string returned.

    .. Note:: Strings will be returned as Unicode strings (using
              :func:`unicode`).
    """
    try:
        x = x.strip()
    except AttributeError:
        pass
    m = re.match(r"""['"](?P<value>.*)["']$""", str(x))
    if m is None:
        # not a quoted string, try different types
        for converter in int, float, unicode:   # try them in increasing order of lenience
            try:
                return converter(x)
            except ValueError:
                pass
    else:
        # quoted string
        x = unicode(m.group('value'))
    return x
    
