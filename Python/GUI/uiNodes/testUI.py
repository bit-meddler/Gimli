from . import UINode, Nodes
from GUI.nodeTraits import *

class TestUINode( UINode ):

    def __init__( self ):
        super( TestUINode, self ).__init__( "UI Test" )
        self.type_info = Nodes.TYPE_TESTING

        self.traits = {
            "Int Knob"       : TraitInt( "Int Knob", 60, 0, 60, style=TRAIT_STYLE_KNOB ),
            "Float Knob"     : TraitFloat( "Float Knob", 0., 0., 1., style=TRAIT_STYLE_KNOB ),

        }
        self.trait_order = list( self.traits.keys() )

        self._survey()