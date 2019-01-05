import sys, struct
import numpy as np

def readwts(wtsfile, label = False):
    """w, m = readwts(file) return the array w of beamformer weights found
    in the given .wts file, and the affine transform m needed to map
    voxels of the array into ortho space. If label is true also return
    the channel id."""

    wts = open(wtsfile, 'rb')

    # Read the header.

    fmt = ">8s"
    h = wts.read(struct.calcsize(fmt))
    l = struct.unpack(fmt, h)
    if l[0] == 'SAMCOEFF':
        fmt = ">1i"
    elif l[0] == 'SAMFWDSL':    # basically the same but byte-swapped
        fmt = "<1i"
    else:
        raise RuntimeError("%s is not a SAM coefficient file" % wtsfile)
    h = wts.read(struct.calcsize(fmt))
    l = struct.unpack(fmt, h)
    ver = l[0]
    endian = '>'
    if ver == 1:
        fmt = ">256s2i4x11d256s3i3i3i2i4x"
    elif ver == 2:
        fmt = ">256s2i4x11d256s3i3i3i2i4x3d3d3d32s"
    elif ver == 3:
        endian = '<'
        fmt = "<256s2i4x11d256s3i3i3i2i4x"
    else:
        raise RuntimeError("unknown SAM coefficient file format!")
    head = wts.read(struct.calcsize(fmt))
    l = struct.unpack(fmt, head)

    N = l[1]
    W = l[2]
    x1, x2 = l[3], l[4]
    y1, y2 = l[5], l[6]
    z1, z2 = l[7], l[8]
    step = l[9]

    coords = None
    if step:
        x = np.arange(x1, x2 + 1e-8, step)
        y = np.arange(y1, y2 + 1e-8, step)
        z = np.arange(z1, z2 + 1e-8, step)
        coords = (x, y, z)

    # Read the rest of the header.

    if ver == 1 or ver == 3:
        fmt = "%c%di" % (endian, N)
        s = struct.calcsize(fmt)
        buf = wts.read(s)
        chan_idx = struct.unpack(fmt, buf)
    else: # ver == 2
        fmt = ">" + "32s" * (N + W) + "%dd" % (W * 3)
        s = struct.calcsize(fmt)
        buf = wts.read(s)
        l = struct.unpack(fmt, buf)
        labels = [s.split('\x00')[0].split('-')[0] for s in l[:N]]

    # Read the weights.

    w = np.zeros((W, N))
    for i in range(W):
        fmt = "%c%dd" % (endian, N)
        s = struct.calcsize(fmt)
        buf = wts.read(s)
        w[i, :] = np.array(struct.unpack(fmt, buf))
    if step:
        w.shape = len(x), len(y), len(z), N

    # Create the transform. Get linear coefficients for each coordinate.

    m = None
    if coords:
        m = np.zeros((4, 4), 'f')
        c = coords
        for i in (0, 1, 2):
            n = len(c[i])
            x0 = c[i][0] * 1000.    # convert meters to millimeters
            x1 = c[i][n-1] * 1000.
            a = (x1 - x0) / (n - 1)
            b = x0
            m[i, i] = a
            m[i, 3] = b
        m[3, 3] = 1.

        # The above matrix is in PRI, not RAI. Permute the axes appropriately.

        T = np.array([
                [ 0.,-1., 0., 0. ],
                [ 1., 0., 0., 0. ],
                [ 0., 0., 1., 0. ],
                [ 0., 0., 0., 1. ]])
        m = np.dot(T, m)

    if label:
        if ver == 1 or ver == 3:
            return w, m, chan_idx
        return w, m, labels
    return w, m
