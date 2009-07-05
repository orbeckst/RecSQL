# $Id: sqlarray.py 3345 2009-04-17 23:12:37Z oliver $
# Copyright (C) 2009 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License, version 3 or higher (your choice)

"""
:mod:`sqlarray` --- Implementation of :class:`SQLarray`
=======================================================

:class:`SQLarray` is a thin wrapper around pysqlite SQL tables. The main
features ares that ``SELECT`` queries can return ``numpy.recarrays`` and the
:meth:`SQLarray.selection` method returns a new :class:`SQLarray` instance.  

numpy arrays can be stored in sql fields which allows advanced table
aggregate functions such as ``histogram``.

A number of additional SQL functions are defined.

:TODO:
   * Make object saveable (i.e. store the database on disk instead of
     memory or dump the memory db and provide a load() method
   * Use hooks for the pickling protocol to make this transparent. 
"""

import re
try:
    from pysqlite2 import dbapi2 as sqlite     # ... all development was with pysqlite2
except ImportError:
    from sqlite3 import dbapi2 as sqlite       # I hope we are compatible with sqlite3
import numpy
from sqlutil import adapt_numpyarray, convert_numpyarray,\
    adapt_object, convert_object
from rest_table import Table2array

sqlite.register_adapter(numpy.ndarray,adapt_numpyarray)
sqlite.register_adapter(numpy.recarray,adapt_numpyarray)
sqlite.register_adapter(numpy.core.records.recarray,adapt_numpyarray)
sqlite.register_adapter(tuple,adapt_object)
sqlite.register_adapter(list,adapt_object)
sqlite.register_converter("NumpyArray", convert_numpyarray)
sqlite.register_converter("Object", convert_object)


