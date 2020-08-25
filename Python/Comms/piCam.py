""" Class to enable communications with a piCam """
from copy import deepcopy
import json
import struct

import numpy as np

from . import CameraTraits

# Camera Config Data -----------------------------------------------------------
CAMERA_CAPABILITIES = {
    "fps" : CameraTraits( "fps", 60, 0, 60, int,
                          value=None,
                          units="Frames per Second",
                          human_name="Frame Rate",
                          desc="Camera Frame Rate",
                          mode="rw" ),

    "strobe" : CameraTraits( "strobe", 20, 0, 70, int,
                          value=None,
                          units="Watts",
                          human_name="Strobe Power",
                          desc="Strobe LED Power",
                          mode="rw" ),

    "shutter" : CameraTraits( "shutter", 8, 2, 250, int,
                          value=None,
                          units="100's of uSecs",
                          human_name="Exposure Time",
                          desc="Shutter Period for camera",
                          mode="rw" ),

    "mtu" : CameraTraits( "mtu", 0, 0, 8, int,
                          value=None,
                          units="kilobytes above 1500",
                          human_name="Packet Size",
                          desc="Additional Packet Size (Jumbo Frames)",
                          mode="rwa" ),

    "iscale" : CameraTraits( "iscale", 1, 1, 128, int,
                          value=None,
                          units="Powers of 2",
                          human_name="Image decimation",
                          desc="Scale down image by powers of 2",
                          mode="rwa" ),

    "idelay" : CameraTraits( "idelay", 15, 3, 255, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Image Delay",
                          desc="Deley between sending fragmented images",
                          mode="rwa" ),

    "threshold" : CameraTraits( "threshold", 128, 0, 255, int,
                          value=None,
                          units="8-Bit Grey Level",
                          human_name="Threshold",
                          desc="Image Thresholding",
                          mode="rw" ),

    "numdets" : CameraTraits( "numdets", 13, 0, 80, int,
                          value=None,
                          units="10s of Centroids",
                          human_name="Centroids per Packet",
                          desc="Limit number of Centroids in a packet",
                          mode="rwa" ),

    "arpdelay" : CameraTraits( "arpdelay", 15, 0, 255, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Gratuitous ARP Delay",
                          desc="ARP Interval",
                          mode="rwa" ),

    # 3-axis IMU
    "impactflags" : CameraTraits( "impactflags", 60, 0, 60, int,
                          value=None,
                          units="",
                          human_name="Impact Warning Flags",
                          desc="",
                          mode="rw" ),

    "impactlimit" : CameraTraits( "impactlimit", 150, 0, 255, int,
                          value=None,
                          units="1/10th RMS deviation",
                          human_name="Impact Threashold",
                          desc="RMS Impact Deviation Threashold ",
                          mode="rwa" ),

    "impactrefx": CameraTraits( "impactrefx", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference X",
                          desc="Calibrated IMU Pos X",
                          mode="rwa" ),

    "impactrefy": CameraTraits( "impactrefy", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference Y",
                          desc="Calibrated IMU Pos Y",
                          mode="rwa" ),

    "impactrefz": CameraTraits( "impactrefz", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference Z",
                          desc="Calibrated IMU Pos Z",
                          mode="rwa" ),

    "impactvalx": CameraTraits( "impactvalx", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value X",
                            desc="Measured IMU Pos X",
                            mode="ra" ),

    "impactvaly": CameraTraits( "impactvaly", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value Y",
                            desc="Measured IMU Pos Y",
                            mode="ra" ),

    "impactvalz": CameraTraits( "impactvalz", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value Z",
                            desc="Measured IMU Pos Z",
                            mode="ra" ),

    # Masking Zones (auto Generated)
    "maskzone01x": CameraTraits( "maskzone01x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 LEFT",
                                 desc="Mask 01 position Left",
                                 mode="rw" ),
               
    "maskzone01y": CameraTraits( "maskzone01y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 TOP",
                                 desc="Mask 01 position Top",
                                 mode="rw" ),
               
    "maskzone01m": CameraTraits( "maskzone01m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 RIGHT",
                                 desc="Mask 01 position Right",
                                 mode="rw" ),
               
    "maskzone01n": CameraTraits( "maskzone01n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 BOTTOM",
                                 desc="Mask 01 position Bottom",
                                 mode="rw" ),
               
    "maskzone02x": CameraTraits( "maskzone02x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 LEFT",
                                 desc="Mask 02 position Left",
                                 mode="rw" ),
               
    "maskzone02y": CameraTraits( "maskzone02y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 TOP",
                                 desc="Mask 02 position Top",
                                 mode="rw" ),
               
    "maskzone02m": CameraTraits( "maskzone02m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 RIGHT",
                                 desc="Mask 02 position Right",
                                 mode="rw" ),
               
    "maskzone02n": CameraTraits( "maskzone02n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 BOTTOM",
                                 desc="Mask 02 position Bottom",
                                 mode="rw" ),
               
    "maskzone03x": CameraTraits( "maskzone03x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 LEFT",
                                 desc="Mask 03 position Left",
                                 mode="rw" ),
               
    "maskzone03y": CameraTraits( "maskzone03y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 TOP",
                                 desc="Mask 03 position Top",
                                 mode="rw" ),
               
    "maskzone03m": CameraTraits( "maskzone03m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 RIGHT",
                                 desc="Mask 03 position Right",
                                 mode="rw" ),
               
    "maskzone03n": CameraTraits( "maskzone03n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 BOTTOM",
                                 desc="Mask 03 position Bottom",
                                 mode="rw" ),
               
    "maskzone04x": CameraTraits( "maskzone04x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 LEFT",
                                 desc="Mask 04 position Left",
                                 mode="rw" ),
               
    "maskzone04y": CameraTraits( "maskzone04y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 TOP",
                                 desc="Mask 04 position Top",
                                 mode="rw" ),
               
    "maskzone04m": CameraTraits( "maskzone04m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 RIGHT",
                                 desc="Mask 04 position Right",
                                 mode="rw" ),
               
    "maskzone04n": CameraTraits( "maskzone04n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 BOTTOM",
                                 desc="Mask 04 position Bottom",
                                 mode="rw" ),
               
    "maskzone05x": CameraTraits( "maskzone05x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 LEFT",
                                 desc="Mask 05 position Left",
                                 mode="rw" ),
               
    "maskzone05y": CameraTraits( "maskzone05y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 TOP",
                                 desc="Mask 05 position Top",
                                 mode="rw" ),
               
    "maskzone05m": CameraTraits( "maskzone05m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 RIGHT",
                                 desc="Mask 05 position Right",
                                 mode="rw" ),
               
    "maskzone05n": CameraTraits( "maskzone05n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 BOTTOM",
                                 desc="Mask 05 position Bottom",
                                 mode="rw" ),
               
    "maskzone06x": CameraTraits( "maskzone06x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 LEFT",
                                 desc="Mask 06 position Left",
                                 mode="rw" ),
               
    "maskzone06y": CameraTraits( "maskzone06y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 TOP",
                                 desc="Mask 06 position Top",
                                 mode="rw" ),
               
    "maskzone06m": CameraTraits( "maskzone06m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 RIGHT",
                                 desc="Mask 06 position Right",
                                 mode="rw" ),
               
    "maskzone06n": CameraTraits( "maskzone06n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 BOTTOM",
                                 desc="Mask 06 position Bottom",
                                 mode="rw" ),
               
    "maskzone07x": CameraTraits( "maskzone07x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 LEFT",
                                 desc="Mask 07 position Left",
                                 mode="rw" ),
               
    "maskzone07y": CameraTraits( "maskzone07y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 TOP",
                                 desc="Mask 07 position Top",
                                 mode="rw" ),
               
    "maskzone07m": CameraTraits( "maskzone07m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 RIGHT",
                                 desc="Mask 07 position Right",
                                 mode="rw" ),
               
    "maskzone07n": CameraTraits( "maskzone07n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 BOTTOM",
                                 desc="Mask 07 position Bottom",
                                 mode="rw" ),
               
    "maskzone08x": CameraTraits( "maskzone08x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 LEFT",
                                 desc="Mask 08 position Left",
                                 mode="rw" ),
               
    "maskzone08y": CameraTraits( "maskzone08y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 TOP",
                                 desc="Mask 08 position Top",
                                 mode="rw" ),
               
    "maskzone08m": CameraTraits( "maskzone08m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 RIGHT",
                                 desc="Mask 08 position Right",
                                 mode="rw" ),
               
    "maskzone08n": CameraTraits( "maskzone08n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 BOTTOM",
                                 desc="Mask 08 position Bottom",
                                 mode="rw" ),
               
    "maskzone09x": CameraTraits( "maskzone09x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 LEFT",
                                 desc="Mask 09 position Left",
                                 mode="rw" ),
               
    "maskzone09y": CameraTraits( "maskzone09y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 TOP",
                                 desc="Mask 09 position Top",
                                 mode="rw" ),
               
    "maskzone09m": CameraTraits( "maskzone09m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 RIGHT",
                                 desc="Mask 09 position Right",
                                 mode="rw" ),
               
    "maskzone09n": CameraTraits( "maskzone09n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 BOTTOM",
                                 desc="Mask 09 position Bottom",
                                 mode="rw" ),
               
    "maskzone10x": CameraTraits( "maskzone10x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 LEFT",
                                 desc="Mask 10 position Left",
                                 mode="rw" ),
               
    "maskzone10y": CameraTraits( "maskzone10y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 TOP",
                                 desc="Mask 10 position Top",
                                 mode="rw" ),
               
    "maskzone10m": CameraTraits( "maskzone10m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 RIGHT",
                                 desc="Mask 10 position Right",
                                 mode="rw" ),
               
    "maskzone10n": CameraTraits( "maskzone10n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 BOTTOM",
                                 desc="Mask 10 position Bottom",
                                 mode="rw" ),
               
    "maskzone11x": CameraTraits( "maskzone11x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 LEFT",
                                 desc="Mask 11 position Left",
                                 mode="rw" ),
               
    "maskzone11y": CameraTraits( "maskzone11y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 TOP",
                                 desc="Mask 11 position Top",
                                 mode="rw" ),
               
    "maskzone11m": CameraTraits( "maskzone11m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 RIGHT",
                                 desc="Mask 11 position Right",
                                 mode="rw" ),
               
    "maskzone11n": CameraTraits( "maskzone11n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 BOTTOM",
                                 desc="Mask 11 position Bottom",
                                 mode="rw" ),
               
    "maskzone12x": CameraTraits( "maskzone12x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 LEFT",
                                 desc="Mask 12 position Left",
                                 mode="rw" ),
               
    "maskzone12y": CameraTraits( "maskzone12y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 TOP",
                                 desc="Mask 12 position Top",
                                 mode="rw" ),
               
    "maskzone12m": CameraTraits( "maskzone12m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 RIGHT",
                                 desc="Mask 12 position Right",
                                 mode="rw" ),
               
    "maskzone12n": CameraTraits( "maskzone12n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 BOTTOM",
                                 desc="Mask 12 position Bottom",
                                 mode="rw" ),
               
    "maskzone13x": CameraTraits( "maskzone13x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 LEFT",
                                 desc="Mask 13 position Left",
                                 mode="rw" ),
               
    "maskzone13y": CameraTraits( "maskzone13y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 TOP",
                                 desc="Mask 13 position Top",
                                 mode="rw" ),
               
    "maskzone13m": CameraTraits( "maskzone13m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 RIGHT",
                                 desc="Mask 13 position Right",
                                 mode="rw" ),
               
    "maskzone13n": CameraTraits( "maskzone13n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 BOTTOM",
                                 desc="Mask 13 position Bottom",
                                 mode="rw" ),
               
    "maskzone14x": CameraTraits( "maskzone14x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 LEFT",
                                 desc="Mask 14 position Left",
                                 mode="rw" ),
               
    "maskzone14y": CameraTraits( "maskzone14y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 TOP",
                                 desc="Mask 14 position Top",
                                 mode="rw" ),
               
    "maskzone14m": CameraTraits( "maskzone14m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 RIGHT",
                                 desc="Mask 14 position Right",
                                 mode="rw" ),
               
    "maskzone14n": CameraTraits( "maskzone14n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 BOTTOM",
                                 desc="Mask 14 position Bottom",
                                 mode="rw" ),
               
    "maskzone15x": CameraTraits( "maskzone15x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 LEFT",
                                 desc="Mask 15 position Left",
                                 mode="rw" ),
               
    "maskzone15y": CameraTraits( "maskzone15y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 TOP",
                                 desc="Mask 15 position Top",
                                 mode="rw" ),
               
    "maskzone15m": CameraTraits( "maskzone15m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 RIGHT",
                                 desc="Mask 15 position Right",
                                 mode="rw" ),
               
    "maskzone15n": CameraTraits( "maskzone15n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 BOTTOM",
                                 desc="Mask 15 position Bottom",
                                 mode="rw" ),
               
    "maskzone16x": CameraTraits( "maskzone16x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 LEFT",
                                 desc="Mask 16 position Left",
                                 mode="rw" ),
               
    "maskzone16y": CameraTraits( "maskzone16y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 TOP",
                                 desc="Mask 16 position Top",
                                 mode="rw" ),
               
    "maskzone16m": CameraTraits( "maskzone16m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 RIGHT",
                                 desc="Mask 16 position Right",
                                 mode="rw" ),
               
    "maskzone16n": CameraTraits( "maskzone16n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 BOTTOM",
                                 desc="Mask 16 position Bottom",
                                 mode="rw" ),

}

