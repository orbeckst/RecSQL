import numpy

# gaussian, but random order
N = 10000
x = 10*(numpy.random.permutation(N)/(1.0*N) - 0.5)
y = numpy.exp(-x*x/4.)

Nbins = 20
bins = numpy.linspace(-6,6,Nbins)
midpoints = 0.5*(bins[:-1]+bins[1:])

# no harm in pre-sorting:
sorting_index = numpy.argsort(x)
sx = x[sorting_index]
sy = y[sorting_index]

# sx_k = bins.searchsorted(sx)
# sx_regularized = midpoints[bin_index -1 ]  #  why -1 ? ... but must be done

# boundaries in SORTED data that demarcate bins
# position in bin_index is the bin number
bin_index = numpy.r_[sx.searchsorted(bins[:-1], 'left'),
                     sx.searchsorted(bins[-1], 'right')]

# naive implementation: apply operator to each bin separately (figure
# out a way to to this numpy style later; average is simple because
# one can use cumsum and diff)
# It's not clear to me how one could effectively block this procedure because
# there does not seem to be a general way to combine the chunks for different blocks,
# eg func=median

#func = numpy.mean
func = numpy.median
#func = numpy.std
F = numpy.zeros(len(bins)-1)  # final function
# N = numpy.zeros(len(bins)-1)  # counts (histogram)
# for ibin,start,stop in zip(numpy.arange(len(bins)-1),bin_index[:-1],bin_index[1:]):
#     chunk = sy[start:stop]
#     N[ibin] = len(chunk)
#     F[ibin] = func(chunk)

F[:] = [func(sy[start:stop]) \
            for ibin,start,stop in zip(numpy.arange(len(bins)-1),bin_index[:-1],bin_index[1:])]

import pylab
pylab.plot(x,y,'ro',alpha=0.1,hold=True)
pylab.plot(midpoints,F,'w-',hold=True)
    


# numpy implementation for reference
# (can only do weighted sum, i.e. func = numpy.sum)
def whisto(x,y,bins):
    a = numpy.asarray(x)
    weights = numpy.asarray(y)
    block = 65536
    zero = numpy.array(0, dtype=weights.dtype)
    for i in numpy.arange(0, len(a), block):
        tmp_a = a[i:i+block]
        tmp_w = weights[i:i+block]
        sorting_index = numpy.argsort(tmp_a)
        sa = tmp_a[sorting_index]
        sw = tmp_w[sorting_index]
        cw = numpy.concatenate(([zero,], sw.cumsum()))
        bin_index = numpy.r_[sa.searchsorted(bins[:-1], 'left'), \
                              sa.searchsorted(bins[-1], 'right')]
        n += cw[bin_index]

    n = numpy.diff(n)
    return n, bins

