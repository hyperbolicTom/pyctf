#! /usr/bin/env python

from __future__ import print_function

import sys, os, tempfile
from pylab import *
import pyctf
from pyctf.util import *
from pyctf.st.smt import calc_tapers, calcbw, mtst, smt
from pyctf.st import st, fft
from pyctf.samiir import mkfft, mkiir, dofilt

usage("""[options] -c channel ... [dataset]

This program produces time-frequency plots using the Stockwell transform.
The default behavior is to average all trials and compute the Stockwell
transform of the average. Each channel is averaged separately and the
resulting Stockwells are averaged together.

For the -m, -c, and -T options, you can specify multiple arguments in
quotes, or use multiple options, or both. In other words,
    -m 'mark1 mark2 mark3'
and
    -m mark1 -m mark2 -m mark3
are equivalent.

You must specify at least one channel to work on.

Options are:

    -d dataset      You can either specify a dataset using -d or as
                    the last argument.

    -m marker       Define trials relative to the specified marker,
                    rather than the dataset's trial structure. You can
                    use more than one marker.

    -t "t0 t1"      The time window (in seconds), relative to the markers,
                    if any. Default: whole trial.

    -b "lo hi"      Frequencies to use. Default: "0 80".

    -a              Compute the average of the Stockwells, rather than
                    the Stockwell of the average.

    -k K            Multitaper smoothing parameter. Default: 0. This is
                    the number of tapers to use. This program uses sine
                    tapers, resulting in a smoothing bandwidth that
                    depends on the length of the time window as well as
                    the number of tapers.

    -c channel      The channel list can be a set of individually
                    specified channels or a prefix such as MLO or ML.
                    There is no default, you need to specify at least
                    one channel.

    -T trial        Only process the specified trial(s). You can
                    specify more than one trial.

    -p              Apply a 60 Hz notch filter.

    -l              Plot the log of the power.

    -n              Normalize by the average across the entire time window.

    -B "t0 t1"      Normalize by the average across the specified baseline
                    time window. The time values are in seconds relative
                    to the left-hand side of the plot! (Implies -n.)

    -D "t0 t1"      Trim the display to be from t0 to t1 (relative to the
                    original axis).

    -r channel      Add an ADC or other channel in a subplot.

    -o prefix       Name of an AFNI output BRIK. Default: display a graph.
                    The BRIK stores the log of the Stockwell, so that
                    subtracting one BRIK (or an average of several
                    BRIKs) from another results in the log of the power
                    ratio of the two conditions.

    --mat matfile   Save the output to a Matlab(tm) file. The file
                    will contain 'st_time', an array describing the time
                    points; 'st_freq', an array describing the frequencies;
                    and 'st_data', the 2D array of log(power).

    -v              Verbose output showing progress.

This is StockwellDs.py version 2.2""")

optlist, args = parseargs("m:t:b:ak:c:npPso:lr:T:d:B:D:v", ["mat="])

dsname = None
mlist = []
clist = []
trlist = []
t0 = None
baset0 = None
dispt0 = None
lo = 0
hi = 80
K = 0
donorm = False
smoothnorm = False
pflag = False
Pflag = False
aflag = False
prefix = None
lflag = False
ref = None
matfile = None
verbose = False

class struct:
    pass

for opt, arg in optlist:
    if opt == '-d':
        dsname = arg
    elif opt == '-m':
        mlist.extend(arg.split())
    elif opt == '-t':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -t "t0 t1"')
            printusage()
            sys.exit(1)
        t0 = float(s[0])
        t1 = float(s[1])
    elif opt == '-B':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -B "t0 t1"')
            printusage()
            sys.exit(1)
        baset0 = float(s[0])
        baset1 = float(s[1])
        donorm = True
    elif opt == '-D':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -D "t0 t1"')
            printusage()
            sys.exit(1)
        dispt0 = float(s[0])
        dispt1 = float(s[1])
    elif opt == '-b':
        s = arg.split()
        if len(s) != 2:
            printerror('usage: -b "lo hi"')
            printusage()
            sys.exit(1)
        lo = float(s[0])
        hi = float(s[1])
    elif opt == '-s':
        smoothnorm = True
    elif opt == '-k':
        K = int(arg)
        if K < 0:
            printerror("K must be >= 0")
            printusage()
            sys.exit(1)
    elif opt == '-c':
        clist.extend(arg.split())
    elif opt == '-T':
        trlist.extend(arg.split())
    elif opt == '-n':
        donorm = True
    elif opt == '-P':
        Pflag = True
    elif opt == '-p':
        pflag = True
    elif opt == '-a':
        aflag = True
    elif opt == '-l':
        lflag = True
    elif opt == '-o':
        prefix = arg
    elif opt == '-r':
        ref = arg
    elif opt == '--mat':
        from matlab import mio
        matfile = arg
    elif opt == '-v':
        verbose = True

