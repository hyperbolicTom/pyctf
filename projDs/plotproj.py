#! /usr/bin/env python

import sys, getopt
from math import floor
import numpy as np
##import h5py
import pyctf
from pyctf.st import hilbert

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category = FutureWarning)
    import h5py

__usage = """-p projections

Reads a projection dataset in .hdf5 format and plots graphs."""

__scriptname = sys.argv[0]

def printerror(s):
    sys.stderr.write("%s: %s\n" % (__scriptname, s))

def printusage():
    sys.stderr.write("usage: %s %s\n" % (__scriptname, __usage))

def parseargs(opt):
    try:
        optlist, args = getopt.getopt(sys.argv[1:], opt)
    except Exception as msg:
        printerror(msg)
        printusage()
        sys.exit(1)
    return optlist, args

optlist, args = parseargs("p:")

projfile = None
for opt, arg in optlist:
    if opt == '-p':
        projfile = arg

if projfile is None:
    printusage()
    sys.exit(1)

def round(x):
    return int(floor(x + .5))

f = h5py.File(projfile)
head = f['head']

srate = head['srate'].value
marks = head['marks'][:].tolist()
t0, t1 = head['time'][:]
lo, hi = head['band'][:]
trialmarks = head['trialmarks'][:].tolist()

H = f['H'].value

s = H.shape
nvox = s[0]     # number of virtual channels
ntrials = s[1]  # number of trials
nsamp = s[2]    # number of samples

#H = H * H

def remove_baseline(x, n):
    a = x[:n].mean()
    x -= a
    return x

# Average all the segments for one mark together.

def doavg(mark):
    s = 0
    j = 0
    for i in range(ntrials):
        if trialmarks[i] == mark:
            #s += H[2, i, :]
            x = H[2, i, :]
            x = abs(hilbert(x))
            s += remove_baseline(x, round(.5 * srate))
            j += 1
    s /= j
    return s

from pylab import plot, show

for m in ['9r0', '9r1', '9r2']:
    s = doavg(m)
    plot(s)
show()
