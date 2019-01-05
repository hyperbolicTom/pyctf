#! /usr/bin/env python

"""Command line utility to calculate and report on head positions
from .hc files."""

from __future__ import print_function

import sys, os
import numpy as np
import pyctf

if len(sys.argv) < 2:
    print('usage: %s dataset ...' % sys.argv[0])
    sys.exit()
dslist = sys.argv[1:]

l = []
for dsname in dslist:
    ds = pyctf.dsopen(dsname)
    t = ds.r.time
    coilPos = ds.dewar
    l.append((t, coilPos, ds.setname))

l.sort(key = lambda x: x[0])

coilTimes = [x[0] for x in l]
coilPosList = np.array([x[1] for x in l])

if len(l) == 0:
    print("no .hc info")
    sys.exit()

fmt = '%s %.3g %.3g %.3g'
def pr(cp):
    print(fmt % ('na', cp[0][0], cp[0][1], cp[0][2]))
    print(fmt % ('le', cp[1][0], cp[1][1], cp[1][2]))
    print(fmt % ('re', cp[2][0], cp[2][1], cp[2][2]))

def fuzz(a):
    b = a.flatten()
    for i in range(len(b)):
        if np.abs(b[i]) < 1e-6:
            b[i] = 0.
    b.shape = a.shape
    return b

i = 0
for t, coilPos, setname in l:
    print()
    print("%d: dewar coordinates (cm) for %s at %s" % (i, setname, t))
    pr(coilPos)
    i += 1

def avgPosList(poslist):
    """poslist is a list of indices into coilPosList"""
    if len(poslist) > len(coilPosList):
        print("Too many positions.")
        return None
    coilPos = coilPosList[poslist].sum(axis = 0) / len(poslist)
    return coilPos

def position(poslist):
    coilPos = avgPosList(poslist)
    print()
    print("Average measured head position in dewar coordinates (cm)")
    pr(coilPos)
    fid = pyctf.fid.fid(coilPos[0], coilPos[1], coilPos[2])
    head = [pyctf.fid.fid_transform(fid, x) for x in coilPos]
    coilPos = np.array(head)
    print()
    print("fiducials in head coordinates (cm)")
    pr(fuzz(coilPos))

def movement(p0, p1):
    a = coilPosList[p0]
    b = coilPosList[p1]

    d = a - b
    d1 = np.sqrt((d * d).sum(axis = 1))
    m = np.sqrt((d * d).sum() / 3.)

    oa = a[2] + (a[1] - a[2]) / 2.
    ob = b[2] + (b[1] - b[2]) / 2.
    d = oa - ob
    d2 = np.sqrt((d * d).sum())

    print()
    print('from position', p0, 'to', p1)
    print(fmt % ('coil movements (cm) (na, le, re)', d1[0], d1[1], d1[2]))
    print('average movement (cm) %.3g' % d1.mean())
    print('origin movement (cm) %.3g' % d2)
    print('RMS movement (cm) %.3g' % m)

n = range(len(coilPosList))
position(n)

while 1:
    print()
    print('Enter a list of positions (0-%d) to average: ' % (len(coilPosList) - 1), end = '')
    sys.stdout.flush()
    l = sys.stdin.readline().split()
    if len(l) == 0:
        break
    n = np.array(list(map(int, l)))
    position(n)
    movement(n[0], n[-1])