class SQLarray(object):
    """A SQL table that returns (mostly) rec arrays.

    .. method:: SQLarray([name[,records[,columns[,cachesize=5,connection=None]]]])

    :Arguments:
       name        
          table name (can be referred to as '__self__' in SQL queries)
       records    
          numpy record array that describes the layout and initializes the
          table OR any iterable (and then columns must be set, too) OR a string
          that contains a single, *simple reStructured text table* (and the table name is
          set from the table name in the reST table.)
          If ``None`` then simply associate with existing table name.
       columns
          sequence of column names (only used if records does not have 
          attribute dtype.names) [``None``]
       cachesize   
          number of (query, result) pairs that are cached [5]
       connection  
          If not ``None``, reuse this connection; this adds a new table to the same 
          database, which allows more complicated queries with cross-joins. The 
          table's connection is available as the attribute T.connection. [``None``]
       is_tmp
          ``True``: create a tmp table; ``False``: regular table in db [``False``] 

    :Bugs:        
       * :exc:`InterfaceError`: *Error binding parameter 0 - probably unsupported type*

         In this case the recarray contained types such as ``numpy.int64`` that are not
         understood by sqlite. You need to convert the data manually first.
    """

    tmp_table_name = '__tmp_merge_table'  # reserved name (see merge())

    def __init__(self,name=None ,records=None, columns=None,
                 cachesize=5, connection=None, is_tmp=False):
        """Build the SQL table from a numpy record array.
        """
        self.name = str(name)
        if self.name == self.tmp_table_name and not is_tmp:
            raise ValueError('name = %s is reserved, choose another one' % name)
        if connection is None:
            self.connection = sqlite.connect(':memory:',
                                             detect_types=sqlite.PARSE_DECLTYPES | sqlite.PARSE_COLNAMES)
            self._init_sqlite_functions()   # add additional functions to database
        else:
            self.connection = connection    # use existing connection
        self.cursor = self.connection.cursor()

        if records is None:
            if name is None:
                raise ValueError("Provide either an existing table name or a source of records.")
            # associate with existing table
            # SECURITY risk: interpolating name...
            SQL = "SELECT * FROM %(name)s WHERE 0" % vars(self)
            c = self.cursor
            try:
                c.execute(SQL)
            except sqlite.OperationalError,err:
                if str(err).find('no such table') > -1 or \
                       str(err).find('syntax error') > -1:
                    raise ValueError("Provide existing legal 'name' of an existing table not %r"
                                     % self.name)
                else:
                    raise
            self.columns = tuple([x[0] for x in c.description])
            self.ncol = len(self.columns)
        else:
            if type(records) is str:
                # maybe this is a reST table
                P = Table2array(records)
                records = P.recarray()
                self.name = P.tablename    # name provided as 'Table[<tablename>]: ...'
            try:
                self.columns = records.dtype.names
            except AttributeError:
                if columns is None:
                    raise TypeError('records must be a recarray or columns should be supplied')
                self.columns = columns  # XXX: no sanity check
            self.ncol = len(self.columns)

            # initialize table
            # * input is NOT sanitized and is NOT safe, don't use as CGI...
            # * this can overwrite an existing table (name is not checked)
            if not is_tmp:
                SQL = "CREATE TABLE "+self.name+" ("+",".join(self.columns)+")"
            else:
                # temporary table
                SQL = "CREATE TEMPORARY TABLE "+self.name+" ("+",".join(self.columns)+")"
            self.cursor.execute(SQL)
            SQL = "INSERT INTO "+self.name+" ("+ ",".join(self.columns)+") "\
                +"VALUES "+"("+",".join(self.ncol*['?'])+")"
            # The next can fail with 'InterfaceError: Error binding parameter 0 - probably unsupported type.'
            # This means that the numpy array should be set up so that there are no data types
            # such as numpy.int64 which are not compatible with sqlite (no idea why).
            self.cursor.executemany(SQL,records)

        # initialize query cache
        self.__cache = KRingbuffer(cachesize)

    def recarray():
        doc = """Return underlying SQL table as a read-only record array."""
        def fget(self):
            return self.SELECT('*')
        return locals()
    recarray = property(**recarray())

    def merge(self,recarray,columns=None):
        """Merge another recarray with the same columns into this table.
        
        :Arguments:
           recarray    
              numpy record array that describes the layout and initializes the
              table

        :Returns:
           n           number of inserted rows
           
        :Raises:
           Raises an exception if duplicate and incompatible data exist
           in the main table and the new one.
        """
        len_before = len(self)
        #  CREATE TEMP TABLE in database
        tmparray = SQLarray(self.tmp_table_name, records=recarray, columns=columns,
                            connection=self.connection, is_tmp=True)
        len_tmp = len(tmparray)
        # insert into main table
        SQL = """INSERT OR ABORT INTO __self__ SELECT * FROM %s""" % self.tmp_table_name
        self.sql(SQL)
        len_after = len(self)
        n_inserted = len_after - len_before
        assert len_tmp == n_inserted
        del tmparray          # also drops the tmp table (keep it at end for debugging)
        return n_inserted

    def merge_table(self,name):
        """Merge an existing table in the database with the __self__ table.

        Executes as ``'INSERT INTO __self__ SELECT * FROM <name>'``.
        However, this method is probably used less often than the simpler :meth:`merge`.

        :Arguments:
           name         name of the table in the database (must be compatible with __self__)
        
        :Returns:
           n            number of inserted rows
        """
        l_before = len(self)
        SQL = """INSERT OR ABORT INTO __self__ SELECT * FROM %s""" % name
        self.sql(SQL)
        l_after = len(self)
        return l_after - l_before

    def sql_index(self,index_name,column_names,unique=True):
        """Add a named index on given columns to improve performance."""
        if type(column_names) == str:
            column_names = [column_names]
        try:
            if len(column_names) == 0:
                raise TypeError
        except TypeError:
            raise ValueError("Provide a list of column names for an index.")
        if unique:
            UNIQUE = "UNIQUE"
        else:
            UNIQUE = ""
        table_name = self.name
        columns = ",".join(column_names)
        SQL = """CREATE %(UNIQUE)s INDEX %(index_name)s ON %(table_name)s """\
            """(%(columns)s)""" % locals()
        self.sql(SQL)

    def sql_select(self,fields,*args,**kwargs):
        """Execute a simple SQL ``SELECT`` statement and returns values as new numpy rec array.

        The arguments *fields* and the additional optional arguments
        are simply concatenated with additional SQL statements
        according to the template::

           SELECT <fields> FROM __self__ [args]

        The simplest fields argument is ``"*"``.

        Example:
           Create a recarray in which students with average grade less than
           3 are listed::

             result = T.SELECT("surname, subject, year, avg(grade) AS avg_grade",
                            "WHERE avg_grade < 3", "GROUP BY surname,subject",
                            "ORDER BY avg_grade,surname")

           The resulting SQL would be::

             SELECT surname, subject, year, avg(grade) AS avg_grade FROM __self__
                  WHERE avg_grade < 3
                  GROUP BY surname,subject
                  ORDER BY avg_grade,surname

           Note how one can use aggregate functions such avg().

           The string *'__self__'* is automatically replaced with the table
           name (``T.name``); this can be used for cartesian products such as ::

              LEFT JOIN __self__ WHERE ...
        """
        SQL = "SELECT "+str(fields)+" FROM __self__ "+ " ".join(args)
        return self.sql(SQL,**kwargs)

    SELECT = sql_select

    def sql(self,SQL,asrecarray=True,cache=True):
        """Execute sql statement. 

        .. warning::
           There are **no sanity checks** applied to the SQL. 

        If  possible, the  returned list  of tuples  is turned  into a
        numpy record  array, otherwise the original list  of tuples is
        returned.

        .. warning::
           Potential BUG: if there are memory issues then it can
           happen that we just silently fall back to a tuple even
           though calling code expects a recarray; because we
           swallowed ANY exception the caller will never know

        The last cachesize queries are cached (for cache=True) and are
        returned directly unless the table has been modified.

        .. Note:: '__self__' is substituted with the table name. See the doc
                  string of the :meth:`SELECT` method for more details.
        """
        SQL = SQL.replace('__self__',self.name)

        # cache the last N (query,result) tuples using a 'FIFO-dict'
        # of length N, where key = SQL; if we can use the cache
        # (cache=True) and if query in dict (AND cache
        # valid, ie it hasn't been emptied (??)) just return cache result.
        if cache and SQL in self.__cache:
            return self.__cache[SQL]

        c = self.cursor
        c.execute(SQL)  # no sanity checks!
        if c.rowcount > 0 or SQL.upper().find('DELETE') > -1:
            # table was (potentially) modified
            # rowcount does not change for DELETE, see 
            # http://oss.itsystementwicklung.de/download/pysqlite/doc/sqlite3.html#cursor-objects
            # so we catch this case manually and invalidate the whole cache
            self.__cache.clear()
        result = c.fetchall()
        if not result:
            return []    # leaving here keeps cache invalidated
        if asrecarray:
            try:
                names = [x[0] for x in c.description]   # first elements are column names
                result = numpy.rec.fromrecords(result,names=names)
            except:
                # XXX: potential BUG: if there are memory issues then it can happen that 
                # XXX: we just silently fall back to a tuple but calling code expects a
                # XXX: recarray; because we swallowed ANY exception the caller will never know
                # XXX: ... should probably change this and not have the try ... except in the first place
                pass  # keep as tuples if we cannot convert
        else:
            pass      # keep as tuples/data structure as requested
        if cache:
            self.__cache.append(SQL,result)
        return result

    def limits(self,variable):
        """Return minimum and maximum of variable across all rows of data."""
        (vmin,vmax), = self.SELECT('min(%(variable)s), max(%(variable)s)' % vars())
        return vmin,vmax

    def selection(self,SQL,parameters=None,**kwargs):
        """Return a new SQLarray from a SELECT selection.

        This is a very useful method because it allows one to build complicated
        selections and essentially new tables from existing data.

        Examples::

                s = selection('a > 3')
                s = selection('a > ?', (3,))
                s = selection('SELECT * FROM __self__ WHERE a > ? AND b < ?', (3, 10))
        """
        # TODO: under development
        # - could use VIEW
        # - might be a good idea to use cache=False

        import md5
        # pretty unsafe... I hope the user knows what they are doing
        # - only read data to first semicolon
        # - here should be input scrubbing...
        safe_sql = re.match(r'(?P<SQL>[^;]*)',SQL).group('SQL')

        if re.match(r'\s*SELECT.*FROM',safe_sql,flags=re.IGNORECASE):
            _sql = safe_sql
        else:
            # WHERE clause only        
            _sql = """SELECT * FROM __self__ WHERE """+str(safe_sql)
        # (note: MUST replace __self__  before md5!)
        _sql = _sql.replace('__self__', self.name)        
        # unique name for table (unless user supplied... which could be 'x;DROP TABLE...')
        newname = kwargs.pop('name', 'selection_'+md5.new(_sql).hexdigest())

        # create table directly
        # SECURITY: unsafe tablename !!!! (but cannot interpolate?)
        _sql = "CREATE TABLE %(newname)s AS " % vars() + _sql
        
        c = self.cursor
        if parameters is None:
            c.execute(_sql)              # no sanity checks!
        else:
            c.execute(_sql, parameters)  # no sanity checks; params should be tuple

        # associate with new table in db
        return SQLarray(newname, None, connection=self.connection)
        
    def _init_sqlite_functions(self):
        """additional SQL functions to the database"""
        import sqlfunctions
                
        self.connection.create_function("sqrt", 1,sqlfunctions._sqrt)
        self.connection.create_function("fformat",2,sqlfunctions._fformat)
        self.connection.create_aggregate("std",1,sqlfunctions._Stdev)
        self.connection.create_aggregate("median",1,sqlfunctions._Median)
        self.connection.create_aggregate("array",1,sqlfunctions._NumpyArray)
        self.connection.create_aggregate("histogram",4,sqlfunctions._NumpyHistogram)
        self.connection.create_aggregate("distribution",4,sqlfunctions._NormedNumpyHistogram)
        self.connection.create_aggregate("meanhistogram",5,sqlfunctions._MeanHistogram)
        self.connection.create_aggregate("stdhistogram",5,sqlfunctions._StdHistogram)
        self.connection.create_aggregate("minhistogram",5,sqlfunctions._MinHistogram)
        self.connection.create_aggregate("maxhistogram",5,sqlfunctions._MaxHistogram)
        self.connection.create_aggregate("medianhistogram",5,sqlfunctions._MedianHistogram)
        self.connection.create_aggregate("zscorehistogram",5,sqlfunctions._ZscoreHistogram)

    def __len__(self):
        """Number of rows in the table."""
        return self.SELECT('COUNT() AS length').length[0]

    def __del__(self):
        """Delete the underlying SQL table from the database."""
        SQL = """DROP TABLE IF EXISTS __self__""" 
        self.sql(SQL)