# (reg, sz, need hiRegs)
TRAIT_LOCATIONS = {
        "fps"         : ( 200, 1, False ),
        "strobe"      : ( 204, 1, False ),
        "shutter"     : ( 206, 1, False ),
        "mtu"         : ( 251, 1, False ),
        "iscale"      : ( 252, 1, False ),
        "idelay"      : ( 253, 1, False ),
        "threshold"   : ( 255, 1, False ),
        "numdets"     : ( 254, 1, False ),
        "arpdelay"    : ( 226, 1, False ),

        # 3-axis IMU
        "impactflags" : ( 236, 1, False ),
        "impactlimit" : ( 249, 1, False ),
        "impactrefx"  : ( 214, 2, False ),
        "impactrefy"  : ( 216, 2, False ),
        "impactrefz"  : ( 218, 2, False ),
        "impactvalx"  : ( 230, 2, False ),
        "impactvaly"  : ( 232, 2, False ),
        "impactvalz"  : ( 234, 2, False ),

        # Masking Zones (auto Generated)
        "maskzone01x" : ( 300, 2, True ),
        "maskzone01y" : ( 302, 2, True ),
        "maskzone01m" : ( 304, 2, True ),
        "maskzone01n" : ( 306, 2, True ),
        "maskzone02x" : ( 308, 2, True ),
        "maskzone02y" : ( 310, 2, True ),
        "maskzone02m" : ( 312, 2, True ),
        "maskzone02n" : ( 314, 2, True ),
        "maskzone03x" : ( 316, 2, True ),
        "maskzone03y" : ( 318, 2, True ),
        "maskzone03m" : ( 320, 2, True ),
        "maskzone03n" : ( 322, 2, True ),
        "maskzone04x" : ( 324, 2, True ),
        "maskzone04y" : ( 326, 2, True ),
        "maskzone04m" : ( 328, 2, True ),
        "maskzone04n" : ( 330, 2, True ),
        "maskzone05x" : ( 332, 2, True ),
        "maskzone05y" : ( 334, 2, True ),
        "maskzone05m" : ( 336, 2, True ),
        "maskzone05n" : ( 338, 2, True ),
        "maskzone06x" : ( 340, 2, True ),
        "maskzone06y" : ( 342, 2, True ),
        "maskzone06m" : ( 344, 2, True ),
        "maskzone06n" : ( 346, 2, True ),
        "maskzone07x" : ( 348, 2, True ),
        "maskzone07y" : ( 350, 2, True ),
        "maskzone07m" : ( 352, 2, True ),
        "maskzone07n" : ( 354, 2, True ),
        "maskzone08x" : ( 356, 2, True ),
        "maskzone08y" : ( 358, 2, True ),
        "maskzone08m" : ( 360, 2, True ),
        "maskzone08n" : ( 362, 2, True ),
        "maskzone09x" : ( 364, 2, True ),
        "maskzone09y" : ( 366, 2, True ),
        "maskzone09m" : ( 368, 2, True ),
        "maskzone09n" : ( 370, 2, True ),
        "maskzone10x" : ( 372, 2, True ),
        "maskzone10y" : ( 374, 2, True ),
        "maskzone10m" : ( 376, 2, True ),
        "maskzone10n" : ( 378, 2, True ),
        "maskzone11x" : ( 380, 2, True ),
        "maskzone11y" : ( 382, 2, True ),
        "maskzone11m" : ( 384, 2, True ),
        "maskzone11n" : ( 386, 2, True ),
        "maskzone12x" : ( 388, 2, True ),
        "maskzone12y" : ( 390, 2, True ),
        "maskzone12m" : ( 392, 2, True ),
        "maskzone12n" : ( 394, 2, True ),
        "maskzone13x" : ( 396, 2, True ),
        "maskzone13y" : ( 398, 2, True ),
        "maskzone13m" : ( 400, 2, True ),
        "maskzone13n" : ( 402, 2, True ),
        "maskzone14x" : ( 404, 2, True ),
        "maskzone14y" : ( 406, 2, True ),
        "maskzone14m" : ( 408, 2, True ),
        "maskzone14n" : ( 410, 2, True ),
        "maskzone15x" : ( 412, 2, True ),
        "maskzone15y" : ( 414, 2, True ),
        "maskzone15m" : ( 416, 2, True ),
        "maskzone15n" : ( 418, 2, True ),
        "maskzone16x" : ( 420, 2, True ),
        "maskzone16y" : ( 422, 2, True ),
        "maskzone16m" : ( 424, 2, True ),
        "maskzone16n" : ( 426, 2, True ),
}

