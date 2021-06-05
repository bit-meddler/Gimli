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

"""
Docking Outliner.
This will need more functionality possibly?  Search for nodes?  Filter nodes?  Restrict depth?

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from GUI import getStdIcon

class QDockingOutliner( QtWidgets.QDockWidget ):

    def __init__( self, parent ):
        super( QDockingOutliner, self ).__init__( "Outliner", parent )
        self.setObjectName( "OutlineDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self._buildUI()

    def _expandChildren( self, item ):
        """Todo: make this work with the MVC model"""
        """for i in range( item.childCount() ):
            self._expandChildren( item.child( i ) )
        self.tree.expandItem( item )"""
        return None

    def _buildUI( self ):
        self.tree = QtWidgets.QTreeView()
        self.tree.setHeaderHidden( True )
        self.tree.setSelectionBehavior( QtWidgets.QAbstractItemView.SelectRows )
        self.tree.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )

        self.setWidget( self.tree )

    def setModels( self, item_model, selection_model ):
        old = self.tree.selectionModel()
        self.tree.setModel( item_model )
        self.tree.setSelectionModel( selection_model )
        del( old )