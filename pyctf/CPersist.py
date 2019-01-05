# Read .rp, .acq, and other files in CPersist format.

import os, sys
from struct import Struct

CPERSISTHDR = b"WS1_"

be_int = Struct(">i")
be_uint = Struct(">I")
be_short = Struct(">h")
be_ushort = Struct(">H")
be_long = Struct(">l")
be_ulong = Struct(">L")
be_double = Struct(">d")

def get(f, s):
    return s.unpack(f.read(s.size))[0]

def getint(f):
    return get(f, be_int)

def getstr(f):
    count = getint(f)
    return f.read(count)

def getCPersist(f):
    s = f.read(4)
    if s != CPERSISTHDR:
        raise RuntimeError("improper CPersist file")

    d = {}
    while 1:
        tag = getstr(f).decode()
        if tag == "EndOfParameters":
            break
        tagtype = getint(f)
        if tagtype == 1:                # Custom
            if tag == "DataManagerStart":
                # This tag has no data
                v = None
            elif tag == "DatasetFiles":
                i = getint(f)
                if i != 1:
                    print('erk')
                v = getstr(f)
                get(f, be_short) # unknown
            elif tag == "DisplaySets":
                n = getint(f)
                v = [None] * n
                for i in range(n):
                    v[i] = getCPersist(f)
                getint(f)
            elif tag == "ChannelSet":
                v = getCPersist(f)
            else:                       # punt
                v = getCPersist(f)
        elif tagtype == 2:              # Object
            v = getCPersist(f)
        elif tagtype == 3:              # Binary
            v = getstr(f)
        elif tagtype == 4:              # Double
            v = get(f, be_double)
        elif tagtype == 5:              # Integer
            v = get(f, be_int)
        elif tagtype == 6:              # Short
            v = get(f, be_short)
        elif tagtype == 7:              # UShort
            v = get(f, be_ushort)
        elif tagtype == 8:              # Boolean
            v = f.read(1)
            v = ord(bytes(v))           # works in py2 and py3
        elif tagtype == 9:              # CStr32
            print('CStr32')
        elif tagtype == 10:             # String
            v = getstr(f)
        elif tagtype == 11:             # StringList
            n = getint(f)
            v = [None] * n
            for i in range(n):
                v[i] = getstr(f)
        elif tagtype == 12:             # CStr32List
            n = getint(f)
            v = [None] * n
            for i in range(n):
                v[i] = getCstr(f)
        elif tagtype == 13:             # SensorClassList
            pass
        elif tagtype == 14:             # Long
            v = get(f, be_long)
        elif tagtype == 15:             # ULong
            v = get(f, be_ulong)
        elif tagtype == 16:             # UInteger
            v = get(f, be_uint)
        elif tagtype == 17:             # CTFBoolean
            print('CTFbool')
        else:
            raise NameError("unhandled tag type %d" % tagtype)

        # _eeg_info is type 5, but it is special: its value
        # is the number of following cpersist structures.

        if tag == "_eeg_info":
            n = v
            v = [None] * n
            for i in range(n):
                v[i] = getCPersist(f)

        d[tag] = v

    # .acq files have one more unnamed cpersist struct at the end,
    # but it isn't very interesting so we can ignore it.

    return d
