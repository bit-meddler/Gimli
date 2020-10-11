"""
    Experiment to move a QSlider as if it's a playhead of a timeline
"""
from PySide2 import QtCore, QtGui, QtWidgets

import sys, os
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
sys.path.append( CODE_PATH )
RES_PATH = os.path.join( _git_root_, "midget", "Python", "GUI", "resources" ) # to be replaced with a resource bundle

from GUI import QDarkPalette, getStdIcon


class Timeline( QtWidgets.QWidget ):

    frameChangePlay = QtCore.Signal( int ) # Timeline is playing
    frameChangeDrag = QtCore.Signal( int ) # Timeline was dragged
    requestRedraw   = QtCore.Signal()      # the scene needs to be updated

    def __init__( self, parent=None ):
        super( Timeline, self ).__init__( parent )

        self.is_playing = False
        self._frame = 0 # current frame
        self.start = 0
        self.end = 100
        self.fps = 60

        # Timing
        self._period = int( 1000 / self.fps ) # could toggle whole and fraction rates?
        self._timer = QtCore.QTimer( self )
        self._timer.timeout.connect( self.doNextFrame )

        # UI
        self._buildUI()

    def doNextFrame( self ):
        frame = self._frame + 1
        if( frame >= self.end ):
            frame = self.start
        self.timeslider.setValue( frame )

    def broadcast( self, frame_no ):
        self._frame = frame_no
        if( self.is_playing ):
            self.frameChangePlay.emit( frame_no )
        else:
            self.frameChangeDrag.emit( frame_no )
        self.requestRedraw.emit()

    def doPlay( self ):
        self.is_playing = True
        self._timer.start( self._period )

    def doStop( self ):
        self.is_playing = False
        self._timer.stop()

    def _buildUI( self ):
        layout = QtWidgets.QHBoxLayout( self )

        self.startSB = QtWidgets.QSpinBox( self )
        self.startSB.setValue( self.start )
        self.startSB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        layout.addWidget( self.startSB )

        self.timeslider = QtWidgets.QSlider( self )
        self.timeslider.setOrientation( QtCore.Qt.Horizontal )
        layout.addWidget( self.timeslider )

        self.endSB = QtWidgets.QSpinBox( self )
        self.endSB.setValue( self.end )
        self.endSB.setButtonSymbols( QtWidgets.QAbstractSpinBox.NoButtons )
        layout.addWidget( self.endSB )

        self.playBut = QtWidgets.QPushButton( getStdIcon(QtWidgets.QStyle.SP_MediaPlay), "", parent=self )
        layout.addWidget( self.playBut )

        self.stopBut = QtWidgets.QPushButton( getStdIcon(QtWidgets.QStyle.SP_MediaStop), "", parent=self )
        layout.addWidget( self.stopBut )

        self.fpsSB = QtWidgets.QSpinBox( self )
        self.fpsSB.setValue( self.fps )
        self.fpsSB.setButtonSymbols( QtWidgets.QAbstractSpinBox.NoButtons )
        layout.addWidget( self.fpsSB )

        self.setLayout( layout )

        # Signals
        self.playBut.clicked.connect( self.doPlay )
        self.stopBut.clicked.connect( self.doStop )

        # Logic
        self.timeslider.valueChanged.connect( self.broadcast )


class QMain( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        self.palette = QDarkPalette()
        self.palette.apply2Qapp( self._app )
        self.time_line = Timeline( self )
        self.setCentralWidget( self.time_line )
        self.show()
        self.setGeometry( 150, 150, 800, 100 )

if __name__ == "__main__":

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )

