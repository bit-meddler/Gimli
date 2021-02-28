from . import UINode, Nodes
from GUI.nodeTraits import TraitInt, TraitFloat

class ViewUINode( UINode ):
    def __init__( self ):
        super( ViewUINode, self ).__init__( "ViewUI" )
        self.type_info = Nodes.TYPE_VIEW

        self.traits = {
            "fps"        : TraitInt( "fps", 60, 0, 60,
                                        value=None,
                                        units="Frames per Second",
                                        units_short="fps",
                                        human_name="Frame Rate",
                                        desc="Camera Frame Rate",
                                        mode="rwa" ),

            "boogie"     : TraitFloat( "boogie", 0., 0., 1.,
                                        value=None,
                                        units="Linear",
                                        units_short="",
                                        human_name="Boogy factor",
                                        desc="The amount of Boogy to use, 0-1",
                                        mode="rw" ),
        }
        self.trait_order = [ "fps", "boogie", ]

        self._survey()