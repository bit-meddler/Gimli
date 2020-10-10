"""
docking Camera Activity Monitor

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from GUI.widgets import QFlowLayout


class QDockingCamActivityMon( QtWidgets.QDockWidget ):

    class QCamButSettings( object ):

        def __init__( self ):
            self.BUT_SIZE = QtCore.QSize( 48, 48 )

            self.HIGH_RECT = QtCore.QRect( 1, 1, 46, 46 ) # sz -1 px
            self.BUT_RECT = QtCore.QRect( 3, 3, 41, 41 ) # sz - 3 px
            self.CHIP = QtCore.QRect( 14, 7, 18, 18 ) # 20x20 centred in BUT_RECT

            self.FONT = QtGui.QFont( "Arial", 12 )
            self.FONT.setWeight( 60 )

            self.PEN_GREY = QtGui.QPen()
            self.PEN_GREY.setColor( QtGui.QColor( 134, 132, 130 ) )
            self.PEN_GREY.setWidth( 1 )
            self.PEN_GREY.setStyle( QtCore.Qt.SolidLine )
            self.PEN_GREY.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_GREY.setJoinStyle( QtCore.Qt.RoundJoin )

            self.GRAD_GRAY = QtGui.QLinearGradient( 0, 0, 0, 38 )
            self.GRAD_GRAY.setColorAt( 0.000, QtGui.QColor( 134, 132, 130,  0 ) )
            self.GRAD_GRAY.setColorAt( 0.666, QtGui.QColor( 134, 132, 130, 32 ) )
            self.GRAD_GRAY.setColorAt( 1.000, QtGui.QColor( 134, 132, 130, 64 ) )

            self.PEN_WHITE = QtGui.QPen()
            self.PEN_WHITE.setColor( QtGui.QColor( "white" ) )
            self.PEN_WHITE.setWidthF( 1.5 )
            self.PEN_WHITE.setStyle( QtCore.Qt.SolidLine )
            self.PEN_WHITE.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_WHITE.setJoinStyle( QtCore.Qt.RoundJoin )

            self.CHIP_PATH = QtGui.QPainterPath()
            self.CHIP_PATH.addRoundedRect( self.CHIP, 2, 2 )

            self.OUT_PATH = QtGui.QPainterPath()
            self.OUT_PATH.addRoundedRect( self.BUT_RECT, 2, 2 )

            self.SEL_PATH = QtGui.QPainterPath()
            self.SEL_PATH.addRect( self.HIGH_RECT )

            self.COL_OK   = QtGui.QColor( "green" )
            self.COL_WARN = QtGui.QColor( "red" )

            self.COL_BG  = QtGui.QColor( "black" )
            self.COL_SEL = QtGui.QColor( "white" )

            self.roid_overload_limit = 150 # this needs to be on a Knob


    class QCamButton( QtWidgets.QWidget ):

        def __init__( self, parent, settings, cam_id ):
            super( QDockingCamActivityMon.QCamButton, self ).__init__( parent )

            self.setSizePolicy( QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed )

            self.cam_id = cam_id
            self.settings = settings
            self.text = str( self.cam_id )
            self.selected = False
            self.roid_count = 0

        def sizeHint( self ):
            return self.settings.BUT_SIZE

        def paintEvent( self, e ):
            painter = QtGui.QPainter( self )

            painter.setPen( self.settings.PEN_GREY )

            painter.setBrush( self.settings.GRAD_GRAY )
            painter.drawPath( self.settings.OUT_PATH )
            painter.setBrush( QtCore.Qt.NoBrush )

            if( self.roid_count > 0 ):
                if (self.roid_count >= self.settings.roid_overload_limit):
                    painter.fillPath( self.settings.CHIP_PATH, self.settings.COL_WARN )
                else:
                    painter.fillPath( self.settings.CHIP_PATH, self.settings.COL_OK )

            painter.drawPath( self.settings.CHIP_PATH )

            painter.setPen( self.settings.PEN_WHITE )
            if (self.text):
                painter.setFont( self.settings.FONT )
                painter.drawText( self.settings.BUT_RECT, QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom, self.text )

            if (self.selected):
                painter.drawPath( self.settings.SEL_PATH )


    def __init__( self, parent ):
        super( QDockingCamActivityMon, self ).__init__( "CamActivityMon", parent )
        self.setObjectName( "CamMonDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea |
                              QtCore.Qt.RightDockWidgetArea )

        self.settings = QDockingCamActivityMon.QCamButSettings()

        self.scroll_area = QtWidgets.QScrollArea( self )
        self.scroll_area.setWidgetResizable( True )
        hz = self.scroll_area.horizontalScrollBar()
        hz.setEnabled( False )
        self.scroll_area.setHorizontalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )

        self.canvas = QtWidgets.QWidget( self.scroll_area )
        self.canvas.setMinimumWidth( 150 )

        self.layout = QFlowLayout( self.canvas )

        # change when we get proper MVC
        self.cam_count = 0
        self.roid_count_list = []
        self.cam_list = []
        self._populate()

        self.scroll_area.setWidget( self.canvas )
        self.setWidget( self.scroll_area )

    def addCam( self, cam_id ):
        button = QDockingCamActivityMon.QCamButton( self.canvas, self.settings, cam_id )
        self.layout.addWidget( button )
        self.roid_count_list.append( 0 )
        self.cam_list.append( button )
        self.cam_count += 1
        return button

    def updateRoidCount( self ):
        for button, num in zip( self.cam_list, self.roid_count_list ):
            button.roid_count = num
            button.update()

    def _populate( self ):
        for i in range( 10 ):
            button = self.addCam( i )
            if (i == 4):
                button.selected = True
