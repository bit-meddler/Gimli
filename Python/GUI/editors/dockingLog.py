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
docking Logger

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL


class QDockingLog( QtWidgets.QDockWidget ):

    class QPlainTextEditLogger( logging.Handler ):

        def __init__( self, parent ):
            super( QDockingLog.QPlainTextEditLogger, self ).__init__()
            self.qpte = QtWidgets.QPlainTextEdit( parent )
            self.qpte.setReadOnly( True )
            terse_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s] %(message)s", "%y%m%d %H:%M:%S" )
            self.setFormatter( terse_log )

        def emit( self, record ):
            msg = self.format( record )
            self.qpte.appendPlainText( msg )

    def __init__( self, parent ):
        super( QDockingLog, self ).__init__( "Logging", parent )
        self.setObjectName( "LogDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea |
                              QtCore.Qt.RightDockWidgetArea |
                              QtCore.Qt.BottomDockWidgetArea |
                              QtCore.Qt.TopDockWidgetArea )
        self.log_widget = self.QPlainTextEditLogger( self )
        self.setWidget( self.log_widget.qpte )
        logging.getLogger().addHandler( self.log_widget )

