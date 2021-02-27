from . import UINode, Nodes, NodeTrait1D

class ViewUINode( UINode ):
    def __init__( self ):
        super( ViewUINode, self ).__init__( "ViewUI" )
        self.type_info = Nodes.TYPE_VIEW

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
        }
        self.trait_order = [ "fps", "strobe", ]

        self._survey()