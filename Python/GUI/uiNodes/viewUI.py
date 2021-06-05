# 
# Copyright (C) 2016~2021 The Gimli Project
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
from GUI.nodeTraits import TraitInt, TraitFloat, TRAIT_STYLE_KNOB, TRAIT_STYLE_DIAL, TRAIT_STYLE_EDIT

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
                                        mode="rwa",
                                        style=TRAIT_STYLE_KNOB ),

            "boogie"     : TraitFloat( "boogie", 0., 0., 1.,
                                        value=None,
                                        units="Linear",
                                        units_short="",
                                        human_name="Boogy factor",
                                        desc="The amount of Boogy to use, 0-1",
                                        mode="rw",
                                        style=TRAIT_STYLE_KNOB ),
        }
        self.trait_order = [ "fps", "boogie", ]

        self._survey()

