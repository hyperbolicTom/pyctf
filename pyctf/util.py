# Some useful stuff.

import sys, os, getopt
try:
        import subprocess
except:
        import popen2

__scriptname = os.path.basename(sys.argv[0])

def usage(s):
        global __usage
        __usage = s

def msg(s):
        sys.stderr.write(s)

def printerror(s):
        msg("%s: %s\n" % (__scriptname, s))

def printusage():
        msg("usage: %s %s\n" % (__scriptname, __usage))

def parseargs(*args):
        """usage: parseargs(opt, [lopt]) where opt is a string
        that looks like "a:bc:" and lopt (if present) is a list of
        long options without the --"""

        try:
                optlist, args = getopt.getopt(sys.argv[1:], *args)
        except Exception as msg:
                printerror(msg)
                printusage()
                sys.exit(1)
        return optlist, args

def run(cmd, raw = False):
        try:
                p = subprocess.Popen(cmd, shell=True, close_fds=True,
                                     stdout=subprocess.PIPE)
                pr = p.stdout
        except:
                (pr, pw) = popen2.popen2(cmd)
                pw.close()
        if raw:
                r = pr.read()
        else:
                r = pr.readlines()
        pr.close()
        return r