# reg:name
TRAIT_REV_LUT = { v[0]:k for k,v in TRAIT_LOCATIONS.items() }

CAMERA_COMMANDS = {
    "start"   : b"n", # Begin Streaming Centroids
    "stop"    : b" ", # End Streaming Centroids
    "single"  : b"p", # Send an Image
    "stream"  : b"s", # Begin Streaming Images
}

CAMERA_REQUESTS = {
    "regslo"  : b"r", # Request 'State' Regs 200~255
    "regshi"  : b"R", # Request 'Superset' Regs 200~1023 (Inc Exclusions)
    "version" : b"?", # Request Version
    "hello"   : b"h", # Request the letter h
}

CAMERA_COMMANDS_REV = { v:k for k,v in CAMERA_COMMANDS.items() }
CAMERA_REQUESTS_REV = { v:k for k,v in CAMERA_REQUESTS.items() }

CAM_EXE_PARAMS = (sorted( CAMERA_COMMANDS.keys() ))
CAM_REQ_PARAMS = (sorted( CAMERA_REQUESTS.keys() ))
CAM_SET_PARAMS = (sorted( CAMERA_CAPABILITIES.keys() ))

# Sync Config Data -------------------------------------------------------------
SYNC_CAPABILITIES = {
    "dep_fps": CameraTraits( "dep_fps", 19, 0, 60, int,
                         value=None,
                         units="Frames per Second",
                         human_name="Frame Rate",
                         desc="Sync unit Frame Rate (depricated register)",
                         mode="rwx"),

    "dep_multi": CameraTraits( "dep_multi", 2, 1, 5, int,
                             value=None,
                             units="Sync Multiplier",
                             human_name="Frame Rate",
                             desc="Sync unit Frame Rate (depricated register)",
                             mode="rwx" ),

    "fw_version": CameraTraits( "fw_version", 0, -1, -1, int,
                             value=None,
                             units="",
                             human_name="Firmware Version",
                             desc="Sync Unit Firmware Version",
                             mode="ra" ),

    "framerate": CameraTraits( "framerate", 0x001E0000, -1, -1, int,
                             value=None,
                             units="Frames per Second",
                             human_name="Sync Frame Rate",
                             desc="Sync Frame Rate",
                             mode="rw" ),

    "tc_h": CameraTraits( "tc_h", 0, 0, 23, int,
                             value=None,
                             units="Hours",
                             human_name="Timecode Hours",
                             desc="Sync Timecode Hours",
                             mode="rw" ),
    "tc_m": CameraTraits( "tc_m", 59, 0, 59, int,
                             value=None,
                             units="Minutes",
                             human_name="Timecode Minutes",
                             desc="Sync Timecode Minutes",
                             mode="rw" ),
    "tc_s": CameraTraits( "tc_s", 50, 0, 59, int,
                             value=None,
                             units="Seconds",
                             human_name="Timecode Seconds",
                             desc="Sync Timecode Seconds",
                             mode="rw" ),
    "tc_f": CameraTraits( "tc_f", 0, 0, 29, int,
                             value=None,
                             units="Frames",
                             human_name="Timecode Frames",
                             desc="Sync Timecode Frames",
                             mode="rw" ),
    "tc_source": CameraTraits( "tc_source", 0, 0, 1, int,
                             value=None,
                             units="",
                             human_name="Frame Rate",
                             desc="Timecode Source",
                             mode="r" ),
    "sync_source": CameraTraits( "sync_source", 3, 1, 3, int,
                             value=None,
                             units="Frames per Second",
                             human_name="Frame Rate",
                             desc="Sync Source",
                             mode="r" ),
    "sync_multi": CameraTraits( "sync_multi", 2, 1, 6, int,
                             value=None,
                             units="x",
                             human_name="Sync Multiplier",
                             desc="Sync Multiplier",
                             mode="rw" ),
    "sync_out": CameraTraits( "sync_out", 0, 0, 1, int,
                             value=None,
                             units="",
                             human_name="Sync Output",
                             desc="Sync Output (Camera Trigger)",
                             mode="rw" ),
    "sync_divisor": CameraTraits( "sync_divisor", 1, 1, 6, int,
                             value=None,
                             units="",
                             human_name="Sync Divisor",
                             desc="Sync Divisor",
                             mode="rw" ),
    "tc_emit": CameraTraits( "tc_emit", 1, 0, 1, int,
                             value=None,
                             units="",
                             human_name="Timecode Server",
                             desc="Enable timecode server",
                             mode="rw" ),
    "diag_sync_in": CameraTraits( "diag_sync_in", 19, 0, 60, int,
                             value=None,
                             units="Samples @104Mhz (9.6ns)",
                             human_name="Sync In Period",
                             desc="Sync input period",
                             mode="ra" ),
    "diag_sync_out": CameraTraits( "diag_sync_out", 19, 0, 60, int,
                             value=None,
                             units="Samples @104MHz (9.6ns)",
                             human_name="Sync Out Period",
                             desc="Sync output period",
                             mode="rw" ),

    "diag_tc_in": CameraTraits( "diag_tc_in", 19, 0, 60, int,
                               value=None,
                               units="Timecode",
                               human_name="Input Timecode",
                               desc="Incoming timecode",
                               mode="ra" ),

    "diag_tc_mod": CameraTraits( "diag_tc_mod", 19, 0, 60, int,
                               value=None,
                               units="",
                               human_name="Timecode Modulus",
                               desc="Timecode Modulus (Diagnostic)",
                               mode="ra" ),

    "diag_tc_algo": CameraTraits( "diag_tc_algo", 19, 0, 60, int,
                               value=None,
                               units="",
                               human_name="",
                               desc="Timecode Algorytthum (Diagnostic)",
                               mode="ra" ),

    "sync_offset": CameraTraits( "sync_offset", 19, 0, 60, int,
                               value=None,
                               units="Samples @104MHz (9.6ns)",
                               human_name="Sync Offset",
                               desc="Sync Offset",
                               mode="rwa" ),
}

SYNC_LOCATIONS = {
    "dep_fps"         : ( 200, 1, False ),
    "dep_multi"       : ( 207, 1, False ),
    "fw_version"      : ( 208, 1, False ),
    "framerate"       : ( 216, 4, False ),
    "tc_flood"        : ( 220, 4, False ), # flood fill tc
    "tc_h"            : ( 220, 1, False ),
    "tc_m"            : ( 221, 1, False ),
    "tc_s"            : ( 222, 1, False ),
    "tc_f"            : ( 223, 1, False ),
    "tc_source"       : ( 224, 1, False ),
    "sync_source"     : ( 225, 1, False ),
    "sync_multi"      : ( 226, 1, False ),
    "sync_out"        : ( 227, 1, False ),
    "sync_divisor"    : ( 228, 1, False ),
    "tc_emit"         : ( 229, 1, False ),
    "diag_sync_in"    : ( 230, 4, False ),
    "diag_sync_out"   : ( 234, 4, False ),
    "diag_tc_in"      : ( 238, 4, False ),
    "diag_tc_mod"     : ( 242, 1, False ),
    "diag_tc_algo"    : ( 243, 1, False ),
    "sync_offset"     : ( 244, 4, False ),
}

SYNC_COMMANDS = {
    "cams_on"    : b"+", # Turn all Cameras ON
    "cams_off"   : b"-", # Turn all Cameras OFF
    "cams_reset" : b"/", # Reset Cameras
    "sync_ttl"   : b"t", # Sync to TTL / GPIO
    "sync_vid"   : b"v", # Sync to Genlock / Tri-Sync / Video
}

