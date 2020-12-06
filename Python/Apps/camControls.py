""" camControls.py - UI for configuring cameras and monitoring Centroids.

"""
from functools import partial
import logging
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
from queue import SimpleQueue
from OpenGL import GL, GLU, GLUT 
import zmq

import sys, os
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
sys.path.append( CODE_PATH )
RES_PATH = os.path.join( _git_root_, "midget", "Python", "GUI", "resources" ) # to be replaced with a resource bundle

logging.basicConfig()
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

detailed_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s][%(name)-16s] %(message)s {%(filename)s@%(lineno)s}", "%y%m%d %H:%M:%S" )
terse_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s] %(message)s", "%y%m%d %H:%M:%S" )

import Comms

from GUI import QDarkPalette, QBrownPalette, getStdIcon, Camera, Mesh

from GUI.editors.dockingLog        import QDockingLog
from GUI.editors.dockingAttributes import QDockingAttrs
from GUI.editors.dockingCamMonitor import QDockingCamActivityMon
from GUI.editors.dockingMasks      import QDockingRegions
from GUI.editors.dockingOutliner   import QDockingOutliner

from GUI.glViewers.viewerCameras import QGLCameraView
#from GUI.glViewers.viewer3D      import QGLView


class QMain( QtWidgets.QMainWindow ):

    class ArbiterListen( QtCore.QThread ):

        found = QtCore.Signal()

        def __init__( self, out_q ):
            # Thread setup
            super( QMain.ArbiterListen, self ).__init__()

            # recv monitor
            self._frame_counter = QtCore.QElapsedTimer()
            self._frame_counter.restart()
            self.fps = 1

            # setup ZMQ
            self._zctx = zmq.Context()

            self.dets_recv = self._zctx.socket( zmq.SUB )
            self.dets_recv.subscribe( Comms.ABT_TOPIC_ROIDS )
            self.dets_recv.connect( "tcp://localhost:{}".format( Comms.ABT_PORT_DATA ) )

            self.poller = zmq.Poller()
            self.poller.register( self.dets_recv, zmq.POLLIN )

            # output Queue
            self._q = out_q

            # Thread Control
            self.running = True

        def run( self ):
            # Core Thread
            while( self.running ):
                # look for packets
                coms = dict( self.poller.poll( 0 ) )
                if( coms.get( self.dets_recv ) == zmq.POLLIN ):
                    topic, _, time, strides, data = self.dets_recv.recv_multipart()
                    # pass to the callbacks
                    nd_strides = np.frombuffer( strides, dtype=np.int32 )
                    nd_data = np.frombuffer( data, dtype=np.float32 ).reshape( -1, 3 )
                    self._q.put( (self.fps, time, nd_strides, nd_data) )
                    self.found.emit()
                    fps = 1000. / (float( self._frame_counter.restart() ) + 1e-6)
                    if (fps > 150. or fps < 0.1):
                        fps = self.fps
                    self.fps = fps

            # while
            self.dets_recv.close()
            self._zctx.term()

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent

        # app config
        self._app.setApplicationName( "Testing Midget UI" )
        self._app.setOrganizationName( "Midget Software" )
        self._app.setOrganizationDomain( "" )

        screen, placement = self._getPrefDims()

        # BlackStyle
        self.palette = QDarkPalette()
        #self.palette = QBrownPalette()
        self.palette.apply2Qapp( self._app )

        # Splash Screen & Test Card
        self.test_card = QtGui.QPixmap( os.path.join( RES_PATH, "cardK.png" ) )
        self.splash = QtWidgets.QSplashScreen( self, pixmap=self.test_card )
        self.splash.move( screen.availableGeometry().center() - self.splash.rect().center() )
        self.splash.show()

        # Some UI stuff
        self.selection_que = [ ]
        self.selection_observers = [ ]
        self._actions = { }

        # Centroid receiving
        self.dets_q = SimpleQueue()
        self.dets_time = None
        self.dets_strides = [ ]
        self.dets_dets = [ ]

        # Arbiter Comms channels
        # TODO: Test if Arbiter is running, spawn one if needed
        self.splash.showMessage( "Starting C&C" )
        self.command = Comms.ArbiterControl()
        self.splash.showMessage( "Starting Listener" )
        self.dets_listen = QMain.ArbiterListen( self.dets_q )
        self.dets_listen.found.connect( self.getNewFrame )

        self.packet_count = 0

        self.splash.showMessage( "Building UI" )
        self._buildUI()

        # Show the Interface
        self.setGeometry( placement )
        self.splash.showMessage( "01 Ready" )
        self.show()
        self.splash.finish( self )

        # start the det recever
        self.logNreport( "Started Centroid receiver", 5000 )
        self.dets_listen.start()

    def _getPrefDims( self ):
        """ Get prefered screen dimentions and prefered screen.
            1 screen Centre
            2 screens:
                pick biggest
                or if both the same size, use system defined primary
        """
        # Find Physicaly biggest Screen
        big_scr = self._app.primaryScreen()
        big_dim = self._app.primaryScreen().physicalSize().width()
        screens = self._app.screens()
        for screen in screens:
            width = screen.physicalSize().width()
            if (width > big_dim):
                big_scr = screen
                big_dim = width

        # set window to fit nicely inside it
        desk_w = big_scr.availableGeometry().width()
        desk_h = big_scr.availableGeometry().height()
        width = desk_w * 0.75
        height = desk_h * 0.75

        # place in the screen's available canvas
        x = ((desk_w - width) / 2) + big_scr.availableGeometry().left()
        y = ((desk_h - height) / 2) + big_scr.availableGeometry().top()

        tgt_rect = QtCore.QRect( x, y, width, height )

        return (big_scr, tgt_rect)

    def getNewFrame( self ):
        det_fps, time, strides, dets = self.dets_q.get()
        self.dets_time = time
        self.dets_strides = strides
        self.dets_dets = dets
        self.packet_count += 1
        num_cams = len( strides ) - 1
        roid_count = [ 0 for _ in range( num_cams ) ]
        for i in range( num_cams ):
            roid_count[ i ] = strides[ i + 1 ] - strides[ i ]
        self.cam_mon.roid_count_list = roid_count

        # update watchers
        self.cam_mon.updateRoidCount()
        if (self.packet_count % 10 == 0):
            log.info( "Got centroids @{:3.2f} fps: {}".format( det_fps, roid_count ) )
        self.cam_view.acceptNewData( self.dets_dets, strides, None )

    def sendCNC( self, verb, noun, value=None ):
        tgt_list = list( map( lambda x: x.id, self.selection_que ) )
        self.command.send( verb, noun, value, tgt_list )
        log.info( "SENT: {}, {}, {} to {}".format( verb, noun, value, tgt_list ) )

    def logNreport( self, msg, dwel=1200 ):
        log.info( msg )
        self.status_bar.showMessage( msg, dwel )

    def updateSelection( self ):
        # tell oservers it's changed
        for obs in self.selection_observers:
            obs.selectionChanged( self.selection_que )

        report = "None"
        if (len( self.selection_que ) > 0):
            report = "{}: {}".format( type( self.selection_que[ 0 ] ),
                                      ", ".join( map( lambda x: str( x.id ), self.selection_que ) ) )

        log.info( "Selected: {}".format( report ) )

    # Action CBs
    def _newFileCB( self ):
        self.textEdit.setText( "" )

    def _exitFileCB( self ):
        self.close()

    def _aboutHelpCB( self ):
        QtWidgets.QMessageBox.about( self, "About the software",
                                     "I was born the son of a poor Filipino merchant. "
                                     "I remember I would sit on the stoop of my tenement brownstone "
                                     "on the lower East Side. I was... I was... I was... Crying!"
                                     )

    # UI Assembly
    def _buildStatusBar( self ):
        self.status_bar = QtWidgets.QStatusBar()
        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setRange( 0, 100 )

        self.status_lbl = QtWidgets.QLabel( "" )

        self.status_bar.addPermanentWidget( self.status_progress, 0 )
        self.status_bar.addPermanentWidget( self.status_lbl, 0 )

        self.setStatusBar( self.status_bar )

    def _buildActions( self ):
        self._actions[ "newAction" ] = QtWidgets.QAction( QtGui.QIcon( "new.png" ), '&New', self )
        self._actions[ "newAction" ].setShortcut( QtGui.QKeySequence.New )
        self._actions[ "newAction" ].setStatusTip( "Create a New File" )
        self._actions[ "newAction" ].triggered.connect( self._newFileCB )

        self._actions[ "exitAction" ] = QtWidgets.QAction( QtGui.QIcon( 'exit.png' ), 'E&xit', self )
        self._actions[ "exitAction" ].setShortcut( "Ctrl+Q" )
        self._actions[ "exitAction" ].setStatusTip( "Exit the Application" )
        self._actions[ "exitAction" ].triggered.connect( self._exitFileCB )

        self._actions[ "aboutAction" ] = QtWidgets.QAction( QtGui.QIcon( 'about.png' ), 'A&bout', self )
        self._actions[ "aboutAction" ].setStatusTip( "Displays info about text editor" )
        self._actions[ "aboutAction" ].triggered.connect( self._aboutHelpCB )

    def _buildMenuBar( self ):
        # Make Menu Actions
        menu_bar = self.menuBar()
        fileMenu = menu_bar.addMenu( "&File" )
        fileMenu.addAction( self._actions[ "newAction" ] )
        fileMenu.addSeparator()
        fileMenu.addAction( self._actions[ "exitAction" ] )

        helpMenu = menu_bar.addMenu( "&Help" )
        helpMenu.addAction( self._actions[ "aboutAction" ] )

    def _buildToolbar( self ):
        mainToolBar = self.addToolBar( "Main" )
        mainToolBar.setMovable( False )
        mainToolBar.addAction( self._actions[ "newAction" ] )
        mainToolBar.addSeparator()

    def _buildUI( self ):
        self.setWindowTitle( "Main Window" )

        self.splash.showMessage( "Setting up Actions" )
        self._buildActions()

        self.splash.showMessage( "Building Menu & Tool bars" )
        self._buildMenuBar()
        self._buildToolbar()

        # Central Widget
        #self.cam_view = QGLView()
        self.cam_view = QGLCameraView( self )
        self.setCentralWidget( self.cam_view )
        # DANGER another dumb hack
        self.cam_view._qgl_pane.cam_list = [ x for x in range(10) ]
        self.cam_view._camlistChanged()

        # Add docables
        self.splash.showMessage( "Creating Dockable Editors" )
        self.splash.showMessage( "Editor: Log" )
        logDockWidget = QDockingLog( self )
        self.addDockWidget( QtCore.Qt.BottomDockWidgetArea, logDockWidget )

        self.splash.showMessage( "Editor: Outliner" )
        outliner = QDockingOutliner( self )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, outliner )

        # setup the attribute editor = TODO: This better
        self.splash.showMessage( "Editor: Attributes" )
        cam = Camera( "anon", -1 )
        mesh = Mesh()
        atribs = QDockingAttrs( self )
        self.selection_observers.append( atribs )
        atribs.addSelectable( cam )
        atribs.addSelectable( mesh )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, atribs )

        # Region tool
        self.splash.showMessage( "Editor: Masking" )
        regions = QDockingRegions( self )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, regions )

        # activity monitor
        self.splash.showMessage( "Editor: Cameras" )
        self.cam_mon = QDockingCamActivityMon( self )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.cam_mon )

        # setup status bar
        self._buildStatusBar()

        # TODO: Handle windowClosing and stop threads / close sockets!


if __name__ == "__main__":

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )


