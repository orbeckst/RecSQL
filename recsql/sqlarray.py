# $Id: sqlarray.py 3345 2009-04-17 23:12:37Z oliver $
# Copyright (C) 2009 Oliver Beckstein <orbeckst@gmail.com>
# Released under the GNU Public License, version 3 or higher (your choice)

"""sqlarray is a thin wrapper around pysqlite SQL tables. The main
feature is that SELECT queries return numpy.recarrays. In addition,
numpy arrays can be stored in sql columns.

A number of additional SQL functions are defined.
"""

import re
from pysqlite2 import dbapi2 as sqlite
import numpy
from sqlutil import adapt_numpyarray, convert_numpyarray,\
    adapt_object, convert_object

sqlite.register_adapter(numpy.ndarray,adapt_numpyarray)
sqlite.register_adapter(numpy.recarray,adapt_numpyarray)
sqlite.register_adapter(numpy.core.records.recarray,adapt_numpyarray)
sqlite.register_adapter(tuple,adapt_object)
sqlite.register_adapter(list,adapt_object)
sqlite.register_converter("NumpyArray", convert_numpyarray)
sqlite.register_converter("Object", convert_object)


class SQLarray(object):
    """A SQL table that returns (mostly) rec arrays.

    The SQLarray object populates a SQL table from a numpy record array. The SQL
    table is held in memory and functions are provided to run SQL queries and
    commands on the underlying database. Queries return record arrays if
    possible (although a flag can explicitly change this).

    Queries are cached to improve performance.

    The SQL table is named on initialization. Later one can refer to this table
    by the name '__self__' in SQL statements. Additional tables can be added to
    the same database (by using the connection keyword of the constructor)

    Note that this SQL database has a few additional functions defined in
    addition to the SQL standard. These can be used in SELECT statements and
    often avoid post-processing of record arrays in python. It is relatively
    straightforward to add new functions (see the source code and in particular
    the _init_sql_functions(); the functions themselves are defined in the
    module sqlfunctions).


    :Simple SQL functions:
    
    Simple functions transform a single input value into a single output value:

      y = f(x)               SELECT f(x) AS y 

    sqrt(x)                  squareroot math.sqrt(x)
    fformat(format,x)        string formatting of a single value format % x


    :Aggregate SQL functions: 

    Aggregate functions combine data from a query; they are typically used with
    a 'GROUP BY col' clause. They can be thought of as numpy ufuncs.

      y = f(x1,x2,...xN)     SELECT f(x) AS y ... GROUP BY x

    avg(x)                   mean [sqlite builtin]
    std(x)                   standard deviation (using N-1 variance)
    median(x)                median of the data (see numpy.median)
    min(x)                   minimum [sqlite builtin]
    max(x)                   maximum [sqlite builtin]

    :PyAggregate SQL functions:
    
    PyAggregate functions act on a list of data points in the same way as
    ordinary aggregate functions but they return python objects such as numpy
    arrays, or tuples of numpy arrays (eg bin edges and histogram). In order to
    make this work, specific types have to be declared when returning the
    results:

    For instance, the histogram() function returns a python Object, the tuple
    (histogram, edges):

       a.sql('SELECT histogram(x) AS "x [Object]" FROM __self__', asrecarray=False)

    The return type ('Object') needs to be declared with the 'AS "x [Object]"'
    syntax (note the quotes). (See more details in the pysqlite2 documentation
    under 'adaptors' and 'converters'.)

    --------------- -------------- --------------------------------------------
    PyAggregate       type           signature, description
    --------------- -------------- --------------------------------------------
    array             NumpyArray     array(x)
                                     a standard numpy array
    histogram         Object         histogram(x,nbins,xmin,xmax) 
                                     histogram x in nbins evenly spaced bins between xmin and xmax
    distribution      Object         distribution(x,nbins,xmin,xmax) 
                                     normalized histogram whose integral gives 1
    meanhistogram     Object         meanhistogram(x,y,nbins,xmin,xmax)
                                     histogram data points y along x and average all y in each bin
    stdhistogram      Object         stdhistogram(x,y,nbins,xmin,xmax)
                                     give the standard deviation (from N-1 variance)
                                     std(y) = sqrt(Var(y)) with Var(y) = <(y-<y>)^2>
    medianhistogram   Object         medianhistogram((x,y,nbins,xmin,xmax)
                                     median(y)
    minhistogram      Object         minhistogram((x,y,nbins,xmin,xmax)
                                     min(y)
    maxhistogram      Object         maxhistogram((x,y,nbins,xmin,xmax)
                                     max(y)
    zscorehistogram   Object         zscorehistogram((x,y,nbins,xmin,xmax)
                                     <abs(y-<y>)>/std(y)


    Examples of using types in tables:

    # declare types as 'NumpyArray':
    >>>  a.sql("CREATE TABLE __self__(a NumpyArray)")
    # then you can simply insert python objects (type(my_array) == numpy.ndarray)
    >>>  a.sql("INSERT INTO __self__(a) values (?)", (my_array,))
    
    # when returning results of declared columns one does not have to do anything:    
    >>>  (my_array,) = a.sql("SELECT a FROM __self__")
    # although one can also do
    >>>  (my_array,) = q.sql('SELECT a AS "a [NumpyArray]" FROM __self__')
    # but when using a PyAggregate the type must be declared
    >>>   a.sql('SELECT histogram(x,10,0.0,1.5) as "hist [Object]" FROM __self__')

    """
    tmp_table_name = '__tmp_merge_table'  # reserved name (see merge())

    def __init__(self,name,recarray,cachesize=5,connection=None,is_tmp=False):
        """Build the SQL table from a numpy record array.

        T = SQLarray(<name>,<recarray>,cachesize=5,connection=None)

        :Arguments:
        name        table name (can be referred to as __self__ in SQL queries)
        recarray    numpy record array that describes the layout and initializes the
                    table
        cachesize   number of (query, result) pairs that are chached
        connection  if not None, reuse this connection; this adds a new table to the same 
                    database, which allows more complicated queries with cross-joins. The 
                    table's connection is available as the attribute T.connection. 
        is_tmp      False: default, True: create a tmp table
        """
        self.name = str(name)
        if self.name == self.tmp_table_name and not is_tmp:
            raise ValueError('name = %s is reserved, choose another one' % name)
        if connection is None:
            self.connection = sqlite.connect(':memory:', detect_types=sqlite.PARSE_DECLTYPES | sqlite.PARSE_COLNAMES)
            self._init_sqlite_functions()   # add additional functions to database
        else:
            self.connection = connection    # use existing connection
        self.cursor = self.connection.cursor()
        self.columns = recarray.dtype.names
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
        self.cursor.executemany(SQL,recarray)
        self.__cache = KRingbuffer(cachesize)

    def recarray():
        doc = """Return underlying SQL table as a read-only record array."""
        def fget(self):
            return self.SELECT('*')
        return locals()
    recarray = property(**recarray())

    def merge(self,recarray):
        """Merge another recarray with the same columns into this table.
        
        n = a.merge(<recarray>)

        :Arguments:
        recarray    numpy record array that describes the layout and initializes the
                    table

        :Returns:
        n           number of inserted rows

        Raises an exception if duplicate and incompatible data exist
        in the main table and the new one.
        """
        len_before = len(self)
        #  CREATE TEMP TABLE in database
        tmparray = SQLarray(self.tmp_table_name, recarray, 
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

        n = a.merge_table(<name>)

        Executes as 'INSERT INTO __self__ SELECT * FROM <name>'.
        However, this method is probably used less often than the simpler merge(recarray).

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
        """Execute a simple SQL SELECT statement and return values as new numpy rec array.

        The arguments <fields> and the additional optional arguments
        are simply concatenated with additional SQL statements
        according to the template

           SELECT <fields> FROM __self__ [args]

        The simplest fields argument is "*".

        :Example:

        result = T.SELECT("surname, subject, year, avg(grade) AS avg_grade",
                          "WHERE avg_grade < 3", "GROUP BY surname,subject",
                          "ORDER BY avg_grade,surname")

        The resulting SQL would be

          SELECT surname, subject, year, avg(grade) AS avg_grade FROM __self__
               WHERE avg_grade < 3
            GROUP BY surname,subject
            ORDER BY avg_grade,surname

        Note how one can use aggregate functions such avg().

        The string '__self__' is automatically replaced with the table
        name (T.name); this can be used for cartesian products such as

              LEFT JOIN __self__ WHERE ...
        """
        SQL = "SELECT "+str(fields)+" FROM __self__ "+ " ".join(args)
        return self.sql(SQL,**kwargs)
    SELECT = sql_select

    def sql(self,SQL,asrecarray=True):
        """Execute sql statement (NO SANITY CHECKS). If possible, the
        returned list of tuples is turned into a numpy record array,
        otherwise the original list of tuples is returned.

        The last cachesize queries are cached and are returned
        directly unless the table has been modified.

        Note: __self__ is substituted with the table name. See the doc
        string of the select() method for more details.
        """
        SQL = SQL.replace('__self__',self.name)

        # cache the last N (query,result) tuples using a 'FIFO-dict'
        # of length N, where key = SQL; if query in dict AND cache
        # valid just return cache result.
        if SQL in self.__cache:
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
                pass  # keep as tuples if we cannot convert
        else:
            pass      # keep as tuples/data structure as requested
        self.__cache.append(SQL,result)
        return result

    def limits(self,variable):
        """Return minimum and maximum of variable across all rows of data."""
        (vmin,vmax), = self.SELECT('min(%(variable)s), max(%(variable)s)' % vars())
        return vmin,vmax

    def selection(self,SQL,**kwargs):
        """Return a new SQLarray from a SELECT selection."""
        # TODO: under development
        # - could use VIEW
        # - names might clash (because all in the same db); use md5 of
        #   selection or similar (see AdK code)

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
        # (note: MUST replace __self__ and __data__ before md5!)
        _sql = _sql.replace('__self__', self.name)
        # unique name for table
        newname = kwargs.pop('name', 'selection_'+md5.new(_sql).hexdigest())
        kwargs['asrecarray'] = True
        rec_tmp = self.sql(_sql,**kwargs)
        return SQLarray(newname, rec_tmp, connection=self.connection)
        
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
        """Ring buffer of size capacity; 'pushes' data from left and discards
        on the right.
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
        """Ringbuffer that can be treated as a list. Note that the real queuing
        order is only obtained with the tolist() method.

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
        

