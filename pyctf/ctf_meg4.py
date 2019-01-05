import numpy as np

MEG4HDR = "MEG41CP\x00"

class dsData(object):
    """mmap() the .meg4 file. Return byteswapped, scaled arrays of data."""

    def __init__(self, r, meg4name):
        self.r = r
        self.T = r.numTrials
        self.C = r.numChannels
        self.S = r.numSamples
        self.m = np.memmap(meg4name, dtype = 'int32', mode = 'r',
            shape = (self.T, self.C, self.S), offset = len(MEG4HDR))

    def close(self):
        # call this to release the memory
        #self.m.flush() # only if writable
        del self.m

    def getRawSegment(self, tr, ch, start = 0, n = 0):
        """Read a segment of data from trial tr channel ch."""

        if n == 0:
            n = self.r.numSamples
        a = self.m[tr, ch, start : start + n]
        s = a.byteswap() * self.r.chanGain[ch]
        return s

    def getSegment(self, tr, ch, start = 0, n = 0):
        """Read a segment of MEG data from trial tr channel ch. Return a
        numpy array with units of Tesla. The mean is removed."""

        if n == 0:
            n = self.r.numSamples
        a = self.m[tr, ch, start : start + n]
        s = a.byteswap() * self.r.chanGain[ch]
        return s - s.mean()

    def getArray(self, tr, ch, nch, start, n):
        """Return an array of data from channels ch:ch+nch of trial tr. The
        mean is removed from each channel."""

        a = self.m[tr, ch : ch + nch, start : start + n]
        s = a.byteswap() * self.r.chanGain[ch : ch + nch]
        sm = s.mean(axis = 1)
        sm.shape += (1,)    # make it a column array
        return s - sm

    def getRefArray(self, tr, start = 0, n = 0):
        """Return an array of data from all reference channels of trial tr."""

        ch = self.r.firstRef
        nch = self.r.numRefs
        if n == 0:
            n = self.r.numSamples
        return self.getArray(tr, ch, nch, start, n)

    def getPriArray(self, tr, start = 0, n = 0):
        """Return an array of data from all primary channels of trial tr."""

        ch = self.r.firstPrimary
        nch = self.r.numPrimaries
        if n == 0:
            n = self.r.numSamples
        return self.getArray(tr, ch, nch, start, n)

    def getIdxArray(self, tr, idx, start = 0, n = 0):
        """Return an array of data from channels [idx] of trial tr. The
        mean is removed from each channel."""

        if n == 0:
            n = self.r.numSamples
        a = self.m[tr, idx, start : start + n]
        s = a.byteswap() * self.r.chanGain[idx]
        sm = s.mean(axis = 1)
        sm.shape += (1,)    # make it a column array
        return s - sm

#    def getArray(self, tr, ch, nch, start, n):
#        """Return an array of data from channels ch:ch+nch of trial tr. The
#        mean is removed from each channel."""
#
#        return self.getIdxArray(tr, range(ch, ch + nch), start, n)