SYNC_REQUESTS = {
    "regslo"     : b"r", # Request 'State' Regs 200~255
    "hello"      : b"h", # Request the letter h
}

SYNC_COMMANDS_REV = { v:k for k,v in SYNC_COMMANDS.items() }
SYNC_REQUESTS_REV = { v:k for k,v in SYNC_REQUESTS.items() }

SYNC_SET_PARAMS = (sorted( SYNC_LOCATIONS.keys() ))

# Universal Commands -----------------------------------------------------------
CHAR_COMMAND_VAL  = ord( b"*" ) # (BB) unit8
SHORT_COMMAND_VAL = ord( b"~" ) # (Hh) uint16 with (u)int16 data
WORD_COMMAND_VAL  = ord( b"!" ) # (BI) uint8 with uint32 data


# Data Packet info -------------------------------------------------------------
PACKET_TYPES = {
    "centroids" : 0x00, # Could be multi-packet
    "imagedata" : 0x0A, # will have to be multi Packet for 1MB~4MB images
    "regslo"    : 0x0C, # 56 Bytes
    "regshi"    : 0x0E, # 823 Bytes
    "textslug"  : 0x10, # Logging Text
    "version"   : 0x11, # Version Text
}

ROID_COMPRESSION = {
    "compressed" : 0x00, # XX, YY, D
    "full_sized" : 0x04, # XXx, YYy, H, W, Dd
}

