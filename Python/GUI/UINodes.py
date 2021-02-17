""" Attributes of Core.Nodes that are presented to the UI.

    These are separated in order to keep the Core.Nodes clean when operating in
    a headless mode.
"""

from GUI import Nodes

class NodeTrait1D( object ):
    """
        Object describing controllable trait of some parameter or attribute.
        It holds GUI presentable data like a human readable name, description,
        min and max values, and a "Castor" to get fom str to the correct type.

        'mode' flags are a combination of Read, Write, Advanced, eXclude
            Eg. "rwa" read, write, advanced; "rx" read only, not displayed
    """
    def __init__(self, name, default, min, max, castor,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None ):

        # required
        self.name = name
        self.default = default
        self.min = min
        self.max = max
        self.castor = castor

        # interface sugar
        self.value = value or default
        self.units = units or ""
        self.units_short = units_short or ""
        self.human_name = human_name or name
        self.desc = desc or ""
        self.mode = mode or "rw"

    def isValid( self, candidate ):
        """ Basic Validation, override for special cases """
        return ( (candidate <= self.max) and (candidate >= self.min) )

    def isAdvanced( self ):
        return bool( "a" in self.mode )

    def isShowable( self ):
        return bool( "x" in self.mode )


class UINode( object ):
    def __init__( self, name ):
        self.name = name
        self.trait_order = []
        self.traits = {}
        self.type_info = Nodes.TYPE_NODE
        self.has_advanced = False

    def _survey( self ):
        for trait in self.traits.values():
            if( "a" in trait.mode ):
                self.has_advanced = True
                break

