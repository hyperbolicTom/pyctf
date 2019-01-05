#! /usr/bin/env python

import sys, os
from pylab import *
from numpy import fromfile
from pyctf.thd_atr import afni_open, afni_header_read
from pyctf.util import *

usage("""[options] -b "lo hi" activebrik [controlbrik]

Display a time-frequency plot of the data stored in the named AFNI brik.
Normalization is done as follows: if this is a statistical brik (i.e., one
that has been thresholded by 3dWilcoxon or similar) then no normalization is
done.

If a control brik is specified, it is used to normalize the active brik.
Otherwise, the default is to normalize by the time average; you can suppress
that using -n none. In either case, the plot is logarithmic unless you say
-e, in which case it straight power (i.e., based on zero); use this if you
want to emphasize power increases.

The -b option is not optional. The TF brik will be averaged across the band,
and the result plotted.

Other options:

    -t title    The title for the plot. Defaults to the marker name(s).

    -r "lo hi"  Upper and lower bounds for the y axis.

    -s file     Save the plot in the named file. Extension defaults to .png.

    -o file     Save the timeseries in the named file as text.
""")

optlist, args = parseargs("t:n:er:s:b:o:")

titlestr = None
norm = 'default'
logscale = True
rlo = None
blo = None
plotfile = None
outfile = None

for opt, arg in optlist:
    if opt == '-t':
        titlestr = arg
    elif opt == '-n':
        norm = arg
    elif opt == '-e':
        logscale = False
    elif opt == '-r':
        s = arg.split()
        if len(s) != 2:
            printerror("-r needs two numbers in quotes")
            printusage()
            sys.exit(1)
        rlo = float(s[0])
        rhi = float(s[1])
    elif opt == '-b':
        s = arg.split()
        if len(s) != 2:
            printerror("-b needs two numbers in quotes")
            printusage()
            sys.exit(1)
        blo = float(s[0])
        bhi = float(s[1])
    elif opt == '-s':
        plotfile = arg
    elif opt == '-o':
        outfile = arg

if len(args) < 1 or blo is None:
    printusage()
    sys.exit(1)

def read_brik(brikname):
    h = afni_header_read(brikname)

    hn = h['HISTORY_NOTE']
    tfdim = hn.find('tfdim:')
    if tfdim < 0:
        printerror("Brik %s doesn't contain TF data." % brikname)
        sys.exit(1)
    tfdim = hn[tfdim:]
    title = hn.find('tftitle:')
    if title < 0:
        tftitle = brikname
    else:
        tftitle = hn[title + 9:].split('\n')[0]

    dim = h['DATASET_DIMENSIONS']

    isstat = hn.find('3dWilcoxon') >= 0 or hn.find('3dMannWhitney') >= 0

    # Format is 'tfdim: start end srate lo hi'
    # Also return xdim and ydim.
    s = tfdim.split()
    return [tftitle, float(s[1]), float(s[2]), float(s[3]), float(s[4]),
            float(s[5]), int(dim[0]), int(dim[1]), isstat]

dual = False
brikname = args[0]
l = read_brik(brikname)
[marker, start, end, srate, lo, hi, xdim, ydim, isstat] = l
if len(args) == 2:
    dual = True
    contbrikname = args[1]
    l2 = read_brik(contbrikname)
    if l[3:] != l2[3:]:
        printerror("brik parameters do not match")
        sys.exit(1)

if blo > hi or blo < lo or bhi > hi or bhi < lo or blo > bhi:
    printerror("band limits must be between %g and %g" % (lo, hi))
    sys.exit(1)

if titlestr is None:
    titlestr = marker
    if titlestr == "None":
        titlestr = brikname
    if dual:
        titlestr = "%s / %s" % (marker, l2[0])

titlestr += " -- %g to %g Hz" % (blo, bhi)

#def avg_over_time(s):
#    """Average over time and return an array of the same size
#    where each column (time point) is the same."""
#
#    x = add.reduce(s, 1) / s.shape[1]
#    x.shape = (x.shape[0], 1)
#    x = repeat(x, s.shape[1], 1)
#    return x

# Read the BRIK file(s).

f = afni_open(brikname, 'BRIK')
s = fromfile(f, dtype = 'f')
s.shape = (ydim, xdim)
f.close()
if dual:
    f = afni_open(contbrikname, 'BRIK')
    s2 = fromfile(f, dtype = 'f')
    s2.shape = (ydim, xdim)
    f.close()

# Normalization

if isstat:
    pass
elif dual:
    s = s - s2
    if not logscale:
        s = exp(s)
elif 'default'.startswith(norm):
    if not logscale:
        s = exp(s)

ylabel = 'Power'
if logscale:
    ylabel = 'log(Power)'

figure()

n = min(minimum.reduce(s))
m = max(maximum.reduce(s))

# Sanity check.
if n == m:
    printerror("brik contains no data")
    sys.exit(0)

if rlo is not None:
    n = rlo
    m = rhi

freq = linspace(lo, hi, s.shape[0])
time = linspace(start, end, s.shape[1])

i = freq.searchsorted(blo)
j = freq.searchsorted(bhi)
x = s[i:j+1].mean(axis = 0)

if outfile is not None:
    f = open(outfile, 'w')
    for o in zip(time, x):
        f.write("%g %g\n" % o)
    f.close()
    sys.exit()

plot(time, x)

ax = gca()
title(titlestr, x = 0, horizontalalignment = 'left', fontsize = 15)
ax.set_xlabel('Time (s)')
ax.set_ylabel(ylabel)
ax.set_xlim(start, end)
if rlo is not None:
    ax.set_ylim(rlo, rhi)

if plotfile is None:
    show()
else:
    (root, ext) = os.path.splitext(plotfile)
    if len(ext) > 0:
        savefig(plotfile)
    else:
        savefig("%s%s%s" % (plotfile, os.path.extsep, "png"))
