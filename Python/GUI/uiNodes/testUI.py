# 
# Copyright (C) 2016~2022 The Gimli Project
# This file is part of Gimli <https://github.com/bit-meddler/Gimli>.
#
# Gimli is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Gimli is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gimli.  If not, see <http://www.gnu.org/licenses/>.
#

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