class PiCamUINode( UINode ):
    def __init__( self ):
        super( PiCamUINode, self ).__init__( "PiCamNode" )
        self.type_info = Nodes.TYPE_CAMERA_MC_PI

        # Maybe these should be in a JSON file, rather than hardcoded?
        self.traits = {
            "fps"        : NodeTrait1D( "fps", 60, 0, 60, int,
                                        value=None,
                                        units="Frames per Second",
                                        units_short="fps",
                                        human_name="Frame Rate",
                                        desc="Camera Frame Rate",
                                        mode="rwa" ),

            "strobe"     : NodeTrait1D( "strobe", 20, 0, 70, int,
                                        value=None,
                                        units="Watts",
                                        units_short="W",
                                        human_name="Strobe Power",
                                        desc="Strobe LED Power",
                                        mode="rw" ),

            "shutter"    : NodeTrait1D( "shutter", 8, 2, 250, int,
                                        value=None,
                                        units="100's of uSecs",
                                        units_short="100uS",
                                        human_name="Exposure Time",
                                        desc="Shutter Period for camera",
                                        mode="rw" ),

            "mtu"        : NodeTrait1D( "mtu", 0, 0, 8, int,
                                         value=None,
                                         units="kilobytes above 1500",
                                       units_short="kb",
                                         human_name="Packet Size",
                                         desc="Additional Packet Size (Jumbo Frames)",
                                         mode="rwa" ),

            "iscale"     : NodeTrait1D( "iscale", 1, 1, 128, int,
                                         value=None,
                                         units="Powers of 2",
                                       units_short="/2^X",
                                         human_name="Image decimation",
                                         desc="Scale down image by powers of 2",
                                         mode="rwa" ),

            "idelay"     : NodeTrait1D( "idelay", 15, 3, 255, int,
                                         value=None,
                                         units="Arbitrary Units",
                                       units_short="?",
                                         human_name="Image Delay",
                                         desc="Deley between sending fragmented images",
                                         mode="rwa" ),

            "threshold"  : NodeTrait1D( "threshold", 128, 0, 255, int,
                                         value=None,
                                         units="8-Bit Grey Level",
                                       units_short="b",
                                         human_name="Threshold",
                                         desc="Image Thresholding",
                                         mode="rw" ),

            "numdets"    : NodeTrait1D( "numdets", 13, 0, 80, int,
                                         value=None,
                                         units="10s of Centroids",
                                       units_short="100x",
                                         human_name="Centroids per Packet",
                                         desc="Limit number of Centroids in a packet",
                                         mode="rwa" ),

            "arpdelay"   : NodeTrait1D( "arpdelay", 15, 0, 255, int,
                                         value=None,
                                         units="Arbitrary Units",
                                       units_short="?",
                                         human_name="Gratuitous ARP Delay",
                                         desc="ARP Interval",
                                         mode="rwa" ),

            # 3-axis IMU
            # ToDo: Need to represent bitfields, and probably other types 
            "impactflags": NodeTrait1D( "impactflags", 60, 0, 60, int,#lambda x: '{:08b}'.format(x)
                                         value=None,
                                         units="",
                                        units_short="Flag",
                                         human_name="Impact Warning Flags",
                                         desc="",
                                         mode="rw" ),

            "impactlimit": NodeTrait1D( "impactlimit", 150, 0, 255, int,
                                         value=None,
                                         units="1/10th RMS deviation",
                                         human_name="Impact Threashold",
                                         desc="RMS Impact Deviation Threashold ",
                                         mode="rwa" ),


            # ToDo: These need a NodeTrait3D type
            "impactrefx" : NodeTrait1D( "impactrefx", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Reference X",
                                         desc="Calibrated IMU Pos X",
                                         mode="rwa" ),

            "impactrefy" : NodeTrait1D( "impactrefy", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Reference Y",
                                         desc="Calibrated IMU Pos Y",
                                         mode="rwa" ),

            "impactrefz" : NodeTrait1D( "impactrefz", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Reference Z",
                                         desc="Calibrated IMU Pos Z",
                                         mode="rwa" ),

            "impactvalx" : NodeTrait1D( "impactvalx", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Value X",
                                         desc="Measured IMU Pos X",
                                         mode="ra" ),

            "impactvaly" : NodeTrait1D( "impactvaly", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Value Y",
                                         desc="Measured IMU Pos Y",
                                         mode="ra" ),

            "impactvalz" : NodeTrait1D( "impactvalz", 0, -1023, 1023, int,
                                         value=None,
                                         units="Arbitrary Units",
                                         human_name="Impact Value Z",
                                         desc="Measured IMU Pos Z",
                                         mode="ra" ),
        }
        self.trait_order = [ "fps", "strobe", "shutter", "mtu", "iscale", "idelay",
                             "threshold", "numdets", "arpdelay", "impactflags",
                             "impactlimit", "impactrefx", "impactrefy", "impactrefz",
                             "impactvalx", "impactvaly", "impactvalz" ]

        # No idea how to deal with these ATM
        self.special_traits = {
            # Masking Zones (auto Generated)
            "maskzone01x": NodeTrait1D( "maskzone01x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 01 LEFT",
                                         desc="Mask 01 position Left",
                                         mode="rwx" ),

            "maskzone01y": NodeTrait1D( "maskzone01y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 01 TOP",
                                         desc="Mask 01 position Top",
                                         mode="rwx" ),

            "maskzone01m": NodeTrait1D( "maskzone01m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 01 RIGHT",
                                         desc="Mask 01 position Right",
                                         mode="rwx" ),

            "maskzone01n": NodeTrait1D( "maskzone01n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 01 BOTTOM",
                                         desc="Mask 01 position Bottom",
                                         mode="rwx" ),

            "maskzone02x": NodeTrait1D( "maskzone02x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 02 LEFT",
                                         desc="Mask 02 position Left",
                                         mode="rwx" ),

            "maskzone02y": NodeTrait1D( "maskzone02y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 02 TOP",
                                         desc="Mask 02 position Top",
                                         mode="rwx" ),

            "maskzone02m": NodeTrait1D( "maskzone02m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 02 RIGHT",
                                         desc="Mask 02 position Right",
                                         mode="rwx" ),

            "maskzone02n": NodeTrait1D( "maskzone02n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 02 BOTTOM",
                                         desc="Mask 02 position Bottom",
                                         mode="rwx" ),

            "maskzone03x": NodeTrait1D( "maskzone03x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 03 LEFT",
                                         desc="Mask 03 position Left",
                                         mode="rwx" ),

            "maskzone03y": NodeTrait1D( "maskzone03y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 03 TOP",
                                         desc="Mask 03 position Top",
                                         mode="rwx" ),

            "maskzone03m": NodeTrait1D( "maskzone03m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 03 RIGHT",
                                         desc="Mask 03 position Right",
                                         mode="rwx" ),

            "maskzone03n": NodeTrait1D( "maskzone03n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 03 BOTTOM",
                                         desc="Mask 03 position Bottom",
                                         mode="rwx" ),

            "maskzone04x": NodeTrait1D( "maskzone04x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 04 LEFT",
                                         desc="Mask 04 position Left",
                                         mode="rwx" ),

            "maskzone04y": NodeTrait1D( "maskzone04y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 04 TOP",
                                         desc="Mask 04 position Top",
                                         mode="rwx" ),

            "maskzone04m": NodeTrait1D( "maskzone04m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 04 RIGHT",
                                         desc="Mask 04 position Right",
                                         mode="rwx" ),

            "maskzone04n": NodeTrait1D( "maskzone04n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 04 BOTTOM",
                                         desc="Mask 04 position Bottom",
                                         mode="rwx" ),

            "maskzone05x": NodeTrait1D( "maskzone05x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 05 LEFT",
                                         desc="Mask 05 position Left",
                                         mode="rwx" ),

            "maskzone05y": NodeTrait1D( "maskzone05y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 05 TOP",
                                         desc="Mask 05 position Top",
                                         mode="rwx" ),

            "maskzone05m": NodeTrait1D( "maskzone05m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 05 RIGHT",
                                         desc="Mask 05 position Right",
                                         mode="rwx" ),

            "maskzone05n": NodeTrait1D( "maskzone05n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 05 BOTTOM",
                                         desc="Mask 05 position Bottom",
                                         mode="rwx" ),

            "maskzone06x": NodeTrait1D( "maskzone06x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 06 LEFT",
                                         desc="Mask 06 position Left",
                                         mode="rwx" ),

            "maskzone06y": NodeTrait1D( "maskzone06y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 06 TOP",
                                         desc="Mask 06 position Top",
                                         mode="rwx" ),

            "maskzone06m": NodeTrait1D( "maskzone06m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 06 RIGHT",
                                         desc="Mask 06 position Right",
                                         mode="rwx" ),

            "maskzone06n": NodeTrait1D( "maskzone06n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 06 BOTTOM",
                                         desc="Mask 06 position Bottom",
                                         mode="rwx" ),

            "maskzone07x": NodeTrait1D( "maskzone07x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 07 LEFT",
                                         desc="Mask 07 position Left",
                                         mode="rwx" ),

            "maskzone07y": NodeTrait1D( "maskzone07y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 07 TOP",
                                         desc="Mask 07 position Top",
                                         mode="rwx" ),

            "maskzone07m": NodeTrait1D( "maskzone07m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 07 RIGHT",
                                         desc="Mask 07 position Right",
                                         mode="rwx" ),

            "maskzone07n": NodeTrait1D( "maskzone07n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 07 BOTTOM",
                                         desc="Mask 07 position Bottom",
                                         mode="rwx" ),

            "maskzone08x": NodeTrait1D( "maskzone08x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 08 LEFT",
                                         desc="Mask 08 position Left",
                                         mode="rwx" ),

            "maskzone08y": NodeTrait1D( "maskzone08y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 08 TOP",
                                         desc="Mask 08 position Top",
                                         mode="rwx" ),

            "maskzone08m": NodeTrait1D( "maskzone08m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 08 RIGHT",
                                         desc="Mask 08 position Right",
                                         mode="rwx" ),

            "maskzone08n": NodeTrait1D( "maskzone08n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 08 BOTTOM",
                                         desc="Mask 08 position Bottom",
                                         mode="rwx" ),

            "maskzone09x": NodeTrait1D( "maskzone09x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 09 LEFT",
                                         desc="Mask 09 position Left",
                                         mode="rwx" ),

            "maskzone09y": NodeTrait1D( "maskzone09y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 09 TOP",
                                         desc="Mask 09 position Top",
                                         mode="rwx" ),

            "maskzone09m": NodeTrait1D( "maskzone09m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 09 RIGHT",
                                         desc="Mask 09 position Right",
                                         mode="rwx" ),

            "maskzone09n": NodeTrait1D( "maskzone09n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 09 BOTTOM",
                                         desc="Mask 09 position Bottom",
                                         mode="rwx" ),

            "maskzone10x": NodeTrait1D( "maskzone10x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 10 LEFT",
                                         desc="Mask 10 position Left",
                                         mode="rwx" ),

            "maskzone10y": NodeTrait1D( "maskzone10y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 10 TOP",
                                         desc="Mask 10 position Top",
                                         mode="rwx" ),

            "maskzone10m": NodeTrait1D( "maskzone10m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 10 RIGHT",
                                         desc="Mask 10 position Right",
                                         mode="rwx" ),

            "maskzone10n": NodeTrait1D( "maskzone10n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 10 BOTTOM",
                                         desc="Mask 10 position Bottom",
                                         mode="rwx" ),

            "maskzone11x": NodeTrait1D( "maskzone11x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 11 LEFT",
                                         desc="Mask 11 position Left",
                                         mode="rwx" ),

            "maskzone11y": NodeTrait1D( "maskzone11y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 11 TOP",
                                         desc="Mask 11 position Top",
                                         mode="rwx" ),

            "maskzone11m": NodeTrait1D( "maskzone11m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 11 RIGHT",
                                         desc="Mask 11 position Right",
                                         mode="rwx" ),

            "maskzone11n": NodeTrait1D( "maskzone11n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 11 BOTTOM",
                                         desc="Mask 11 position Bottom",
                                         mode="rwx" ),

            "maskzone12x": NodeTrait1D( "maskzone12x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 12 LEFT",
                                         desc="Mask 12 position Left",
                                         mode="rwx" ),

            "maskzone12y": NodeTrait1D( "maskzone12y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 12 TOP",
                                         desc="Mask 12 position Top",
                                         mode="rwx" ),

            "maskzone12m": NodeTrait1D( "maskzone12m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 12 RIGHT",
                                         desc="Mask 12 position Right",
                                         mode="rwx" ),

            "maskzone12n": NodeTrait1D( "maskzone12n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 12 BOTTOM",
                                         desc="Mask 12 position Bottom",
                                         mode="rwx" ),

            "maskzone13x": NodeTrait1D( "maskzone13x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 13 LEFT",
                                         desc="Mask 13 position Left",
                                         mode="rwx" ),

            "maskzone13y": NodeTrait1D( "maskzone13y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 13 TOP",
                                         desc="Mask 13 position Top",
                                         mode="rwx" ),

            "maskzone13m": NodeTrait1D( "maskzone13m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 13 RIGHT",
                                         desc="Mask 13 position Right",
                                         mode="rwx" ),

            "maskzone13n": NodeTrait1D( "maskzone13n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 13 BOTTOM",
                                         desc="Mask 13 position Bottom",
                                         mode="rwx" ),

            "maskzone14x": NodeTrait1D( "maskzone14x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 14 LEFT",
                                         desc="Mask 14 position Left",
                                         mode="rwx" ),

            "maskzone14y": NodeTrait1D( "maskzone14y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 14 TOP",
                                         desc="Mask 14 position Top",
                                         mode="rwx" ),

            "maskzone14m": NodeTrait1D( "maskzone14m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 14 RIGHT",
                                         desc="Mask 14 position Right",
                                         mode="rwx" ),

            "maskzone14n": NodeTrait1D( "maskzone14n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 14 BOTTOM",
                                         desc="Mask 14 position Bottom",
                                         mode="rwx" ),

            "maskzone15x": NodeTrait1D( "maskzone15x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 15 LEFT",
                                         desc="Mask 15 position Left",
                                         mode="rwx" ),

            "maskzone15y": NodeTrait1D( "maskzone15y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 15 TOP",
                                         desc="Mask 15 position Top",
                                         mode="rwx" ),

            "maskzone15m": NodeTrait1D( "maskzone15m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 15 RIGHT",
                                         desc="Mask 15 position Right",
                                         mode="rwx" ),

            "maskzone15n": NodeTrait1D( "maskzone15n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 15 BOTTOM",
                                         desc="Mask 15 position Bottom",
                                         mode="rwx" ),

            "maskzone16x": NodeTrait1D( "maskzone16x", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 16 LEFT",
                                         desc="Mask 16 position Left",
                                         mode="rwx" ),

            "maskzone16y": NodeTrait1D( "maskzone16y", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 16 TOP",
                                         desc="Mask 16 position Top",
                                         mode="rwx" ),

            "maskzone16m": NodeTrait1D( "maskzone16m", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 16 RIGHT",
                                         desc="Mask 16 position Right",
                                         mode="rwx" ),

            "maskzone16n": NodeTrait1D( "maskzone16n", 0, 0, 4096, int,
                                         value=None,
                                         units="Pixels",
                                         human_name="Mask Zone 16 BOTTOM",
                                         desc="Mask 16 position Bottom",
                                         mode="rwx" ),

        }

        # OK
        self._survey()

NODE_LUT = {
    Nodes.TYPE_CAMERA_MC_PI : PiCamUINode,
}

def uiNodeFactory( node_type ):
    return NODE_LUT[ node_type ]()
