#! /usr/bin/env python

from __future__ import print_function

import sys, os, tempfile
from math import floor
from pylab import *
import pyctf
from pyctf.util import *
from pyctf.st.smt import calc_tapers, calcbw, mtst
from pyctf.st import st
from pyctf.samiir import mkfft, mkiir, dofilt

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category = FutureWarning)
    import h5py

usage("""[options] -c channel ... [projhdf5]

This program produces time-frequency plots using the Stockwell transform.
The default behavior is to average all trials and compute the Stockwell
transform of the average. Each channel is averaged separately and the
resulting Stockwells are averaged together.

projhdf5 is the output of projDs.py.

For the -m, -c, and -T options, you can specify multiple arguments in
quotes, or use multiple options, or both. In other words,
        -m 'mark1 mark2 mark3'
and
        -m mark1 -m mark2 -m mark3
are equivalent.

You must specify at least one channel to work on.

Options are:

        -d dataset      You can either specify a dataset using -d or as the
                        last argument. Must be an hdf5 file output from projDs.py.

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

        -c channel      The channel list is a set of individually
                        specified channels, numbered starting from 0.
                        There is no default, you need to specify at least
                        one channel.

        -T trial        Only process the specified trial(s). You can
                        specify more than one trial. Default is all trials.

        -p              Apply a 60 Hz notch filter.

        -l              Plot the log of the power.

        -n              Normalize by the average across the entire time window.

        -B "t0 t1"      Normalize by the average across the specified baseline
                        time window. The time values are in seconds relative
                        to the left-hand side of the plot! (Implies -n.)

        -D "t0 t1"      Trim the display to be from t0 to t1 (relative to the
                        original axis).

        -r channel      Add a channel in a subplot.

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

This is StockwellProj.py version 1.0""")

def round(x):
    return int(floor(x + .5))

optlist, args = parseargs("m:t:b:ak:c:npPso:lr:T:d:B:D:v", ["mat="])

dsname = None
mlist = []
clist = []
trlist = []
t0 = None
baset0 = None
dispt0 = None
lo = None
hi = None
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

# Open the hdf5 file.

f = h5py.File(dsname, "r")
head = f['head']

srate = head['srate'].value
marks = head['marks'][:].tolist()
T0, T1 = head['time'][:]
Lo, Hi = head['band'][:]
trialmarks = head['trialmarks'][:].tolist()

H = f['H'].value

s = H.shape
nvox = s[0]     # number of virtual channels
ntrials = s[1]  # number of trials
nsamples = s[2] # number of samples

# Sanity check.

if t0 is None and len(mlist) == 0 and ntrials == 1:
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

# Band limits

if lo == None:
        lo = Lo
if hi == None:
        hi = Hi

# The time bounds of the trial.

if t0 is None:
        t0 = T0
        t1 = T1
        print("Default time window is %g to %g" % (t0, t1))
        seglen = nsamples
else:
        seglen = round((t1 - t0) * srate)

# Convert the channel list to dataset indices.

idx = list(map(int, clist)) # list() converts python3 map objects to lists
cnames = ', '.join(clist)
nch = len(idx)

# Look at the markers and construct the list of trials.

for marker in mlist:
        if marker not in marks:
                printerror("unknown marker '%s'" % marker)
                sys.exit(1)

if len(mlist) == 0:
        # if no marks, use all trials
        tlist = list(zip(range(ntrials), [0]*ntrials))
else:
        tlist = []
        for i in range(ntrials):
                if trialmarks[i] in mlist:
                        tlist.append((i, 0))

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
        return round(f * seglen / srate)

s = 0.
if not aflag:
        s = [0.] * nch

n = 0
maxm = len(tlist)
m = 1

if K > 0:
        tapers = calc_tapers(K, seglen)

# Optionally notch filter the data.

if pflag:
        lineFilt = mkfft(61., 59., srate, nsamples)

last_tr = None
for tr, t in tlist:
        if t + t0 < T0 or t + t1 > T1:
                continue
        if tr != last_tr:
                D = H[:, tr, :]
                last_tr = tr
                print('trial %d' % tr)
                if pflag:
                        for ch in idx:
                                D[ch, :] = dofilt(D[ch], lineFilt)
        samp = round((t - T0 + t0) * srate)
        i = 0
        for ch in idx:
                d = D[ch][samp : samp + seglen]
                if aflag:
                        if verbose:
                                print(ch, end = ' ')
                        if K == 0:
                                if Pflag:
                                        s += st(d, freq(lo), freq(hi))
                                else:
                                        s += abs(st(d, freq(lo), freq(hi)))**2
                        else:
                                s += mtst(K, tapers, d, freq(lo), freq(hi))
                else:
                        s[i] += d
                i += 1
                n += 1
        if aflag and verbose:
                print()
                print(n)

r = 0.
if ref:
        ch = int(ref)
        for tr, t in tlist:
                if t + t0 < T0 or t + t1 > T1:
                        continue
                samp = round((t - T0 + t0) * srate)
                d = H[ch, tr, samp : samp + seglen]
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
else:
        d = 0.
        for ch in range(nch):
                if verbose:
                        print(ch, end = ' ')
                if K == 0:
                        if Pflag:
                                d += st(s[ch] / n, freq(lo), freq(hi))
                        else:
                                d += abs(st(s[ch] / n, freq(lo), freq(hi)))**2
                else:
                        d += mtst(K, tapers, s[ch] / n, freq(lo), freq(hi))
        if verbose:
                print()
        if Pflag:
                s = abs(d)**2 / nch
        else:
                s = d / nch

print('bw =', calcbw(K, seglen, srate))

def writebrik(s, prefix):
        "Write 2D TF data as an AFNI BRIK."

        # dump the array into a file
        fd, tmpfile = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
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
# you can uncomment this to set the z range
#        n = 0
#        m = 3e8
#        m = 6
        nlevels = 40
        clevel = linspace(n, m, nlevels)
        ticks, mticks = scale1(clevel[0], clevel[-1])
        time = linspace(t0, t1, y.shape[1])
        fr = linspace(lo, hi, y.shape[0])
        if ref:
                subplot(211)
        c = contourf(time, fr, y, clevel, cmap = cm.jet)
#        c = contourf(time, fr, y, clevel, cmap = cm.hsv)
        cax = gca()
        if dispt0 is None:
                cax.set_xlim(t0, t1)
        else:
                cax.set_xlim(dispt0, dispt1)
        cax.set_ylim(lo, hi)
        title(titlestr, fontsize = 15)
        colorbar(format = '%.2g', ticks = ticks)
        if ref:
                #from matplotlib.colorbar import make_axes
                newright = cax.get_position().x1
                subplot(212)
                plot(time, r)
                # ensure the x axis takes up the same amount of space
                ax = gca()
                p = ax.get_position()
                p.x1 = newright
                ax.set_position(p)
                # ensure the x axis has the same range
                a = list(ax.axis())
                a[0:2] = cax.axis()[0:2]
                ax.axis(a)

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

        freq = linspace(lo, hi, x.shape[0])
        if smoothnorm:
                x = x.max() * exp(-freq/20.)

#        figure()
#        plot(freq, x)
#        title("Average power in the window [%g, %g]s" % \
#              (t0 + baset0, t0 + baset1), fontsize = 15)

        # Normalize s by the baseline time average.

        x.shape = (x.shape[0], 1)
        x = repeat(x, s.shape[1], 1)
        s /= x

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

figure()
plotst(s, "%s %s; %s" % (os.path.basename(dsname), caption, cnames))
show()
