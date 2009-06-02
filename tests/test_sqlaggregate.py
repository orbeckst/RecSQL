import numpy
_numpyversion = map(int, numpy.version.version.split('.'))
if _numpyversion[0] < 1:
    raise ImportError('Need at least numpy 1.x, only have %r' % numpy.version.version)
if _numpyversion[1] < 1:
    # we want a histogram that returns edges
    def histogram1d(*args,**kwargs):
        _range = kwargs.pop('range',None)
        if not _range is None:
            kwargs['range'] = (_range,)   # needs to be a sequence
        h,e = numpy.histogramdd(*args,**kwargs)
        return h,e[0]
    histogram1d.__doc__ = "1D histogram, based on numpy histogramdd; returns edges as in numpy 1.1.x\n"+\
                        numpy.histogram.__doc__    
else:
    # once deprecation for new=True sets in we can catch this here
    def histogram1d(*args,**kwargs):
        kwargs['new'] = True
        h,e = numpy.histogram(*args,**kwargs)
        return h,e
    histogram1d.__doc__ = numpy.histogram.__doc__
    

from sqlfunctions import regularized_function

class _NumpyHistogram(object):
    def __init__(self):
        self.is_initialized = False
        self.data = []
    def step(self,x,bins,xmin,xmax):
        if not self.is_initialized:
            self.bins = bins
            self.range = (xmin,xmax)
            self.is_initialized = True
        self.data.append(x)
    def finalize(self):
        hist,edges = histogram1d(self.data,bins=self.bins,range=self.range,
                                     normed=False)
        #return adapt_object((hist,edges))
        return hist,edges

class _NormedNumpyHistogram(_NumpyHistogram):
    def finalize(self):
        hist,edges = histogram1d(self.data,bins=self.bins,range=self.range,
                                     normed=True)
        #return adapt_object((hist,edges))
        return hist,edges


class _FunctionHistogram(_NumpyHistogram):
    def __init__(self):
        _NumpyHistogram.__init__(self)
        self.y = []
    def step(self,x,y,bins,xmin,xmax):
        _NumpyHistogram.step(self,x,bins,xmin,xmax)
        self.y.append(y)
    def finalize(self):
        raise NotImplementedError("_FunctionHistogram must be inherited from.")
        # return adapt_object( (...,...,...) )

class _StdHistogram(_FunctionHistogram):
    """Old version, new one simply uses regularized_function()."""
    def finalize(self):
        y = numpy.array(self.y)
        _sum,edges = histogram1d(self.data,bins=self.bins,range=self.range,
                                 weights=y,normed=False)
        _sumsquare,edges = histogram1d(self.data,bins=self.bins,range=self.range,
                                           weights=y*y,normed=False)
        _N,edges = histogram1d(self.data,bins=self.bins,range=self.range,
                                   normed=False)
        _mean = numpy.nan_to_num(_sum/_N)    # N=0 bins -> 0/0 -> nan -> 0
        _Nminusone = _N - 1
        _Nminusone[_Nminusone < 0] = 0    # avoid negative counts, just in case 
        _variance = numpy.nan_to_num(_sumsquare/_Nminusone)
        _std = numpy.sqrt(_variance - _mean*_mean)
        return (_std, edges)
        #return adapt_object((_std,edges))

class _ZscoreHistogram(_FunctionHistogram):
    """Z-score of the weights in each bin abs(Y - <Y>)/std(Y). 
    Takes TWO column arguments: value and weight"""
    def Zscore(self,v):
        m = v.mean()
        s = v.std()
        return numpy.nan_to_num( numpy.mean(numpy.abs(v - m))/s )

    def finalize(self):
        #return adapt_object(\
        return  regularized_function(self.data,self.y,self.Zscore,bins=self.bins,range=self.range)
        #)


class _MaxHistogram(_FunctionHistogram):
    """Max value of the weights in each bin. 
    Takes TWO column arguments: value and weight"""
    def finalize(self):
        def _max(v):
            try:
                return numpy.max(v)
            except ValueError:  # empty array
                return numpy.nan
        return regularized_function(self.data,self.y,_max,bins=self.bins,range=self.range)



data = numpy.random.randn(1000,2)

def do_func_hist(obj=_ZscoreHistogram()):
    #F = _StdHistogram()
    #F = _ZscoreHistogram()
    #F = _MaxHistogram()

    for x,y in data:
        obj.step(x,y,30,0,3)

    result = obj.finalize()
    return result

def do_hist(obj=_NumpyHistogram()):
    for x,y in data:
        obj.step(x,30,0,3)

    result = obj.finalize()
    return result