# Ring buffer (from hop.utilities)
try:
    import collections
    class Fifo(collections.deque):
        pop = collections.deque.popleft

    class Ringbuffer(Fifo):
        """Ring buffer of size capacity; 'pushes' data from left and discards on the right.
        """
        #  See http://mail.python.org/pipermail/tutor/2005-March/037149.html.
        def __init__(self,capacity,iterable=None):
            if iterable is None: iterable = []
            super(Ringbuffer,self).__init__(iterable)
            assert capacity > 0
            self.capacity = capacity
            while len(self) > self.capacity:
                super(Ringbuffer,self).pop()   # prune initial loading
        def append(self,x):
            while len(self) >= self.capacity:
                super(Ringbuffer,self).pop()
            super(Ringbuffer,self).append(x)
        def __repr__(self):
            return "Ringbuffer(capacity="+str(self.capacity)+", "+str(list(self))+")"
except ImportError:
    class Ringbuffer(list):
        """Ringbuffer that can be treated as a list. 

        Note that the real queuing order is only obtained with the
        :meth:`tolist` method.

        Based on
        http://www.onlamp.com/pub/a/python/excerpt/pythonckbk_chap1/index1.html
        """
        def __init__(self, capacity, iterable=None):
            assert capacity > 0
            self.capacity = capacity
            if iterable is None:
                self = []
            else:
                self[:] = list(iterable)[-self.capacity:]

        class __Full(list):
            def append(self, x):
                self[self.cur] = x
                self.cur = (self.cur+1) % self.capacity
            def tolist(self):
                """Return a list of elements from the oldest to the newest."""
                return self[self.cur:] + self[:self.cur]

        def append(self, x):
            super(Ringbuffer,self).append(x)
            if len(self) >= self.capacity:
                self[:] = self[-self.capacity:]
                self.cur = 0
                # Permanently change self's class from non-full to full
                self.__class__ = self.__Full
        def extend(self,iterable):
            for x in list(iterable)[-self.capacity:]:
                self.append(x)
        def tolist(self):
            """Return a list of elements from the oldest to the newest."""
            return self
        def __repr__(self):
            return "Ringbuffer(capacity="+str(self.capacity)+", "+str(list(self))+")"