if (dsname == None and len(args) != 1) or len(clist) == 0:
    printusage()
    sys.exit(1)

if dsname == None:
    dsname = args[0]
ds = pyctf.dsopen(dsname)

srate = ds.getSampleRate()
ntrials = ds.getNumberOfTrials()
nsamples = ds.getNumberOfSamples()

if ds.isAverage():
    ntrials = 1
    trlist = []

if t0 is None and len(mlist) == 0 and ntrials == 1 and not ds.isAverage():
    # This case is meant to prevent people from trying to Stockwell
    # an entire run. However, we'll allow a single trial, if it's
    # short enough.
    if nsamples > 15 * srate:
        printerror("Trial too long.")
        printerror("You must specify a marker and time window.")
        sys.exit(1)
    else:
        printerror("Note: defaulting to one trial of %d samples." %
                   nsamples)

# The time bounds of the trial.

T0 = ds.getTimePt(0)
T1 = ds.getTimePt(nsamples - 1)

if t0 is None:
    t0 = T0
    t1 = T1
    print("Default time window is %g to %g" % (t0, t1))
    mlist = []
    seglen = nsamples
else:
    seglen = int((t1 - t0) * srate)

# Convert the channel list to dataset indices.

idx = ds.clist2idx(clist)
cnames = ', '.join(clist)
nch = len(idx)

# Look at the markers and construct the list of trials.

marks = ds.marks

for marker in mlist:
    if not marks.get(marker):
        printerror("unknown marker '%s'" % marker)
        sys.exit(1)

if len(mlist) == 0:
    # if no marks, use the start of each trial
    tlist = list(zip(range(ntrials), [0] * ntrials))
else:
    tlist = []
    for marker in mlist:
        tlist.extend(marks[marker])

# Filter out unwanted trials.

if len(trlist) > 0:
    trlist = list(map(int, trlist))
    def intr(t, tr = trlist):
        return t[0] in tr
    tlist = list(filter(intr, tlist))

if len(tlist) == 0:
    printerror("no valid trials!")
    sys.exit(1)

# Convert frequencies in Hz into rows of the ST, given sampling rate and length.

def freq(f):
    return int(f * seglen / srate + .5)

s = 0.
f = 0.
if not aflag:
    s = [0.] * nch

n = 0
maxm = len(tlist)
m = 1

if K > 0:
    tapers = calc_tapers(K, seglen)

# Optionally notch filter the data. @@@ Should really apply all processing parameters.

if pflag:
    lineFilt = mkfft(61., 59., srate, nsamples)

last_tr = None
for tr, t in tlist:
    if t + t0 < T0 or t + t1 > T1:
        continue
    if tr != last_tr:
        D = ds.getIdxArray(tr, idx)
        D *= 1e15 # convert from tesla to femtotesla
        last_tr = tr
        print('trial %d' % tr)
        if pflag:
            for ch in range(nch):
                D[ch, :] = dofilt(D[ch], lineFilt)
    samp = ds.getSampleNo(t + t0)
    for ch in range(nch):
        d = D[ch][samp : samp + seglen]
        if aflag:
            if verbose:
                print(ds.getChannelName(idx[ch]), end = ' ')
                sys.stdout.flush()
            if K == 0:
                if Pflag:
                    s += st(d, freq(lo), freq(hi))
                else:
                    s += abs(st(d, freq(lo), freq(hi)))**2
                    f += abs(fft(d))**2
            else:
                s += mtst(K, tapers, d, freq(lo), freq(hi))
                f += smt(K, d, tapers)
        else:
            s[ch] += d
        n += 1
    if aflag and verbose:
        print()
        print(n)

r = 0.
if ref:
    ch = ds.getChannelIndex(ref)
    for tr, t in tlist:
        if t + t0 < T0 or t + t1 > T1:
            continue
        samp = ds.getSampleNo(t + t0)
        d = ds.getDsRawSegment(tr, ch, samp, seglen)
        r += d

if n == 0:
    printerror("no valid trials!")
    sys.exit(1)
print('%d total epochs, avg. %g per channel' % (n, float(n) / nch))

r /= n
if aflag:
    if Pflag:
        s = abs(s)**2
    else:
        s /= n
        f /= n
else:
    d = 0.
    e = 0.
    for ch in range(nch):
        if verbose:
            print(ds.getChannelName(idx[ch]), end = ' ')
            sys.stdout.flush()
        if K == 0:
            if Pflag:
                d += st(s[ch] / n, freq(lo), freq(hi))
            else:
                d += abs(st(s[ch] / n, freq(lo), freq(hi)))**2
                e += abs(fft(s[ch] / n))**2
        else:
            d += mtst(K, tapers, s[ch] / n, freq(lo), freq(hi))
            e += smt(K, s[ch] / n, tapers)
    if verbose:
        print()
    if Pflag:
        s = abs(d)**2 / nch
    else:
        s = d / nch
        f = e / nch

