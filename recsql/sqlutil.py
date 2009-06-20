# $Id: sqlutil.py 2346 2008-10-06 19:36:21Z oliver $
# Copyright (C) 2009 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License, version 3 or higher (your choice)

"""Helper functions that are used throughout the SQLarray package."""

import cPickle

# storing numpy arrays in the db as pickles
def adapt_numpyarray(a):
    return cPickle.dumps(a,protocol=0)  # must use text protocol for use with sqlite

def convert_numpyarray(s):
    return cPickle.loads(s)

def adapt_object(a):
    return cPickle.dumps(a,protocol=0)  # must use text protocol for use with sqlite

def convert_object(s):
    return cPickle.loads(s)

# declare types as 'NumpyArray':
#   cur.execute("CREATE TABLE test(a NumpyArray)")
#   cur.execute("INSERT INTO test(a) values (?)", (my_array,))
# or as column types
#   cur.execute('SELECT a as "a [NumpyArray]" from test')


# Fake* not needed anymore since SQLarray takes an iterable + columns descriptors
# Use FakeRecArray to load the db from an iterable

class FakeDtype(object):
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)

class FakeRecArray(object):
    """Pseudo recarray that is used to feed SQLarray:

    Must only implement:

      recarray.dtype.names         sequence of column names
      iteration                    yield records
    """
    def __init__(self, iterable, columns):
        self.dtype = FakeDtype(names=columns)
        self.iterable = iterable

    def __iter__(self):
        for rec in self.iterable:
            yield rec