class KRingbuffer(dict):
    """Ring buffer with key lookup.

    Basically a ringbuffer for the keys and a dict (k,v) that is
    cleaned up to reflect the keys in the Ringbuffer.
    """
    def __init__(self,capacity,*args,**kwargs):
        super(KRingbuffer,self).__init__(*args,**kwargs)
        self.capacity = capacity
        self.__ringbuffer = Ringbuffer(self.capacity,self.keys())
        self._prune()
    def append(self,k,v):
        """x.append(k,v)"""
        self.__ringbuffer.append(k)
        super(KRingbuffer,self).__setitem__(k,v)
        self._prune()
    def clear(self):
        """Reinitialize the KRingbuffer to empty."""
        self.__ringbuffer = Ringbuffer(self.capacity)
        self._prune()
    def _prune(self):
        """Primitive way to keep dict in sync with RB."""
        delkeys = [k for k in self.keys() if k not in self.__ringbuffer]
        for k in delkeys:  # necessary because dict is changed during iterations
            super(KRingbuffer,self).__delitem__(k)
    def __setitem__(self,k,v):
        raise NotImplementedError('Only append() is supported.')
    def __delitem__(self,k):
        raise NotImplementedError('Only pop() is supported.')
    def update(self,*args,**kwargs):
        raise NotImplementedError('Only append() is supported.')
        