PACKET_TYPES_REV = { v:k for k,v in PACKET_TYPES.items() }
ROID_COMPRESSION_REV = { v:k for k,v in ROID_COMPRESSION.items() }

HEADER_PACK_FMT = ">HHBBBBBBBB"
HEADER_READ_FMT = ">HHBBBBI" # Read the tc as an int
HEADER_DGAM_FMT = "<HH"
HEADER_IMGS_FMT = ">HH"

# Networking Configurations ----------------------------------------------------
UDP_PORT_TX = 1234 # Camera Xmis
UDP_PORT_RX = 1235 # Camera Recv

# Network Sync Pulses
MCAST_GRP  = "224.10.6.10"
MCAST_PORT = 5678
MCAST_TTL  = 6

# Networking functions
def composeCommand( command_name, value ):
    """ Compose a command in the Camera wire format
        command_name : (str) Name of the command
        value : (num) This is assumed to be cast and valid

        returns Tuple ( (bytes) command, (bool) in_regshi )
    """
    in_regshi = False
    cmd_str = b""
    payload = b""

    # Exe command
    if (command_name in CAM_EXE_PARAMS):
        cmd_str = CAMERA_COMMANDS[ command_name ]

    # Req command
    if (command_name in CAM_REQ_PARAMS):
        cmd_str = CAMERA_REQUESTS[ command_name ]

    # Set commands are a bit harder...
    if (command_name in CAM_SET_PARAMS):

        reg, size, in_regshi = TRAIT_LOCATIONS[ command_name ]

        if (size == 1):
            payload = struct.pack( ">BB", reg, value )
            cmd_str = b"*"

        if (size == 2):
            payload = struct.pack( ">Hh", reg, value )
            cmd_str = b"~"

    return (cmd_str + payload, in_regshi)
