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