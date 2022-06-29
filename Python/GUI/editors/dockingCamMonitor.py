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
Docking Camera Activity Monitor.  Just a silly heatmap to show which cameras are getting centroids, or if any are
getting unusually high numbers of centroids.

"""

import logging
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from GUI import ROLE_INTERNAL_ID, ROLE_NUMROIDS, Nodes
from GUI.widgets.knobs import KnobInt

class QDockingCamActivityMon( QtWidgets.QDockWidget ):

    class CamDelegate( QtWidgets.QStyledItemDelegate ):
        """
        Draw a nice looking button with a 'chip' in the middle to act as the 'heatmap'.
        """

        BUT_SIZE  = QtCore.QSize( 48, 48 )
        HIGH_RECT = QtCore.QRect(  1, 1, 46, 46 )
        BUT_RECT  = QtCore.QRect(  3, 3, 41, 41 )
        CHIP      = QtCore.QRect( 14, 7, 18, 18 )

        FONT      = QtGui.QFont(  "Arial", 12 )

        COL_OK    = QtGui.QColor( "green" )
        COL_WARN  = QtGui.QColor( "red" )

        A_HIGH    = 48
        A_SEL     = 48
        A_SEL_FIL = 69

        def __init__( self, palette, parent=None ):
            super( QDockingCamActivityMon.CamDelegate, self ).__init__( parent )

            self.FONT.setWeight( 60 )

            c = palette.color( QtGui.QPalette.Active, QtGui.QPalette.Shadow )

            self.PEN_OUTLINE = QtGui.QPen()
            self.PEN_OUTLINE.setColor( QtGui.QColor( c ) )
            self.PEN_OUTLINE.setWidth( 1 )
            self.PEN_OUTLINE.setStyle( QtCore.Qt.SolidLine )
            self.PEN_OUTLINE.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_OUTLINE.setJoinStyle( QtCore.Qt.RoundJoin )

            self.GRADIENT = QtGui.QLinearGradient( 0, 0, 0, 38 )
            self.GRADIENT.setColorAt( 0.000, QtGui.QColor( c.red(), c.green(), c.blue(), 0 ) )
            self.GRADIENT.setColorAt( 0.666, QtGui.QColor( c.red(), c.green(), c.blue(), 32 ) )
            self.GRADIENT.setColorAt( 1.000, QtGui.QColor( c.red(), c.green(), c.blue(), 64 ) )

            self.PEN_TEXT = QtGui.QPen()
            self.PEN_TEXT.setColor( palette.color( QtGui.QPalette.Active, QtGui.QPalette.Text ) )
            self.PEN_TEXT.setWidthF( 1.5 )
            self.PEN_TEXT.setStyle( QtCore.Qt.SolidLine )
            self.PEN_TEXT.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_TEXT.setJoinStyle( QtCore.Qt.RoundJoin )

            self.CHIP_PATH = QtGui.QPainterPath()
            self.CHIP_PATH.addRoundedRect( self.CHIP, 2, 2 )

            self.OUT_PATH = QtGui.QPainterPath()
            self.OUT_PATH.addRoundedRect( self.BUT_RECT, 2, 2 )

            self.SEL_PATH = QtGui.QPainterPath()
            self.SEL_PATH.addRect( self.HIGH_RECT )

            c = palette.color( QtGui.QPalette.Active, QtGui.QPalette.Highlight )

            self.COL_SEL  = QtGui.QColor( c.red(), c.green(), c.blue(), self.A_SEL  )
            self.COL_HIGH = QtGui.QColor( c.red(), c.green(), c.blue(), self.A_HIGH )

            self.PEN_SEL = QtGui.QPen()
            self.PEN_SEL.setColor( QtGui.QColor( c.red(), c.green(), c.blue(), self.A_SEL_FIL ) )
            self.PEN_SEL.setWidth( 2 )
            self.PEN_SEL.setStyle( QtCore.Qt.SolidLine )


            self.roid_overload_limit = 150  # this needs to be on a Knob

        def sizeHint( self, options, index ):
            return self.BUT_SIZE

        def paint( self, painter, option, index ):

            canvas, state = option.rect, option.state

            sel = bool( state & QtWidgets.QStyle.State_Selected  )
            hov = bool( state & QtWidgets.QStyle.State_MouseOver )

            cam = int( index.data( ROLE_INTERNAL_ID ) )
            num = int( index.data( ROLE_NUMROIDS ) )

            # Go to correct place
            painter.save()
            painter.translate( canvas.left(), canvas.top() )

            # Highlight or hover
            painter.setPen( self.PEN_SEL )
            painter.setBrush( QtCore.Qt.NoBrush )
            if( sel or hov ):
                if( sel ):
                    painter.fillPath( self.SEL_PATH, self.COL_SEL )
                else:
                    painter.fillPath( self.SEL_PATH, self.COL_HIGH )
                painter.drawPath( self.SEL_PATH )

            # draw the icon
            painter.setPen( self.PEN_OUTLINE )
            painter.setBrush( self.GRADIENT )
            painter.drawPath( self.OUT_PATH )
            painter.setBrush( QtCore.Qt.NoBrush )

            # draw the "Activity Chip"
            if( num > 0 ):
                if( num >= self.roid_overload_limit ):
                    painter.fillPath( self.CHIP_PATH, self.COL_WARN )
                else:
                    painter.fillPath( self.CHIP_PATH, self.COL_OK )
            painter.drawPath( self.CHIP_PATH )

            # Draw the lable
            painter.setPen( self.PEN_TEXT )
            painter.drawText( self.BUT_RECT, QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom, str( cam ) )

            # Done
            painter.restore()


    def __init__( self, parent ):
        super( QDockingCamActivityMon, self ).__init__( "CamActivityMon", parent )
        self.setObjectName( "CamMonDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self.scroll_area = QtWidgets.QScrollArea( self )
        self.scroll_area.setWidgetResizable( True )
        hz = self.scroll_area.horizontalScrollBar()
        hz.setEnabled( False )
        self.scroll_area.setHorizontalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )

        self._ctx = QtWidgets.QWidget( self )
        layout = QtWidgets.QVBoxLayout( self )
        self._ctx.setLayout( layout )

        self._delegate = QDockingCamActivityMon.CamDelegate( self.palette() )

        self.view = QtWidgets.QListView()
        self.view.setViewMode( QtWidgets.QListView.IconMode )
        self.view.setResizeMode( QtWidgets.QListView.Adjust )
        self.view.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        self.view.setMinimumWidth( 150 )
        self.view.setItemDelegate( self._delegate )

        self.max_knob = KnobInt( self, 1, 1024, 150, "High Det Warning" )
        self.max_knob.valueChanged.connect( self.setRoidLimit )
        self.max_knob.valueSet.connect( self.setRoidLimit ) # save in global settings ???

        layout.addWidget( self.view )
        layout.addWidget( QtWidgets.QLabel("High Detection count Warning", self ) )
        layout.addLayout( self.max_knob )

        self.scroll_area.setWidget( self._ctx )
        self.setWidget( self.scroll_area )

    def setModels( self, item_model, selection_model ):
        """ Editors attach to the main item and selection model """
        old = self.view.selectionModel()
        self.view.setModel( item_model )
        self.view.setSelectionModel( selection_model )
        del( old )
        # root at correct place
        cams_idx = item_model.genIndex( item_model.groups[ Nodes.TYPE_GROUP_MOCAP ] )
        self.view.setRootIndex( cams_idx )

    def setRoidLimit( self, num_roids ):
        """ slot called when 'max_knob' changes """
        self._delegate.roid_overload_limit = int( num_roids )

    def update( self ):
        """ Might be depricated?? """
        self.view.update()

