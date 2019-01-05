#! /usr/bin/env python

import sys, getopt
import numpy as np
##import h5py
import pyctf
from dual import dual

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category = FutureWarning)
    import h5py

__usage = """[-D] -d ds -h hdf -w wts -p projections

Reads a dataset in .hdf5 format and a SAM weight file in .wts or .fwd format
(from MEG dataset ds), and creates projections. With -D, use the dual basis."""

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

optlist, args = parseargs("Dd:h:w:p:")

dsname = hdfname = wtsfile = projfile = Dflag = None
for opt, arg in optlist:
    if opt == '-d':
        dsname = arg
    elif opt == '-D':
        Dflag = True
    elif opt == '-h':
        hdfname = arg
    elif opt == '-w':
        wtsfile = arg
    elif opt == '-p':
        projfile = arg

if dsname is None or hdfname is None or wtsfile is None or projfile is None:
    printusage()
    sys.exit(1)

ds0 = pyctf.dsopen(dsname)
wts, affine = ds0.readwts(wtsfile)
M = wts.shape[-1]

if Dflag:
    wts = dual(wts)

ds = h5py.File(hdfname)
head = ds['head']

srate = head['srate'].value
marks = head['marks'][:].tolist()
t0, t1 = head['time'][:]
lo, hi = head['band'][:]
trialmarks = head['trialmarks'][:].tolist()

D = ds['trials'].value
typ = D[0].dtype.char

#if typ == 'D':  # complex
#    D = D.real
#    typ = 'd'

s = D.shape
ntrials = s[0]  # number of trials
M1 = s[1]       # number of channels
nsamp = s[2]    # number of samples

if M1 != M:
    printerror("wrong number of weights for this dataset")
    sys.exit(1)

"""
# Concatenate all the segments for one mark together.

mark = '9r2'
l = len(filter(lambda x: x == mark, trialmarks))
d = np.zeros((1, M, l * nsamp))
j = 0
for i in range(ntrials):
    if trialmarks[i] == mark:
        d[0, :, j : j + nsamp] = D[i, :, :]
        j += nsamp
D = d
nsamp = j
ntrials = 1
"""

#from random import shuffle

idx = range(wts.shape[0])
if affine:
    idx = []
    for x1 in range(wts.shape[2]):
        for y1 in range(wts.shape[1]):
            for z1 in range(wts.shape[0]):
                i = (z1, y1, x1)
                if wts[i].sum() != 0.:      # throw out zero voxels
                    idx.append(i)
# if -n:
#                shuffle(wts[i])
else:
    idx = range(wts.shape[0])

nvox = len(idx)

proj = h5py.File(projfile, 'w')
ds.copy(head, proj)
pHead = proj['head']
shape = (nvox,)
if affine:
    pHead['affine'] = affine
    shape = wts.shape[:3]
pHead['shape'] = shape
pHead['idx'] = idx

print('Projecting data')

H = np.zeros((nvox, ntrials, nsamp), dtype = 'd')

def p0(h, d):
    return h.dot(d)
def p1(h, d):
    return abs(h.dot(d))

p = p0
if typ == 'D':
    p = p1

nvox = 0
for i in idx:
    h = wts[i]
    v = list(map(lambda d: p(h, d), D))
    H[nvox, ...] = v
    nvox += 1
    print(i)

proj['H'] = H
