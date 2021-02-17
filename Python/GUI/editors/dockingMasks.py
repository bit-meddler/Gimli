"""
Docking mask region controller.  Currently just visual placeholder.
ToDo: attach to models
ToDo: Emit CnC to selected camera
ToDo: draw and edit Regions in the "viewerCamera"!

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