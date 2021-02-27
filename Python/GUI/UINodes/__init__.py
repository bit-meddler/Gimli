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
        # Maybe these should be in a JSON file, rather than hardcoded?
        self.traits = {}
        self.trait_order = []

        self.type_info = Nodes.TYPE_NODE
        self.has_advanced = False

    def _survey( self ):
        for trait in self.traits.values():
            if( "a" in trait.mode ):
                self.has_advanced = True
                break


from . import piCamUI, viewUI

NODE_LUT = {
    Nodes.TYPE_CAMERA_MC_PI : piCamUI.PiCamUINode,
    Nodes.TYPE_VIEW         : viewUI.ViewUINode,
}

def uiNodeFactory( node_type ):
    return NODE_LUT[ node_type ]()