print('bw =', calcbw(K, seglen, srate))

def writebrik(s, prefix):
    "Write 2D TF data as an AFNI BRIK."

    # dump the array into a file
    fd, tmpfile = tempfile.mkstemp()
    f = os.fdopen(fd, 'wb')
    asarray(s, dtype = 'f').tofile(f)
    f.close()

    # use to3d to create the BRIK file
    sess = os.path.dirname(prefix)
    prefix = os.path.basename(prefix)
    pathname = os.path.join(sess, prefix)
    run("rm -f %s+orig.*" % pathname)
    if sess:
        arg = "-session %s -prefix %s" % (sess, prefix)
    else:
        arg = "-prefix %s" % prefix
    cmd = "to3d -fim %s -xSLAB 0P-%dP -ySLAB 0S-%dS -zFOV 0L-1R 3Df:0:0:%d:%d:1:%s" % \
            (arg, s.shape[1], s.shape[0], s.shape[1], s.shape[0], tmpfile)
    run(cmd + " 2> /dev/null")

    # clean up, and set some fields in the AFNI header.
    os.unlink(tmpfile)
    note = "tfdim: %g %g %g %g %g" % (t0, t1, srate, lo, hi)
    cmd = "3dNotes -h '%s' %s+orig" % (note, pathname)
    run(cmd)
    note = "tftitle: %s %s" % (caption, cnames)
    cmd = "3dNotes -h '%s' %s+orig" % (note, pathname)
    run(cmd)

from pyctf.sensortopo.tics import scale1

def plotst(y, titlestr):
    n = min(minimum.reduce(y))
    m = max(maximum.reduce(y))
#    n = 0
#    m = 9e+6
    nlevels = 40
    clevel = linspace(n, m, nlevels)
    ticks, mticks = scale1(clevel[0], clevel[-1])
    time = linspace(t0, t1, y.shape[1])
##    if dispt0 is not None:
##        time = linspace(dispt0, dispt1, y.shape[1])
    fr = linspace(lo, hi, y.shape[0])
    ref = True
    if ref:
        subplot(211)
    c = contourf(time, fr, y, clevel, cmap = cm.jet)
#    c = contourf(time, fr, y, clevel, cmap = cm.hsv)
    cax = gca()
    if dispt0 is None:
        cax.set_xlim(t0, t1)
    else:
        cax.set_xlim(dispt0, dispt1)
    cax.set_ylim(lo, hi)
    title(titlestr, fontsize = 15)
#    colorbar(format = '%.2g', ticks = ticks)
    if ref:
        #from matplotlib.colorbar import make_axes
        newright = cax.get_position().x1
        subplot(212)
        srate / f.shape[0]
        n = freq(hi) - freq(lo)
        fr = linspace(lo, hi, n)
        plot(fr, (f[:n]))
        # ensure the x axis takes up the same amount of space
        ax = gca()
        p = ax.get_position()
        p.x1 = newright
        ax.set_position(p)
        ax.set_xlim(lo, hi)
        # ensure the x axis has the same range
        #a = list(ax.axis())
        #a[0:2] = cax.axis()[0:2]
        #ax.axis(a)

if len(mlist) == 0:
    caption = "%d trial%s" % (ntrials, 's'[0:ntrials > 1])
else:
    caption = ', '.join(mlist)

if donorm:

    # Default to the whole window.

    if baset0 is None:
        baset0 = 0
        baset1 = t1 - t0

    # Average across the baseline.

    b0 = int(baset0 * srate)
    b1 = int(baset1 * srate)
    x = add.reduce(s[:, b0 : b1], 1) / (b1 - b0)

    # Optionally smooth (decaying exponential model).

    fs = linspace(lo, hi, x.shape[0])
    if smoothnorm:
        x = x.max() * exp(-fs/20.)

#    figure()
#    plot(freq, x)
#    title("Average power in the window [%g, %g]s" % \
#          (t0 + baset0, t0 + baset1), fontsize = 15)

    # Normalize s by the baseline time average.

    x.shape = (x.shape[0], 1)
    x = repeat(x, s.shape[1], 1)
    s /= x

    f = x

    caption += " SNR"

if prefix:
    writebrik(log(s), prefix)
    sys.exit(0)

if matfile:
    time = linspace(t0, t1, s.shape[1])
    freq = linspace(lo, hi, s.shape[0])
    x = {'st_time': time, 'st_freq': freq, 'st_data': log(s)}
    if matfile[-4:] != '.mat':
        matfile += '.mat'
    mio.savemat(matfile, x)
    sys.exit(0)

if lflag:
    s = log(s)
    f = log(f)

figure()
plotst(s, "%s; %s" % (caption, cnames))
show()
