from __future__ import division, with_statement

from .dsopen import dsopen, PRI_idx
from . import ctf_res4 as ctf
from . import fid, samiir, st, util
from .samiir import *
from .segments import get_segment_list, onlyTrials
from .paramDict import paramDict
# in case there's no display
try:
    from .sensortopo import sensortopo, cmap
except:
    pass
