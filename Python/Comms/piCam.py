""" Class to enable communications with a piCam """
from copy import deepcopy
import json
import struct

from . import CameraTraits

# Camera Configurations --------------------------------------------------------
CAMERA_CAPABILITIES = {
    "fps" : CameraTraits( "fps", 60, 0, 60, int,
                          value=None,
                          units="Frames per Second",
                          human_name="Frame Rate",
                          desc="Camera Frame Rate" ),

    "strobe" : CameraTraits( "strobe", 20, 0, 70, int,
                          value=None,
                          units="Watts",
                          human_name="Strobe Power",
                          desc="Strobe LED Power" ),

    "shutter" : CameraTraits( "shutter", 8, 2, 250, int,
                          value=None,
                          units="100's of uSecs",
                          human_name="Exposure Time",
                          desc="Shutter Period for camera" ),

    "mtu" : CameraTraits( "mtu", 0, 0, 8, int,
                          value=None,
                          units="kilobytes above 1500",
                          human_name="Packet Size",
                          desc="Additional Packet Size (Jumbo Frames)" ),

    "iscale" : CameraTraits( "iscale", 1, 1, 128, int,
                          value=None,
                          units="Powers of 2",
                          human_name="Image decimation",
                          desc="Scale down image by powers of 2" ),

    "idelay" : CameraTraits( "idelay", 15, 3, 255, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Image Delay",
                          desc="Deley between sending fragmented images" ),

    "threshold" : CameraTraits( "threshold", 128, 0, 255, int,
                          value=None,
                          units="8-Bit Grey Level",
                          human_name="Threshold",
                          desc="Image Thresholding" ),

    "numdets" : CameraTraits( "numdets", 13, 0, 80, int,
                          value=None,
                          units="10s of Centroids",
                          human_name="Centroids per Packet",
                          desc="Limit number of Centroids in a packet" ),

    "arpdelay" : CameraTraits( "arpdelay", 15, 0, 255, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Gratuitous ARP Delay",
                          desc="ARP Interval" ),

    # 3-axis IMU
    "impactflags" : CameraTraits( "impactflags", 60, 0, 60, int,
                          value=None,
                          units="Frames per Second",
                          human_name="Frame Rate",
                          desc="Camera Frame Rate" ),

    "impactlimit" : CameraTraits( "impactlimit", 150, 0, 255, int,
                          value=None,
                          units="1/10th RMS deviation",
                          human_name="Impact Threashold",
                          desc="RMS Impact Deviation Threashold " ),

    "impactrefx": CameraTraits( "impactrefx", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference X",
                          desc="Calibrated IMU Pos X" ),

    "impactrefy": CameraTraits( "impactrefy", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference Y",
                          desc="Calibrated IMU Pos Y" ),

    "impactrefz": CameraTraits( "impactrefz", 0, -1023, 1023, int,
                          value=None,
                          units="Arbitrary Units",
                          human_name="Impact Reference Z",
                          desc="Calibrated IMU Pos Z" ),

    "impactvalx": CameraTraits( "impactvalx", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value X",
                            desc="Measured IMU Pos X" ),

    "impactvaly": CameraTraits( "impactvaly", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value Y",
                            desc="Measured IMU Pos Y" ),

    "impactvalz": CameraTraits( "impactvalz", 0, -1023, 1023, int,
                            value=None,
                            units="Arbitrary Units",
                            human_name="Impact Value Z",
                            desc="Measured IMU Pos Z" ),

    # Masking Zones (auto Generated)
    "maskzone01x": CameraTraits( "maskzone01x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 X",
                                 desc="Mask 1 position Left" ),

    "maskzone01y": CameraTraits( "maskzone01y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 Y",
                                 desc="Mask 1 position Top" ),

    "maskzone01n": CameraTraits( "maskzone01n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 N",
                                 desc="Mask 1 position Right" ),

    "maskzone01m": CameraTraits( "maskzone01m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 01 M",
                                 desc="Mask 1 position Bottom" ),

    "maskzone02x": CameraTraits( "maskzone02x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 X",
                                 desc="Mask 2 position Left" ),

    "maskzone02y": CameraTraits( "maskzone02y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 Y",
                                 desc="Mask 2 position Top" ),

    "maskzone02n": CameraTraits( "maskzone02n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 N",
                                 desc="Mask 2 position Right" ),

    "maskzone02m": CameraTraits( "maskzone02m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 02 M",
                                 desc="Mask 2 position Bottom" ),

    "maskzone03x": CameraTraits( "maskzone03x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 X",
                                 desc="Mask 3 position Left" ),

    "maskzone03y": CameraTraits( "maskzone03y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 Y",
                                 desc="Mask 3 position Top" ),

    "maskzone03n": CameraTraits( "maskzone03n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 N",
                                 desc="Mask 3 position Right" ),

    "maskzone03m": CameraTraits( "maskzone03m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 03 M",
                                 desc="Mask 3 position Bottom" ),

    "maskzone04x": CameraTraits( "maskzone04x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 X",
                                 desc="Mask 4 position Left" ),

    "maskzone04y": CameraTraits( "maskzone04y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 Y",
                                 desc="Mask 4 position Top" ),

    "maskzone04n": CameraTraits( "maskzone04n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 N",
                                 desc="Mask 4 position Right" ),

    "maskzone04m": CameraTraits( "maskzone04m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 04 M",
                                 desc="Mask 4 position Bottom" ),

    "maskzone05x": CameraTraits( "maskzone05x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 X",
                                 desc="Mask 5 position Left" ),

    "maskzone05y": CameraTraits( "maskzone05y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 Y",
                                 desc="Mask 5 position Top" ),

    "maskzone05n": CameraTraits( "maskzone05n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 N",
                                 desc="Mask 5 position Right" ),

    "maskzone05m": CameraTraits( "maskzone05m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 05 M",
                                 desc="Mask 5 position Bottom" ),

    "maskzone06x": CameraTraits( "maskzone06x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 X",
                                 desc="Mask 6 position Left" ),

    "maskzone06y": CameraTraits( "maskzone06y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 Y",
                                 desc="Mask 6 position Top" ),

    "maskzone06n": CameraTraits( "maskzone06n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 N",
                                 desc="Mask 6 position Right" ),

    "maskzone06m": CameraTraits( "maskzone06m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 06 M",
                                 desc="Mask 6 position Bottom" ),

    "maskzone07x": CameraTraits( "maskzone07x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 X",
                                 desc="Mask 7 position Left" ),

    "maskzone07y": CameraTraits( "maskzone07y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 Y",
                                 desc="Mask 7 position Top" ),

    "maskzone07n": CameraTraits( "maskzone07n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 N",
                                 desc="Mask 7 position Right" ),

    "maskzone07m": CameraTraits( "maskzone07m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 07 M",
                                 desc="Mask 7 position Bottom" ),

    "maskzone08x": CameraTraits( "maskzone08x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 X",
                                 desc="Mask 8 position Left" ),

    "maskzone08y": CameraTraits( "maskzone08y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 Y",
                                 desc="Mask 8 position Top" ),

    "maskzone08n": CameraTraits( "maskzone08n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 N",
                                 desc="Mask 8 position Right" ),

    "maskzone08m": CameraTraits( "maskzone08m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 08 M",
                                 desc="Mask 8 position Bottom" ),

    "maskzone09x": CameraTraits( "maskzone09x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 X",
                                 desc="Mask 9 position Left" ),

    "maskzone09y": CameraTraits( "maskzone09y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 Y",
                                 desc="Mask 9 position Top" ),

    "maskzone09n": CameraTraits( "maskzone09n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 N",
                                 desc="Mask 9 position Right" ),

    "maskzone09m": CameraTraits( "maskzone09m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 09 M",
                                 desc="Mask 9 position Bottom" ),

    "maskzone10x": CameraTraits( "maskzone10x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 X",
                                 desc="Mask 10 position Left" ),

    "maskzone10y": CameraTraits( "maskzone10y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 Y",
                                 desc="Mask 10 position Top" ),

    "maskzone10n": CameraTraits( "maskzone10n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 N",
                                 desc="Mask 10 position Right" ),

    "maskzone10m": CameraTraits( "maskzone10m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 10 M",
                                 desc="Mask 10 position Bottom" ),

    "maskzone11x": CameraTraits( "maskzone11x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 X",
                                 desc="Mask 11 position Left" ),

    "maskzone11y": CameraTraits( "maskzone11y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 Y",
                                 desc="Mask 11 position Top" ),

    "maskzone11n": CameraTraits( "maskzone11n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 N",
                                 desc="Mask 11 position Right" ),

    "maskzone11m": CameraTraits( "maskzone11m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 11 M",
                                 desc="Mask 11 position Bottom" ),

    "maskzone12x": CameraTraits( "maskzone12x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 X",
                                 desc="Mask 12 position Left" ),

    "maskzone12y": CameraTraits( "maskzone12y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 Y",
                                 desc="Mask 12 position Top" ),

    "maskzone12n": CameraTraits( "maskzone12n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 N",
                                 desc="Mask 12 position Right" ),

    "maskzone12m": CameraTraits( "maskzone12m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 12 M",
                                 desc="Mask 12 position Bottom" ),

    "maskzone13x": CameraTraits( "maskzone13x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 X",
                                 desc="Mask 13 position Left" ),

    "maskzone13y": CameraTraits( "maskzone13y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 Y",
                                 desc="Mask 13 position Top" ),

    "maskzone13n": CameraTraits( "maskzone13n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 N",
                                 desc="Mask 13 position Right" ),

    "maskzone13m": CameraTraits( "maskzone13m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 13 M",
                                 desc="Mask 13 position Bottom" ),

    "maskzone14x": CameraTraits( "maskzone14x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 X",
                                 desc="Mask 14 position Left" ),

    "maskzone14y": CameraTraits( "maskzone14y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 Y",
                                 desc="Mask 14 position Top" ),

    "maskzone14n": CameraTraits( "maskzone14n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 N",
                                 desc="Mask 14 position Right" ),

    "maskzone14m": CameraTraits( "maskzone14m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 14 M",
                                 desc="Mask 14 position Bottom" ),

    "maskzone15x": CameraTraits( "maskzone15x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 X",
                                 desc="Mask 15 position Left" ),

    "maskzone15y": CameraTraits( "maskzone15y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 Y",
                                 desc="Mask 15 position Top" ),

    "maskzone15n": CameraTraits( "maskzone15n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 N",
                                 desc="Mask 15 position Right" ),

    "maskzone15m": CameraTraits( "maskzone15m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 15 M",
                                 desc="Mask 15 position Bottom" ),

    "maskzone16x": CameraTraits( "maskzone16x", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 X",
                                 desc="Mask 16 position Left" ),

    "maskzone16y": CameraTraits( "maskzone16y", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 Y",
                                 desc="Mask 16 position Top" ),

    "maskzone16n": CameraTraits( "maskzone16n", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 N",
                                 desc="Mask 16 position Right" ),

    "maskzone16m": CameraTraits( "maskzone16m", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone 16 M",
                                 desc="Mask 16 position Bottom" ),
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
        "maskzone01n" : ( 304, 2, True ),
        "maskzone01m" : ( 306, 2, True ),
        "maskzone02x" : ( 308, 2, True ),
        "maskzone02y" : ( 310, 2, True ),
        "maskzone02n" : ( 312, 2, True ),
        "maskzone02m" : ( 314, 2, True ),
        "maskzone03x" : ( 316, 2, True ),
        "maskzone03y" : ( 318, 2, True ),
        "maskzone03n" : ( 320, 2, True ),
        "maskzone03m" : ( 322, 2, True ),
        "maskzone04x" : ( 324, 2, True ),
        "maskzone04y" : ( 326, 2, True ),
        "maskzone04n" : ( 328, 2, True ),
        "maskzone04m" : ( 330, 2, True ),
        "maskzone05x" : ( 332, 2, True ),
        "maskzone05y" : ( 334, 2, True ),
        "maskzone05n" : ( 336, 2, True ),
        "maskzone05m" : ( 338, 2, True ),
        "maskzone06x" : ( 340, 2, True ),
        "maskzone06y" : ( 342, 2, True ),
        "maskzone06n" : ( 344, 2, True ),
        "maskzone06m" : ( 346, 2, True ),
        "maskzone07x" : ( 348, 2, True ),
        "maskzone07y" : ( 350, 2, True ),
        "maskzone07n" : ( 352, 2, True ),
        "maskzone07m" : ( 354, 2, True ),
        "maskzone08x" : ( 356, 2, True ),
        "maskzone08y" : ( 358, 2, True ),
        "maskzone08n" : ( 360, 2, True ),
        "maskzone08m" : ( 362, 2, True ),
        "maskzone09x" : ( 364, 2, True ),
        "maskzone09y" : ( 366, 2, True ),
        "maskzone09n" : ( 368, 2, True ),
        "maskzone09m" : ( 370, 2, True ),
        "maskzone10x" : ( 372, 2, True ),
        "maskzone10y" : ( 374, 2, True ),
        "maskzone10n" : ( 376, 2, True ),
        "maskzone10m" : ( 378, 2, True ),
        "maskzone11x" : ( 380, 2, True ),
        "maskzone11y" : ( 382, 2, True ),
        "maskzone11n" : ( 384, 2, True ),
        "maskzone11m" : ( 386, 2, True ),
        "maskzone12x" : ( 388, 2, True ),
        "maskzone12y" : ( 390, 2, True ),
        "maskzone12n" : ( 392, 2, True ),
        "maskzone12m" : ( 394, 2, True ),
        "maskzone13x" : ( 396, 2, True ),
        "maskzone13y" : ( 398, 2, True ),
        "maskzone13n" : ( 400, 2, True ),
        "maskzone13m" : ( 402, 2, True ),
        "maskzone14x" : ( 404, 2, True ),
        "maskzone14y" : ( 406, 2, True ),
        "maskzone14n" : ( 408, 2, True ),
        "maskzone14m" : ( 410, 2, True ),
        "maskzone15x" : ( 412, 2, True ),
        "maskzone15y" : ( 414, 2, True ),
        "maskzone15n" : ( 416, 2, True ),
        "maskzone15m" : ( 418, 2, True ),
        "maskzone16x" : ( 420, 2, True ),
        "maskzone16y" : ( 422, 2, True ),
        "maskzone16n" : ( 424, 2, True ),
        "maskzone16m" : ( 426, 2, True ),
}

