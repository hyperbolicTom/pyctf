import numpy
import pyctf
from pyctf import fid

# Continuous head localization channels.

fids = ['Na', 'Le', 'Re']
chans = {fids[0]: ['HLC0011', 'HLC0012', 'HLC0013'],
         fids[1]: ['HLC0021', 'HLC0022', 'HLC0023'],
         fids[2]: ['HLC0031', 'HLC0032', 'HLC0033']}

def getHM(ds, t, chan):
    if chan not in fids:
        raise KeyError("no such channel %s" % chan)
    i = fids.index(chan)
    o = ds.head[i]
    c = chans[chan]
    d = ds.channel

    # make an nx3; one channel per column

    l = []
    for ch in c:
        x = ds.getDsData(t, d[ch])
        x.shape = (x.shape[0], 1)
        l.append(x)
    d = numpy.hstack(l) * 100. # m -> cm

    # Transform to relative head coordinates.
    # fid.fid_transform() only does one vector, but
    # we can do the whole array just as easily.

    m = ds.dewar_to_head    # 4x4 transform
    r = m[0:3, 0:3]         # 3x3 rotation
    t = m[0:3, 3]           # translation
    d = numpy.inner(d, r) + t - o # - o makes relative to .hc origin

    return d

#    d = ds.channel
#    if chan in fids:
#        i = fids.index(chan)
#        o = ds.dewar[i] * .01
#        c = chans[chan]
#        x = ds.getDsData(t, d[c[0]]) - o[0]
#        y = ds.getDsData(t, d[c[1]]) - o[1]
#        z = ds.getDsData(t, d[c[2]]) - o[2]
#        rms = numpy.sqrt(x * x + y * y + z * z) * 100.
#        a = numpy.min(rms)
#        b = numpy.max(rms)
#        arrow = ""
#        if b > .5:
#            arrow = "<--"
#        print(t, chan, a, b, arrow)
