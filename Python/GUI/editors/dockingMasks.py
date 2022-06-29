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

"""
Docking mask region controller.  Currently just visual placeholder.
ToDo: attach to models
ToDo: Emit CnC to selected camera
ToDo: draw and edit Regions in the "viewerCamera"!
ToDo: Post (Soft) Masking

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL


class QDockingRegions( QtWidgets.QDockWidget ):

    def __init__( self, parent ):
        super( QDockingRegions, self ).__init__( "MaskRegions", parent )
        self.setObjectName( "RegionDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self._buildUI()


    def _buildUI( self ):
        self.table = QtWidgets.QTableWidget( 16, 4, self )
        self.table.setHorizontalHeaderLabels( ["X","Y","M","N"] )
        self.table.setVerticalHeaderLabels( [ "MaskZone{:0>2}".format( i+1 ) for i in range(16) ])
        self.table.setColumnWidth( 0, 40 )
        self.table.setColumnWidth( 1, 40 )
        self.table.setColumnWidth( 2, 40 )
        self.table.setColumnWidth( 3, 40 )
        self._populate()
        self.setWidget( self.table )

    def _populate( self ):
        for i in range( 16 ):
            for j in range( 4 ):
                self.table.setItem( i, j, QtWidgets.QTableWidgetItem( "0" ) )