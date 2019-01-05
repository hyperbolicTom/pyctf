#! /usr/bin/env python

import os, sys
from pyctf import dsopen
from pyctf import ctf

dsname = sys.argv[1]
ds = dsopen(dsname)

srate = ds.getSampleRate()
ntrial = ds.getNumberOfTrials()
nsamp = ds.getNumberOfSamples()
nch = ds.getNumberOfChannels()

print(ntrial)

meg4name = ds.getDsFileNameExt(".meg4")
size = os.stat(meg4name).st_size - 8

res4name = ds.getDsFileNameExt(".res4")
r = ctf.read_res4_structs(res4name)

# Get ntrials from size of dataset:
ntrial = size / (nsamp * 4 * nch)

print('new ntrial is', ntrial)

g = list(r.genRes)
g[ctf.gr_numTrials] = ntrial
r.genRes = g

ctf.write_res4_structs(res4name, r)
