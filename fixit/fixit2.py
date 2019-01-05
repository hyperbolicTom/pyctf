#! /usr/bin/env python

from __future__ import print_function

import sys, os
from pyctf import dsopen
from pyctf import ctf

if len(sys.argv) < 2:
    print("usage: %s [-f] dataset" % sys.argv[0])
    sys.exit(1)

n = 1
fixit = False
if sys.argv[1][0:2] == '-f':
    fixit = True
    n = 2
dsname = sys.argv[n]
ds = dsopen(dsname)

srate = ds.getSampleRate()
ntrial = ds.getNumberOfTrials()
nsamp = ds.getNumberOfSamples()
nch = ds.getNumberOfChannels()

res4name = ds.getDsFileNameExt(".res4")
r = ctf.read_res4_structs(res4name)

for ch in range(nch):
    sr = list(r.sensRes[ch][0])
    if sr[ctf.sr_type] == ctf.TYPE_UADC:
        print(ds.getChannelName(ch), sr)

if not fixit:
    sys.exit(0)

for ch in range(nch):
    sr, crd, crh = r.sensRes[ch]
    sr = list(sr)
    if sr[ctf.sr_type] == ctf.TYPE_UADC:
        sr[ctf.sr_properGain] = 1.
        sr[ctf.sr_qGain] = 107374182.4
        sr[ctf.sr_ioGain] = 1.
        print(ds.getChannelName(ch), sr)
        r.sensRes[ch] = (sr, crd, crh)

ctf.write_res4_structs(res4name, r)
