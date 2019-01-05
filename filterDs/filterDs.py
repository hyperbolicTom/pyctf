#! /usr/bin/env python

import sys, getopt
from math import floor
import numpy as np
##import h5py
import pyctf
from pyctf.st import hilbert
from pyctf.segments import get_segment_list

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category = FutureWarning)
    import h5py

__usage = """-d dataset [-n] [-h] -b "lo hi" -m mark... -t "t0 t1" -o hdf5name

Read a dataset, bandpass filter it, and save it as an hdf5 file.
With -h, save the Hilbert transform.
With -n, substitute real data with realistic noise."""

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

def round(x):
    return int(floor(x + .5))

optlist, args = parseargs("d:nhb:m:t:o:")

dsname = None
mlist = []
hdfname = None
do_hilbert = False
noise = False

for opt, arg in optlist:
    if opt == '-d':
        dsname = arg
    elif opt == '-n':
        noise = True
    elif opt == '-h':
        do_hilbert = True
    elif opt == '-b':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -b "lo hi"')
            printusage()
            sys.exit(1)
        lo, hi = map(float, s)
    elif opt == '-m':
        mlist.extend(arg.split())
    elif opt == '-t':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -t "t0 t1"')
            printusage()
            sys.exit(1)
        t0, t1 = map(float, s)
    elif opt == '-o':
        hdfname = arg

if dsname is None:
    printerror("Please specify an input dataset.")
    printusage()
    sys.exit(1)

if hdfname is None:
    printerror("Please specify an output filename.")
    printusage()
    sys.exit(1)

ds = pyctf.dsopen(dsname)

srate = ds.getSampleRate()
nsamp = ds.getNumberOfSamples()
M = ds.getNumberOfPrimaries()
marks = ds.marks

seglist = []
seglen = -1
for m in mlist:
    sl, slen = get_segment_list(ds, m, t0, t1)
    for tr, s in sl:
        seglist.append((tr, s, m))
    if seglen < 0:
        seglen = slen
    else:
        assert seglen == slen

# Sort by trial [0] and time [1].
seglist.sort(key = lambda x: (x[0], x[1]))

# Python3 needs to know what type the strings are.
h5str = h5py.special_dtype(vlen = str)

f = h5py.File(hdfname, 'w')
f['head/srate'] = srate
f['head/marks'] = np.array(mlist, dtype = h5str)
f['head/time'] = [t0, t1]
f['head/band'] = [lo, hi]
f['head/noise'] = noise
f['head/hilbert'] = do_hilbert
trialmarks = []

#filt = pyctf.mkiir(lo, hi, srate)
filt = pyctf.mkfft(lo, hi, srate, nsamp)

if noise:
    from pyctf.meg_noise import meg_noise

ntrials = len(seglist)
Tr = 0
lasttr = None
dtyp = 'd'
if do_hilbert:
    dtyp = 'D'

trials = f.create_dataset("trials", (ntrials, M, seglen), dtype = dtyp)
d = np.zeros((M, nsamp), dtype = dtyp)

for tr, s, m in seglist:
    if tr != lasttr:
        # read and filter the next trial
        print('Trial %d' % tr)
        D = ds.getPriArray(tr)
        for ch in range(M):
            x = D[ch, :] * 1e12     # convert to picoTesla
            x -= x.mean()
            if noise:
                x = meg_noise(nsamp) * x.std()
            x = pyctf.dofilt(x, filt)
            if do_hilbert:
                x = hilbert(x)
            d[ch, :] = x
        lasttr = tr

    # Copy each segment to the hdf file.

    trials[Tr, ...] = d[:, s : s + seglen]
    trialmarks.append(m)
    Tr += 1

f['head/trialmarks'] = np.array(trialmarks, dtype = h5str)

f.close()
