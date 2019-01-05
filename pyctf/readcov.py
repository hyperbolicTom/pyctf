import sys, struct
import numpy as np

def readcov(covfile):
    """readcov(file) returns the covariance matrix found in the given .cov file."""

    cov = open(covfile, 'rb')

    # Read the header.

    fmt = "<8s1i256s256s1i4d3i4x"
    head = cov.read(struct.calcsize(fmt))
    l = struct.unpack(fmt, head)

    if l[0] != 'SAMCOVAR' or l[1] != 3:
        raise RuntimeError("%s is not a valid covariance file" % covfile)

    N = l[4]

    #BW = l[7]
    #Noise = l[8]
    #noiseDensity = np.sqrt(Noise / BW)
    #nSamp = l[10]
    #effSamp = 2. * BW * nSamp / sRate / N

    # Read the indices.

    fmt = "<%di" % N
    buf = cov.read(struct.calcsize(fmt))
    chan_idx = struct.unpack(fmt, buf)

    # Read the covariance matrix.

    fmt = "<%dd" % (N * N)
    buf = cov.read(struct.calcsize(fmt))
    mat = struct.unpack(fmt, buf)

    C = np.array(mat)
    C.shape = (N, N)

    return C
