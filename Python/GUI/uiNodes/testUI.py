from . import UINode, Nodes
from GUI.nodeTraits import *

class TestUINode( UINode ):

    def __init__( self ):
        super( TestUINode, self ).__init__( "UI Test" )
        self.type_info = Nodes.TYPE_TESTING

        self.traits = {
            "Bit Box"     : TraitBool( "Boolen Bit Box", False, style=TRAIT_STYLE_EDIT ),
            "Text Box"    : TraitStr( "Text Edit", "Spam & Eggs", style=TRAIT_STYLE_EDIT ),
            "Int Edit"    : TraitInt( "Int Edit", 30, -60, 120, style=TRAIT_STYLE_EDIT ),
            "Float Edit"  : TraitFloat( "Float Edit", 0., 0., 100., style=TRAIT_STYLE_EDIT ),
            "List Box"    : TraitList( "List Box", "29.97", ["23.976", "24", "25", "29.97", "30"],
                                       style=TRAIT_STYLE_EDIT, desc="Framerate" ),
            "Int Knob"    : TraitInt( "Int Knob", 30, 0, 60, style=TRAIT_STYLE_KNOB ),
            "Float Knob"  : TraitFloat( "Float Knob", 0., 0., 1., style=TRAIT_STYLE_KNOB ),

        }
        self.trait_order = list( self.traits.keys() )

        self._survey()