# composeCommand( command_name, value )

def encodePacket( frm_cnt, num_dts, compression, dtype, sml_cnt, time_stamp, dgm_no, dgm_cnt, data, img_os=None, img_sz=None ):
    """
    Encode a Packet

    :param frm_cnt: (int) number of frames sent, rolling up to 8191
    :param num_dts: (int) number of detections in the packet/sequence
    :param compression: (byte) Centroid Compression
    :param dtype: (byte) PACKET_TYPES
    :param sml_cnt: (byte) Small rolling count up to 256
    :param time_stamp: (4bytes) Timecode of this Frame HH:MM:SS:FF
    :param dgm_no: (int) Fragmented packet number
    :param dgm_cnt: (int) Total number of Fragmented Packets
    :param data: (bytes) the data block

    :return: (bytes) The Encoded packet
    """
    # encode the frm_cnt
    frame = (((frm_cnt & 0x1F80) << 1) | 0x8000) | (frm_cnt & 0x007F)

    # encode the compression mode in the centroid count
    count = (((num_dts & 0x0380) << 1) | 0x4000) | (num_dts & 0x007F) | ((compression & 0x0007) << 11)

    # flag for future use
    flag = 0

    head_sz = 24 if dtype == PACKET_TYPES[ "imagedata" ] else 16 # 2 extra Halfs in an image

    t_h, t_m, t_s, t_f = time_stamp[0], time_stamp[1], time_stamp[2], time_stamp[3]

    header  = struct.pack( HEADER_PACK_FMT, frame, count, flag, dtype, sml_cnt, head_sz, t_h, t_m, t_s, t_f )
    header += struct.pack( HEADER_DGAM_FMT, dgm_no, dgm_cnt )
    if( dtype == PACKET_TYPES[ "imagedata" ] ):
        header += struct.pack( HEADER_IMGS_FMT, img_os, img_sz )

    return header + data
# encodePacket( ... )

