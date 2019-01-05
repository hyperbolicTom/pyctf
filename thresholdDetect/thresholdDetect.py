#! /usr/bin/env python

import sys, os, tempfile
from math import floor
import numpy as np
import pyctf
from pyctf.util import *

usage("""-m mark [--mc color] [-b|--band "lo hi"] [-i] [-a <amplThres>]
    [-d <derivThres>] [--dt <deadTime>] [-t <trial>] [--twin "t0 t1"] -c channel dataset

    This program scans the specified channel of a dataset and marks the
    samples where the specified thresholds are exceeded. If an existing
    marker name is used, it replaces the original.

    -m mark sets the marker name. --mc sets the marker color.

    With --band (or -b), a bandpass filter is applied to the data first,
    which can help to remove noise.

    -i inverts the data, so a positive threshold will detect descending data.

    Prior to thresholding, the channel data is scaled to the range [0, 1].
    Therefore -a (amplitude threshold) values should be between 0 and 1.
    -d values specify a derivative threshold and are in the range [-1, 1];
    negative derivative thresholds specify downward threshold crossings.
    -a defaults to .5 and -d defaults to .1.

    --tlim can be used to limit autoscaling to the specified time window (s).

    Both amplitude and derivative thresholds must be exceeded to create a mark.

    --dt deadtime, specify the minimum time (s) between marks (default .1).

    -t trial, process only the given trial.

    -c channel  -- only one channel may be specified
""")

def round(x):
    return int(floor(x + .5))

optlist, args = parseargs("m:b:ia:d:t:c:C:", ["mc=", "band=", "dt=", "tlim="])

dsname = None
channel = None
mark = None
mark_color = None
invert = False
ampThresh = .5
derivThresh = .1
trial = None        # all trials
lo = None
hi = None
deadTime = .1
t0 = None

for opt, arg in optlist:
    if opt == '-m':
        mark = arg
    elif opt == '-C' or opt == '--mc':
        mark_color = arg
    elif opt == '-i':
        invert = True
    elif opt == '-b' or opt == '--band':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -b "lo hi"')
            printusage()
            sys.exit(1)
        lo, hi = map(float, s)
    elif opt == '-a':
        ampThresh = float(arg)
    elif opt == '-d':
        derivThresh = float(arg)
    elif opt == '--dt':
        deadTime = float(arg)
    elif opt == '-t':
        trial = int(arg)
    elif opt == '-c':
        channel = arg
    elif opt == '--tlim':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: --tlim "t0 t1"')
            printusage()
            sys.exit(1)
        t0, t1 = map(float, s)

if len(args) == 1:
    dsname = args[0]

if dsname is None:
    printerror("Please specify an input dataset.")
    printusage()
    sys.exit(1)

if channel is None:
    printerror("Please specify a channel to scan.")
    printusage()
    sys.exit(1)

if mark is None:
    printerror("Please specify the marker to create.")
    printusage()
    sys.exit(1)

if deadTime <= 0:
    printerror("--dt value must be positive.")
    sys.exit(1)

ds = pyctf.dsopen(dsname)

srate = ds.getSampleRate()
ntrials = ds.getNumberOfTrials()
nsamp = ds.getNumberOfSamples()
ch = ds.channel[channel]

deadSamp = round(deadTime * srate) - 1
if t0 is not None:
    t0 = round(t0 * srate)
    t1 = round(t1 * srate)

if lo is not None:
    filt = pyctf.mkiir(lo, hi, srate)
    ##filt = pyctf.mkfft(lo, hi, srate, nsamp)

# output mark list, trial and time
marklist = []

# list of trials to process
if trial is None:
    trl = range(ntrials)
else:
    trl = [trial]

def dydx(d):
    "first difference"
    return d[1:] - d[:-1]

def scale_data(d):
    "scale to 0..1"
    return (d - d.min()) / (d.max() - d.min())

def scale_deriv(d):
    "scale postive values to to 0..1, negative values to -1..0"
    return np.where(d >= 0., d / d.max(), d / -(d.min()))

for tr in trl:
    x = ds.getDsRawData(tr, ch)
    if t0 is not None:
        x = x[t0 : t1 + 1]  # data to use when scaling
    if lo is not None:
        x = pyctf.dofilt(x, filt)
    if invert:
        x = -x
    d = dydx(x)
    x = scale_data(x)
    #with open("/tmp/moo", "w") as f:
    #    for v in x: f.write("%g\n" % v)
    d = scale_deriv(d)
    #with open("/tmp/mu", "w") as f:
    #    for v in d: f.write("%g\n" % v)

    if derivThresh < 0.:
        d = -d
        derivThresh = -derivThresh
    if t0 is None:
        s = 1
        e = nsamp - 1
    else:
        y = np.zeros(nsamp)
        y[t0 : t1 + 1] = x
        x = y
        s = t0 + 1
        e = t1 - 1
    while s < e:
        if x[s] > ampThresh and d[s] > derivThresh:
            marklist.append((tr, s / srate))
            s += deadSamp
        s += 1

fd, name = tempfile.mkstemp()
f = os.fdopen(fd, 'w')
for tr, t in marklist:
    f.write("%d %g\n" % (tr, t))
f.close()

if mark_color:
    cmd = "addMarker -f -n %s -l %s -p %s %s" % (mark, mark_color, name, dsname)
else:
    cmd = "addMarker -f -n %s -p %s %s" % (mark, name, dsname)
print(run(cmd, raw = True).decode())

run("rm -f %s" % name)
