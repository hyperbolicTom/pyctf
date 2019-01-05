import os
from subprocess import Popen, PIPE

# This sed script pre-parses the marker file and makes things a little easier.

_sedscript = """/:/{
N
s/\\n/ /
}
/^$/d
"""

class markers:
    """Access to the markers of a CTF dataset. Each marker becomes a key
    that returns the list of samples."""

    def __getitem__(self, key):
        return self.marks[key]

    #def __setitem__(self, key, value):
    #    self.marks[key] = value

    def get(self, key):
        return self.marks.get(key)

    def keys(self):
        return self.marks.keys()

    def __init__(self, dsname):
        self.marks = {}

        markerfilename = dsname + '/MarkerFile.mrk'
        try:
            f = open(markerfilename)
        except:
            return
        f.close()

        # Preprocess the file.

        sedcmd = ['sed', '-f', '-', markerfilename]
        p = Popen(sedcmd, stdin = PIPE, stdout = PIPE, universal_newlines = True)
        (pr, pw) = p.stdout, p.stdin
        pw.write(_sedscript)
        pw.close()
        f = pr

        # Look at each line.

        START = 1
        MARK = 2
        NUM = 3
        state = START

        for l in f:
            s = l.split(':')
            if state == START:
                if s[0] == 'CLASSGROUPID':
                    state = MARK
            elif state == MARK:
                if s[0] == 'NAME':
                    name = s[1].strip()
                    state = NUM
            elif state == NUM:
                if s[0] == 'NUMBER OF SAMPLES':
                    num = int(s[1])
                    next(f)
                    self._get_samples(f, name, num)
                    state = START
        pr.close()
        os.wait()

    def _get_samples(self, f, name, num):
        "Add all the samples for a marker to the marks dict."
        for x in range(num):
            l = next(f).split()
            trial = int(l[0])
            t = float(l[1])
            if not self.marks.get(name):
                self.marks[name] = []
            self.marks[name].append((trial, t))
