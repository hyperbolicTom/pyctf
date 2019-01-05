from struct import Struct
import numpy as np

# Various structs in a .res4 file

RES41HDR = b"MEG41RS"
RES42HDR = b"MEG42RS"

# One of these at the beginning.

GenRes = Struct(""">
    256s256s256s
    h255s255s
    ih2xd
    d
    h2xihh
    i10s2xh
    2xih2xii
    32s256s32s32s
    32s32s56s4x
    i4x
""")
(gr_appName, gr_dataOrigin, gr_dataDesc,
 gr_numAvg, gr_time, gr_date,
 gr_numSamples, gr_numChannels, gr_sampleRate,
 gr_epochTime,  # == numSamples / sampleRate * numTrials (even if numAvg > 0!)
 gr_numTrials, gr_preTrig, gr_trialsDone, gr_trialsDisp,
 gr_saveTrials, gr_triggerData, gr_triggerMode,
 gr_acceptFlag, gr_runtimeDisp, gr_zeroHead, gr_artifactMode,
 gr_runName, gr_runTitle, gr_inst, gr_collectDesc,
 gr_subjectId, gr_operator, gr_sensorFilename,
 gr_rdlen
) = range(29)

# Then runDesc, a string of length gr_rdlen.

# Then the filter section.

NumFilters = Struct(">h")
FilterInfo = Struct(">diih")
(fi_freq, fi_class, fi_type, fi_nparam) = range(4)
FilterParam = Struct(">d")

# Then gr_numChannels of these.

ChannelName = Struct(">32s")

# Next, gr_numChannels sets of one SensorRes and two
# arrays of MAX_COILS CoilRec structs.

SensorRes = Struct(""">
    hhi
    dddd
    hhi
""")
(sr_type, sr_runNum, sr_shape,
 sr_properGain, sr_qGain, sr_ioGain, sr_ioOffset,
 sr_numCoils, sr_gradOrder, sr_stimPol
) = range(10)

# Values of the sr_type field.

TYPE_REF_MAG = 0
TYPE_REF_GRAD = 1
TYPE_MEG = 5
TYPE_EEG = None # unknown
TYPE_HADC = 10
TYPE_UPPT = 11
TYPE_TRIGGER = TYPE_UPPT
TYPE_HDAC = 14
TYPE_SCLK = 17
TYPE_UADC = 18

# Coil records.

MAX_COILS = 8

CoilRec = Struct(""">
    ddd8x
    ddd8x
    h6xd
""")
(cr_x, cr_y, cr_z,
 cr_nx, cr_ny, cr_nz,
 cr_nturns, cr_area
) = range(8)

# Then NumCoeffs CoeffInfo structs.

MAX_BALANCING = 50
SENSOR_LABEL = 31

NumCoeffs = Struct(">h")
CoeffInfo = Struct(""">
    32s4s4x
    h
    %ds
    %dd
""" % (MAX_BALANCING * SENSOR_LABEL, MAX_BALANCING))
(ci_sensorName, ci_type,
 ci_ncoeff,
 ci_sensorList,
 ci_coeff
) = range(5)

# Strings returned by Struct.unpack() include '\x00' bytes at the end.

def nullstrip(s):
    """Truncate a string at the first zero byte, if any."""

    i = s.find(b'\x00')
    if i < 0:
        return s
    return s[:i]

# Reading and writing structs.

def getstruct(f, s):
    """Read and unpack an s struct from file f."""
    return s.unpack(f.read(s.size))

def putstruct(f, s, vl):
    """Pack a list of values into an s struct and write it."""
    f.write(s.pack(*vl))

# Read the structs from a res4 file into a res4data container.

class res4data:
    pass

def read_res4_structs(res4name):
    """Low level .res4 file access."""

    f = open(res4name, 'rb')
    s = f.read(8)
    if s[:-1] != RES41HDR and s[:-1] != RES42HDR:
        raise RuntimeError("invalid .res4 file")

    gr = getstruct(f, GenRes)
    runDesc = nullstrip(f.read(gr[gr_rdlen]))

    nf = getstruct(f, NumFilters)[0]
    filterInfo = [None] * nf
    for i in range(nf):
        fi = getstruct(f, FilterInfo)
        n = fi[fi_nparam]
        fp = [None] * n
        for j in range(n):
            fp[j] = getstruct(f, FilterParam)
        filterInfo[i] = (fi, fp)

    M = gr[gr_numChannels]
    chanName = [None] * M
    for i in range(M):
        s = getstruct(f, ChannelName)
        chanName[i] = nullstrip(s[0])

    sensRes = [None] * M
    for i in range(M):
        sr = getstruct(f, SensorRes)
        crd = [None] * MAX_COILS
        crh = [None] * MAX_COILS
        # dewar coords
        for j in range(MAX_COILS):
            crd[j] = getstruct(f, CoilRec)
        # head coords
        for j in range(MAX_COILS):
            crh[j] = getstruct(f, CoilRec)
        sensRes[i] = (sr, crd, crh)

    n = getstruct(f, NumCoeffs)[0]
    coeffInfo = [None] * n
    for i in range(n):
        coeffInfo[i] = getstruct(f, CoeffInfo)

    f.close()

    # Collect everything into a res4data container.

    r = res4data()
    r.genRes = gr
    r.runDesc = runDesc
    r.filterInfo = filterInfo
    r.chanName = chanName
    r.sensRes = sensRes
    r.coeffInfo = coeffInfo

    return r

