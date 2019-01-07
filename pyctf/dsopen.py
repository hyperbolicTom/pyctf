"""This is the main interface for the Python CTF library."""

import os, math
from . import ctf_res4 as ctf
from .ctf_meg4 import dsData
from .markers import markers
from .getHC import getHC
from .getHM import getHM
from . import fid
from .readwts import readwts as _readwts
from .readcov import readcov as _readcov

class dsopen:

    def __init__(self, dsname):
        """Create and return an open CTF dataset object.
        You may open many CTF datasets at once by creating many
        instances of this class. You must call close() or
        delete the instance to release any array memory held."""

        self.dsData = None      # set this now so __del__ won't complain

        dsname = os.path.expanduser(dsname)
        if dsname[-1] == '/':
            dsname = dsname[:-1]
        b = os.path.basename(dsname)
        if b[-3:] != '.ds':
            raise ValueError("%s is not a dataset name" % dsname)
        self.dsname = dsname
        self.setname = b[:-3]

        # Open files. We allow the .meg4 file to be absent.

        res4name = self.getDsFileNameExt('.res4')
        self.r = ctf.readRes4(res4name)
        try:
            meg4name = self.getDsFileNameExt('.meg4')
            self.dsData = dsData(self.r, meg4name)  # handle to open .meg4 file (mmap)
        except:
            pass

        # A mapping from channel name to number, backwards compatible name.

        self.channel = self.r.chanIndex

        # Get the marks, if any.

        self.marks = markers(dsname)

        # Get the dewar coordinates of the head from the .hc file, if any.

        hc = self.getDsFileNameExt('.hc')
        try:
            n, l, r = getHC(hc, 'dewar')
            self.dewar = n, l, r

            # compute the transform into the head frame
            self.dewar_to_head = fid.fid(n, l, r)

            # compute the head coordinates in the head frame
            self.head = [fid.fid_transform(self.dewar_to_head, x) for x in self.dewar]
        except:
            pass

    def __del__(self):
        # deletion takes down everything
        del self.dsData

    def close(self):
        """close() releases dataset memory but does not delete
        the .r or other ds. objects."""
        # just close the dsData object to release memory
        self.dsData.close()

    def getDsFileName(self, name):
        """Formats a pathname for a dataset file."""
        return os.path.join(self.dsname, name)

    def getDsFileNameExt(self, ext):
        """Formats a pathname for a dataset file from an extension."""
        return os.path.join(self.dsname, self.setname + ext)

    def getNumberOfChannels(self):
        """Return the total number of channels."""
        #return self.r.genRes[ctf.gr_numChannels]
        return self.r.numChannels

    def getFirstReference(self):
        """Return the index of the first reference channel."""
        return self.r.firstRef

    def getNumberOfReferences(self):
        """Return the number of reference channels."""
        return self.r.numRefs

    def getFirstPrimary(self):
        """Return the index of the first primary MEG channel."""
        return self.r.firstPrimary

    def getNumberOfPrimaries(self):
        """Return the number of primary MEG channels."""
        return self.r.numPrimaries

    def getSampleRate(self):
        """Return the sampling rate in Hz."""
        return self.r.genRes[ctf.gr_sampleRate]

    def getNumberOfSamples(self):
        """Return the number of samples per trial."""
        return self.r.numSamples

    def getNumberOfTrials(self):
        """Return the number of trials."""
        return self.r.numTrials

    def getChannelName(self, i):
        """Return the name of channel i."""
        return self.r.chanName[i]

    def getChannelIndex(self, name):
        """Return the index of the channel named name."""
        return self.r.chanIndex[name]

    def getChannelType(self, i):
        """Return the type of channel i."""
        return self.r.chanType[i]

    def getChannelGain(self, i):
        """Return the gain of channel i."""
        return self.r.chanGain[i]

    def getSensorList(self, cls = ctf.TYPE_MEG):
        """Return a list of the channel names in ds, of type cls."""

        nc = self.r.numChannels
        l = []
        for i in range(nc):
            if self.getChannelType(i) == cls:
                l.append(self.r.chanName[i])
        return l

    def getPreTrigSamples(self):
        """Return the number of samples in the pre-trigger interval."""

        return self.r.genRes[ctf.gr_preTrig]

    def getTimePt(self, samp):
        """Convert a sample number within a trial to a time in seconds."""

        preTrig = self.getPreTrigSamples()
        return float(samp - preTrig) / self.getSampleRate()

    def getSampleNo(self, t):
        """Convert a time in seconds to a relative sample number."""

        t += self.getPreTrig()
        return int(math.floor(t * self.getSampleRate() + .5))

    def getPreTrig(self):
        """Return the pretrigger length in seconds."""

        return self.getPreTrigSamples() / self.getSampleRate()

    def removeProcessing(self):
        pass

    def getRefArray(self, tr, start = 0, n = 0):
        """Return an array of data from all reference channels of trial tr."""

        return self.dsData.getRefArray(tr, start, n)

    def getPriArray(self, tr, start = 0, n = 0):
        """Return an array of data from all primary channels of trial tr."""

        return self.dsData.getPriArray(tr, start, n)

    def getIdxArray(self, tr, idx, start = 0, n = 0):
        """Return an array of data from channels [idx] of trial tr."""

        return self.dsData.getIdxArray(tr, idx, start, n)

    def getDsRawData(self, tr, ch):
        """Return trial tr from channel ch as a numpy array."""

        return self.dsData.getRawSegment(tr, ch)

    def getDsData(self, tr, ch):
        """Return trial tr from channel ch, the mean is removed."""

        return self.dsData.getSegment(tr, ch)

    def getDsRawSegment(self, tr, ch, start = 0, n = 0):
        """Return n samples starting at start from trial tr channel ch."""

        return self.dsData.getRawSegment(tr, ch, start, n)

    def getDsSegment(self, tr, ch, start = 0, n = 0):
        """Return n samples starting at start from trial tr channel ch, the
        mean is removed."""

        return self.dsData.getSegment(tr, ch, start, n)

    def isAverage(self):
        return self.r.genRes[ctf.gr_numAvg] > 0

    def getHLCData(self, t, chan):
        return getHM(self, t, chan)

    def readwts(self, wtsfile):
        try:
            n = self.getDsFileName("SAM/%s.wts" % wtsfile)
            w = _readwts(n)
        except IOError:
            n = self.getDsFileName("SAM/%s" % wtsfile)
            w = _readwts(n)
        return w

    def readcov(self, covfile):
        try:
            n = self.getDsFileName("SAM/%s.cov" % covfile)
            C = _readcov(n)
        except IOError:
            n = self.getDsFileName("SAM/%s" % covfile)
            C = _readcov(n)
        return C

    def clist2idx(self, clist, cls = ctf.TYPE_MEG):
        """Convert a list of channel names to indices. Allow prefixes."""

        nc = self.r.numChannels
        chanName = self.r.chanName
        chanType = self.r.chanType
        sl = [(i, chanName[i]) for i in range(nc) if chanType[i] == cls]
        r = []
        for c in clist:
            n = len(c)
            found = False
            for i, s in sl:
                if c == s[0:n]:
                    r.append(i)
                    found = True
            if not found:
                raise ValueError("channel %s not found" % c)
        return r

# This takes an arbitrary point in PRI space in m and finds the
# indices within a .wts or .svl file, given the coords object
# returned by readwts().

def PRI_idx(x, y, z, coords):
    i = coords[0].searchsorted(x)
    j = coords[1].searchsorted(y)
    k = coords[2].searchsorted(z)
    return i, j, k
