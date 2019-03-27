import sys, os
from .fieldspline import make_spline, interpolate, interior
from pylab import array, zeros, linspace, ma, contour, contourf, axis, gci, \
    plot, scatter, text, sqrt, cm
from .cmap import meg_cmap
from .tics import scale1

SENSORTOPO = os.path.join(os.path.dirname(__file__), "CTF275.txt")
#SENSORTOPO = os.path.join(os.path.dirname(__file__), "CTF273.txt")

class point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.z = 0.

class sensortopo:
    """Manage a 2D representation of the sensor array."""

    def __init__(self, ds = None):
        """Initialize the full topo, or, if ds is specified,
        just those sensors actually in ds."""

        topo = {}
        sensors = []
        if ds:
            allsensors = ds.channel.keys()
        f = open(SENSORTOPO)
        VERT, BOUND = 1, 2
        state = 0
        for l in f:
            if l[0] == '#':
                continue
            l = l.split()
            if l[0] == 'nv':
                vert = []
                state = VERT
            elif l[0] == 'nb':
                bound = []
                state = BOUND
            elif state == VERT:
                name, x, y = l
                if ds is None:
                    sensors.append(name)
                else:
                    if name in allsensors:
                        sensors.append(name)
                if name in sensors:
                    p = point(x, y)
                    vert.append(p)
                    topo[name] = p
            elif state == BOUND:
                if l[0] in allsensors:
                    bound.append(topo[l[0]])
            else:
                raise AssertionError('bad state in sensortopo')
        f.close()

        self.x = array([p.x for p in vert])
        self.y = array([p.y for p in vert])
        self.vert = vert
        self.topo = topo
        self.sensors = sensors
        self.ds = ds

        # Get the bounding box.

        self.xmin, self.xmax = min(self.x), max(self.x)
        self.ymin, self.ymax = min(self.y), max(self.y)

        # Get the boundary.

        self.boundx = array([b.x for b in bound])
        self.boundy = array([b.y for b in bound])

        # Create a default grid.

        self.make_grid(100)

    def get_names(self):
        return self.sensors

    def get_cidx(self, names):
        """Return channel indices into the dataset's Primary array for the named sensors."""
        cidx = array(self.ds.clist2idx(names))
        cidx -= self.ds.getFirstPrimary()
        return cidx

    def make_grid(self, m):
        self.M = m
        self.X = linspace(self.xmin, self.xmax, m).astype('d')
        self.Y = linspace(self.ymin, self.ymax, m).astype('d')
        self.Z = zeros((m, m))
        mask = zeros((m, m), 'bool')
        r = range(m)
        for i in r:
            xx = self.X[i] * .99 + .005
            for j in r:
                yy = self.Y[j] * .99 + .005
                mask[j, i] = interior(xx, yy, self.boundx, self.boundy)
        self.mask = ~mask

    def plot(self, z, cmap = cm.coolwarm, zrange = 'zero', label = False, showsens = False, nocontour = False):
        """The array z of values to be plotted must be in the same
        order as the array returned by get_names(). zrange can be
        'auto', 'zero' which is auto but symmetric around 0, or
        a pair of min, max. label = True means label the sensors.
        showsens = True means draw dots at the sensor locations.
        nocontour = True means don't draw black contour lines."""

        make_spline(self.x, self.y, array(z, 'd'))
        r = range(self.M)
        for i in r:
            xx = self.X[i]
            for j in r:
                yy = self.Y[j]
                if not self.mask[j, i]:
                    self.Z[j, i] = interpolate(xx, yy, self.x, self.y)

        Z = ma.array(self.Z, mask = self.mask)

        if zrange == 'auto' or zrange == 'zero':
            zmin = ma.minimum.reduce(Z, axis = None)
            zmax = ma.maximum.reduce(Z, axis = None)
            if zrange == 'zero':
                # If it crosses zero make it symmetrical.
                if (zmin < 0) and (0 < zmax):
                    maxmax = max(-zmin, zmax)
                    zmin = -maxmax
                    zmax = maxmax
        else:
            zmin = zrange[0]
            zmax = zrange[1]

        # First make nice tics for this range.
        # Then switch to the new limits given by the tics
        # so the contour plot will use the whole range.
        ticks, mticks = scale1(zmin, zmax)
        zmin, zmax = ticks[0], ticks[-1]

        nlevels = 100
        levels = linspace(zmin, zmax, nlevels)

        # plot the boundary and maybe the sensors
        plot(self.boundx, self.boundy, color = 'black',
            zorder = 1, linewidth = 3)
        if showsens:
            scatter(self.x, self.y, s = 15, c = (0, 1, 0),
                zorder = 2, marker = 'o', linewidth = .5)

        contourf(self.X, self.Y, Z, levels, cmap = cmap)
#        contourf(self.X, self.Y, Z, levels)
        im = gci() # save the ContourSet to return
        if not nocontour:
            contour(self.X, self.Y, Z, 10, colors = 'black')

        if label:
            for name in self.sensors:
                s = self.topo[name]
                text(s.x, s.y, name)

        l = 1.02
        x = -.01
        y = -.04
        axis([x, x + l, y, y + l])
        axis('off')
        axis('scaled')
        return im, ticks

    def nearest(self, x, y):
        l = [None] * len(self.x)
        for i in range(len(self.x)):
            d = sqrt((self.x[i] - x)**2 + (self.y[i] - y)**2)
            l[i] = d, self.sensors[i]
        l.sort()
        return l[0][1]