# Write the structs in a res4data container to a file.

def write_res4_structs(res4name, r):
    f = open(res4name, 'wb')
    f.write(RES42HDR + b'\x00')

    putstruct(f, GenRes, r.genRes)
    f.write(r.runDesc + b'\x00') # gr_rdlen assumed to be correct

    nf = len(r.filterInfo)
    putstruct(f, NumFilters, [nf])
    for i in range(nf):
        fi, fp = r.filterInfo[i]
        putstruct(f, FilterInfo, fi)
        n = fi[fi_nparam]
        for j in range(n):
            putstruct(f, FilterParam, [fp[j]])

    M = r.genRes[gr_numChannels]
    for i in range(M):
        putstruct(f, ChannelName, [r.chanName[i]])

    for i in range(M):
        sr, crd, crh = r.sensRes[i]
        putstruct(f, SensorRes, sr)
        for j in range(MAX_COILS):
            putstruct(f, CoilRec, crd[j])
        for j in range(MAX_COILS):
            putstruct(f, CoilRec, crh[j])

    nc = len(r.coeffInfo)
    putstruct(f, NumCoeffs, [nc])
    for i in range(nc):
        putstruct(f, CoeffInfo, r.coeffInfo[i])

    f.close()

# Format channel names to make them more user friendly.

def fmtChanName(name):
    """Remove the -xxxx from a channel name."""
    return name.decode("utf-8").split('-')[0]

# Read a .res4 file and format the info to be more usable.

def readRes4(res4name):
    """Read a CTF format .res4 file. The information is made
    available in the returned container; with r = readRes4(name),
        r.numTrials     Number of trials.
        r.numChannels   Number of channels.
        r.numSamples    Number of samples per trial.
        r.chanName      List of channel names.
        r.chanIndex     Mapping from channel name to number.
        r.chanType      List of channel types.
        r.chanGain      Numpy array of gains used to convert
                        channel data (int32 samples) into Tesla.
        r.firstPrimary  Index of first primary channel.
        r.numPrimaries  Number of primary channels.
        r.firstRef      Index of first reference channel.
        r.numRefs       Number of reference channels.
        r.coeffInfo     Balancing coefficients.

        r.genRes        raw GenRes struct
        r.runDesc       run description
        r.filterInfo    filter info
        r.sensRes       raw SensorRes structs
    """

    # Fill in raw .res4 structs.
    r = read_res4_structs(res4name)

    # Extract a few common fields.

    r.numTrials = r.genRes[gr_numTrials]
    r.numChannels = r.genRes[gr_numChannels]
    r.numSamples = r.genRes[gr_numSamples]
    M = r.numChannels
    r.time = nullstrip(r.genRes[gr_time]).decode("utf-8")
    r.date = nullstrip(r.genRes[gr_date]).decode("utf-8")

    # Format the channel names and create an index to the channel number.

    r.chanIndex = {}
    for i in range(M):
        name = fmtChanName(r.chanName[i])
        r.chanName[i] = name
        r.chanIndex[name] = i

    # Channel types.

    r.firstPrimary = None
    r.numPrimaries = 0
    r.firstRef = None
    r.numRefs = 0

    r.chanType = [None] * M

    for i in range(M):
        r.chanType[i] = r.sensRes[i][0][sr_type]
        if r.chanType[i] == TYPE_MEG:
            if r.firstPrimary is None:
                r.firstPrimary = i
            r.numPrimaries += 1
        elif r.chanType[i] == TYPE_REF_MAG or r.chanType[i] == TYPE_REF_GRAD:
            if r.firstRef is None:
                r.firstRef = i
            r.numRefs += 1

    # A column array of channel gains.

    r.chanGain = np.zeros((M, 1))
    for i in range(M):
        sr = r.sensRes[i][0]
        r.chanGain[i] = 1. / (sr[sr_properGain] * sr[sr_qGain] * sr[sr_ioGain])

    # Balancing coefficients. Don't bother if there are no references.

    if r.numRefs == 0:
        return r

    n = len(r.coeffInfo)
    for i in range(n):
        ci = list(r.coeffInfo[i])
        r.coeffInfo[i] = ci
        ci[ci_sensorName] = fmtChanName(nullstrip(ci[ci_sensorName]))
        nc = ci[ci_ncoeff]
        sl = ci[ci_sensorList]
        cl = [None] * nc
        for j in range(nc):
            cn = nullstrip(sl[SENSOR_LABEL * j : SENSOR_LABEL * (j+1)])
            cn = fmtChanName(cn)
            cidx = r.chanIndex[cn]
            cl[j] = (cn, cidx, ci[ci_coeff + j])
        ci[ci_sensorList] = cl
        # ...
        #r.__dict__['G3BR'] = refvec

    return r
