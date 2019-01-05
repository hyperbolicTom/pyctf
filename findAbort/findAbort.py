#! /usr/bin/env python

import sys, os.path, getopt
import pyctf

__usage = """dataset

Find the location of an "abort" by detecting when the system clock
goes to zero and stays there. The time (in seconds) of the last
non-zero sample is output."""

__scriptname = os.path.basename(sys.argv[0])

def printerror(s):
    sys.stderr.write("%s: %s\n" % (__scriptname, s))

def printusage():
    sys.stderr.write("usage: %s %s\n" % (__scriptname, __usage))

def parseargs(opt):
    try:
        optlist, args = getopt.getopt(sys.argv[1:], opt)
    except Exception, msg:
        printerror(msg)
        printusage()
        sys.exit(1)
    return optlist, args

optlist, args = parseargs("")

for opt, arg in optlist:
    pass

if len(args) != 1:
    printusage()
    sys.exit(1)

dsname = args[0]
ds = pyctf.dsopen(dsname)

T = ds.getNumberOfTrials()
if T > 1:
    printerror("This dataset has more than one trial.") # @@@ use last trial!
    sys.exit(1)

ch = ds.getChannelIndex("SCLK01")
d = ds.getDsRawData(0, ch)                              # @@@ (T, ch)

if d[-1] != 0.:
    printerror("This dataset does not appear to end with zero.")
    sys.exit(1)

l = d.tolist()
samp = l.index(0.)
t = ds.getTimePt(samp)

if l[samp + 1] != 0.:
    printerror("""There is a zero at time point %g,
however the next time point is not zero.
Cannot continue.""")
    sys.exit(1)

# Output the time of the last non-zero sample.

t = ds.getTimePt(samp - 1)
print(t)
