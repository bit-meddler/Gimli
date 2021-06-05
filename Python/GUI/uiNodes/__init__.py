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

""" Attributes of Core.Nodes that are presented to the UI.

    These are separated in order to keep the Core.Nodes clean when operating in
    a headless mode.

    These are typically non-animating, and are presented for the user to noodle with
    to get a pretty looking result.
"""

from Core import Nodes


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


from . import piCamUI, viewUI, testUI

NODE_LUT = {
    Nodes.TYPE_ROOT         : None,
    Nodes.TYPE_CAMERA_MC_PI : piCamUI.PiCamUINode,
    Nodes.TYPE_VIEW         : viewUI.ViewUINode,
    Nodes.TYPE_TESTING      : testUI.TestUINode,
}

def uiNodeFactory( node_type ):
    print( ">>", node_type )
    return NODE_LUT[ node_type ]