# reg:name
TRAIT_REV_LUT = { v[0]:k for k,v in TRAIT_LOCATIONS.items() }

CAMERA_COMMANDS = {
    "start"  : b"n", # Begin Streaming Centroids
    "stop"   : b" ", # End Streaming Centroids
    "single" : b"p", # Send an Image
    "stream" : b"s", # Begin Streaming Images
}

CAMERA_REQUESTS = {
    "regslo"  : b"r",  # Request 'State' Regs 200~255
    "regshi"  : b"R",  # Request 'Superset' Regs 200~1023 (Inc Exclusions)
    "version" : b"?",  # Request Version
    "hello"   : b"h",  # Request the letter h
}

CHAR_COMMAND_VAL  = ord( b"*" ) # (BB) unit8
SHORT_COMMAND_VAL = ord( b"~" ) # (Hh) uint16 with int16 data

CAMERA_COMMANDS_REV = { v:k for k,v in CAMERA_COMMANDS.items() }
CAMERA_REQUESTS_REV = { v:k for k,v in CAMERA_REQUESTS.items() }

KNOWN_EXE_PARAMS = ( sorted( CAMERA_COMMANDS.keys() ) )
KNOWN_REQ_PARAMS = ( sorted( CAMERA_REQUESTS.keys() ) )
KNOWN_SET_PARAMS = ( sorted( CAMERA_CAPABILITIES.keys() ) )

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
    if (command_name in KNOWN_EXE_PARAMS):
        cmd_str = CAMERA_COMMANDS[ command_name ]

    # Req command
    if (command_name in KNOWN_REQ_PARAMS):
        cmd_str = CAMERA_REQUESTS[ command_name ]

    # Set commands are a bit harder...
    if (command_name in KNOWN_SET_PARAMS):

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