def decodePacket( data ):
    """
    Decode a packet from the piCamera.  How to hand off this data? I don't know.  That's for the Arbiter in the end.
    regs need to be handed to anyone who's interested. Images will be useful in cam setup, vital in ROMing, and handy in
    general shooting.  Centroids need to be collated into "Frames" and shipped in a timely fashion.

    :param data: (bytes) raw data from the packet

    :return: (Tuple)   (dtype,      : Data Type
                        time_stamp, : Timecode
                        num_dts,    : Num Centroids in Packet
                        dgm_no,     : Packet number (if frag'ed 'dets) OR Image Offset if Image
                        dgm_cnt,    : Packet count (if frag'ed 'dets) OR Image Size if Image
                        data )      : The data
    """
    packet_sz = len( data )

    if( packet_sz == 1 ):
        return ( PACKET_TYPES["textslug"], [-1,-1,-1,-1], 0, 1, 1, "Hello" )

    # unpack the header
    frame, count, flag, dtype, sml_cnt, head_sz, time_stamp = struct.unpack( HEADER_READ_FMT, data[:12] )

    if( dtype == PACKET_TYPES[ "imagedata" ] ):
        dgm_no, dgm_cnt = struct.unpack( HEADER_IMGS_FMT, data[16:24] ) # Image os / sz have equivalent use
    else:
        dgm_no, dgm_cnt = struct.unpack( HEADER_DGAM_FMT, data[12:16] )

    # Decode Header info -------------------------------------------------------
    # Frame Count
    frm_cnt = ((frame & 0x3f00) >> 1) | (frame & 0x007f)
    
    # Num Dets
    num_dts = ((count & 0x0700) >> 1) | (count & 0x007F)
    
    # Decode the Protocol
    compression = ((count & 0x3800) >> 11)
    
    # Digest & Data
    return ( dtype, time_stamp, num_dts, dgm_no, dgm_cnt, data[head_sz:] )

# decodePacket( data )

# Class
class PiCamera( object ):
    """ Class to handle management of a Camera's state.
        Also provides conveniences to dump as a 'bulk' statement, and JSON
        import / export functions
    """
    def __init__( self, camera_ip, id=None ):
        self.camera_ip = camera_ip
        self.id = id
        self._stateReset()

    def _stateReset( self ):
        self.hw_settings = deepcopy( CAMERA_CAPABILITIES )
        # these need to be JSONable
        self.md_settings = {} # Internal Meta Data - Camera Name
        self.ui_settings = {} # Future, Draw Options for the inevitable UI
        self.touched = set()  # register of hw settings that have been changed
        self.needs_to_push = False # flag that the state has't been sent to camera

    def toJSON( self ):
        hws = {} # changed hardware settings
        for param, val in self.hw_settings.items():
            if( val.value != val.default or param in self.touched ):
                hws[ param ] = val.value

        camera_config = {
            "HARDWARE"  : hws,
            "METADATA"  : self.md_settings,
            "INTERFACE" : self.ui_settings,
        }
        return json.dumps( camera_config, indent=4, sort_keys=True )

    def fromJSON( self, json_txt ):
        """
        Function to configure settings from a JSON file.  While this will update
        the Camera Object's state, actual commands need to be sent to the physical
        camera to bring about this configuration

        :param json_txt: (str) JSON of the camera's setings
        :return: None
        """
        self._stateReset()
        d = json.loads( json_txt )

        # do metadata
        for k, v in d["METADATA"].items():
            self.md_settings[ k ] = v

        # do ui
        for k, v in d["INTERFACE"].items():
            self.ui_settings[ k ] = v

        # do hardware
        for k, v in d["HARDWARE"].items():
            trait = self.hw_settings[ k ]
            if( trait.isValid(v) ):
                trait.value = v
                self.touched.add( k )

        # Note the settings have been updated, but not pushed to the camera.
        self.needs_to_push = True

    def toBulk( self ):
        """
        Create a bulk command to configure the camera's hardware.

        :return: (str) Bulk configuration Command
        """
        bulk = "bulk "
        for param, val in self.hw_settings.items():
            if( val.value != val.default or param in self.touched ):
                bulk += "set {} {};".format( param, val )
        return bulk

    @staticmethod
    def jsonToBulk( json_text ):
        d = json.loads( json_text )
        bulk = "bulk "
        for param, val in d["HARDWARE"].items():
            bulk += "set {} {};".format( param, val )
        return bulk

    @staticmethod
    def validateSet( param, str_val ):
        trait = CAMERA_CAPABILITIES[ param ]
        cast = trait.dtype( str_val )
        return trait.isValid( cast )

#class PiCamera( object )