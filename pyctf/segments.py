from warnings import warn
from functools import cmp_to_key

def get_segment_list(ds, mlist, t0, t1):
    """Create a list of segments of a dataset. A segment is specified
    using times in seconds relative to marks of the dataset, and
    generates a list of (tr, s) pairs, where each segment starts at
    sample s of trial tr, and ends at sample s + seglen - 1.
    This function returns (seglist, seglen)."""

    # Check the marks in mlist. Convert a string to a list of length 1.

    if type(mlist) == type(''):
        mlist = [mlist]

    marks = ds.marks
    for m in mlist:
        if not marks.get(m):
            raise ValueError("unknown marker '%s'" % m)

    # Get (tr, s) for all specified marks.

    nsamples = ds.getNumberOfSamples()
    if not mlist:
        # If there are no marks, each trial becomes a segment.
        ntrials = ds.getNumberOfTrials()
        seglist = list(zip(range(ntrials), [0] * ntrials))
        seglen = nsamples
        return seglist, seglen

    srate = ds.getSampleRate()
    seglen = int((t1 - t0) * srate + .5)
    seglist = []
    for m in mlist:
        seglist.extend(marks[m])

    # Bounds check, make sure we are always inside trial boundaries.

    T0 = ds.getTimePt(0)
    T1 = ds.getTimePt(nsamples - 1)
    def bck(t):
        if T0 <= t[1] + t0 and t[1] + t1 < T1:
            return True
        warn("mark at trial %d, time %g, out of bounds" % t)
        return False
    seglist = filter(bck, seglist)

    # Convert t0 + marker time (t[1]) to samples.

    def cvt2s(t):
        return (t[0], ds.getSampleNo(t[1] + t0))
    seglist = list(map(cvt2s, seglist))

    # Sort by trial (a) and time (b).

    def cmp(a, b):
        if a[0] < b[0]:
            return -1
        if a[0] == b[0]:
            if a[1] < b[1]:
                return -1
            return 1
        return 1
    seglist.sort(key = cmp_to_key(cmp))

    return seglist, seglen

# Filter out unwanted trials. Specify the ones you want.

def onlyTrials(seglist, trlist):
    def intr(s, tr = trlist):
        return s[0] in tr
    seglist = list(filter(intr, seglist))
    return seglist
