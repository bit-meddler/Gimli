""" camControls.py - UI for configuring cameras and monitoring Centroids. Wand detection can be enabled

"""
from functools import partial
import logging
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets
from queue import SimpleQueue
import zmq

import sys, os
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "Gimli", "Python" )
sys.path.append( CODE_PATH )
RES_PATH = os.path.join( _git_root_, "Gimli", "Python", "GUI", "resources" ) # to be replaced with a resource bundle

logging.basicConfig()
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

detailed_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s][%(name)-16s] %(message)s {%(filename)s@%(lineno)s}", "%y%m%d %H:%M:%S" )
terse_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s] %(message)s", "%y%m%d %H:%M:%S" )

import Comms

from GUI import QDarkPalette, QBrownPalette, getStdIcon, SceneModel, Nodes

from GUI.editors.dockingLog        import QDockingLog
from GUI.editors.dockingAttributes import QDockingAttrs
from GUI.editors.dockingCamMonitor import QDockingCamActivityMon
from GUI.editors.dockingMasks      import QDockingRegions
from GUI.editors.dockingOutliner   import QDockingOutliner

from GUI.glViewers.viewerCameras import QGLCameraView
#from GUI.glViewers.viewer3D      import QGLView


class QMain( QtWidgets.QMainWindow ):

    class ArbiterListen( QtCore.QThread ):
        """
        ArbiterListen.  A Threaded listener making used of a ZMQ Poller to receive a "Data Frame" of centroids and emit
        a signal when this happens.  Received "Data Frames" are placed in a Queue which is 'owned' byt the main app.  It
        is the apps responsibility to either deal with frames peacemeal, or flush the Queue and only process one packet
        from any that have collected there.

        """

        found = QtCore.Signal()

        def __init__( self, out_q ):
            """
            Args:
                out_q: (SimpleQueue) This must be a *Threadsafe* Queue which Data Packets are placed on when they are
                                     received
            """
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
            """

            Emits:
                found() Qt Signal that the Listener has received a frame and placed it on the Queue
            Enqueues:
                A Data Frame (tuple)
                    fps (float) FPS we are receiving and emiting at
                    time (int) timestamp of data frame
                    nd_strides (ndarray) (int) Nx1 Array of stride data for the frame
                    nd_data (ndarray) (float) Nx3 Array of Centroid data, [x, y, r]
            """
            # Core Thread
            while( self.running ):
                # wait for packets
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

        def quit( self ):
            """
            Cleanly close the Network resources used by the thread, before terminating.

            """
            self.running = False
            #self.dets_recv.close()
            #self._zctx.term()
            super( QMain.ArbiterListen, self ).quit()


    def __init__( self, parent ):
        """
        The Main Camera Control Application.
        Args:
            parent: the Parent QApplication - but as this *is* the application, do we need to do this?
        """
        super( QMain, self ).__init__()
        self._app = parent # This could be QtWidgets.QApplication()?

        # app config
        self._app.setApplicationName( "Gimli Camera Controls" )
        self._app.setOrganizationName( "Gimli" )
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
        self._actions = {}
        self.frame_observers = []

        # Qt MVC System
        self.scene_model = SceneModel()
        # Register Nodes we expect in this scene
        self.scene_model.registerNode( Nodes.TYPE_CAMERA_MC_PI )

        # Shared Selection Model
        self.selection_model = QtCore.QItemSelectionModel( self.scene_model )

        # attach the app to the selection model
        self.selection_model.selectionChanged.connect( self.onSelectionChanged )

        # Centroid receiving
        self.dets_q = SimpleQueue()

        # Arbiter Comms channels
        # TODO: Test if Arbiter is running, spawn one if needed. mDNS?
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
        """ Get preferred screen dimensions and preferred display screen.
            1  screen: Centre
            2+ screens:
                pick biggest
                    or if both the same size, use system defined primary

            Returns:
                screen info (tuple):
                    big_scr: (QScreen) The biggest or primary screen
                    tgt_rect: (QRect) Centered rect in the big_scr
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
        """
        Slot triggered when the ArbiterListener receives and enqueues data.  Updates the "Scene Model" with new centroid data
        Emits:
            QAbstractItemModel.emitUpdate()

        """
        det_fps, time, strides, dets = self.dets_q.get()
        self.scene_model.frame_count += 1
        self.scene_model.dets_time = time
        self.scene_model.dets_strides = strides
        self.scene_model.dets_dets = dets

        roid_count = [ strides[ i + 1 ] - strides[ i ] for i in range( len( strides ) - 1 ) ]
        self.scene_model.dets_count = roid_count

        self.scene_model.emitUpdate()

        # update watchers
        for obs in self.frame_observers:
            obs.update()

        if( self.scene_model.frame_count % 10 == 0 ):
            log.info( "Got centroids @{:3.2f} fps: {}".format( det_fps, roid_count ) )

    def sendCNC( self, verb, noun, value=None ):
        """
        Send Command & Control messages to the MoCap system via the Arbiter.  Whatever is selected in the shared
        selection model will be considered a target for this CnC change, we currently only send to Pi Cams, but this
        should be extended to sync control devices and other future supported MoCap Cameras.
        Args:
            verb: (str) GET, TRY, or SET a property
            noun: (str) property to be acted on
            value: (str) value to set, if applicable.
        """
        indexes = self.selection_model.selection().indexes()
        tgt_list = [ i.data(role=Nodes.ROLE_INTERNAL_ID) for i in indexes if i.data(role=ROLE_TYPEINFO) == Nodes.TYPE_CAMERA_MC_PI ]
        self.command.send( verb, noun, value, tgt_list )
        log.info( "SENT: {}, {}, {} to {}".format( verb, noun, value, tgt_list ) )

    def logNreport( self, msg, dwel=1200 ):
        """
        Log a message and show it on the status bar.
        Args:
            msg: (str) Message
            dwel: (int) How long to stay on the status bar
        """
        log.info( msg )
        self.status_bar.showMessage( msg, dwel )

    def onSelectionChanged( self, _selected, _deselected ):
        """ DEBUG ONLY
        Slot registered to the shared selection model.
        Presently just logs selection for debugging
        Args:
            _selected: (unused) required to match Signal's prototype
            _deselected: (unused) required to match Signal's prototype
        """
        # provided "selcted/deselected" are only this change. so need to dip into the selection model
        # to understand what's happening
        indexes = self.selection_model.selection().indexes()
        report = "None"
        if( len( indexes ) > 0 ):
            report = ", ".join( [ i.data() for i in indexes ] )
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
        """ NO ACTIOINS USED IN CURRENT EMBODYMENT"""
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
        """ NO ACTIOINS USED IN CURRENT EMBODYMENT"""
        # Make Menu Actions
        menu_bar = self.menuBar()
        fileMenu = menu_bar.addMenu( "&File" )
        fileMenu.addAction( self._actions[ "newAction" ] )
        fileMenu.addSeparator()
        fileMenu.addAction( self._actions[ "exitAction" ] )

        helpMenu = menu_bar.addMenu( "&Help" )
        helpMenu.addAction( self._actions[ "aboutAction" ] )

    def _buildToolbar( self ):
        """ NO ACTIOINS USED IN CURRENT EMBODYMENT"""
        mainToolBar = self.addToolBar( "Main" )
        mainToolBar.setMovable( False )
        mainToolBar.addAction( self._actions[ "newAction" ] )
        mainToolBar.addSeparator()

    def _buildUI( self ):
        """
        Assemble the UI Components and attach to Data Model and Selection Model, Register relevant events
        """
        self.setWindowTitle( "Main Window" )

        self.splash.showMessage( "Setting up Actions" )
        self._buildActions()

        self.splash.showMessage( "Building Menu & Tool bars" )
        self._buildMenuBar()
        self._buildToolbar()

        # Add some dumy cams
        for i in range( 10 ):
            cam_node =  Nodes.factory( Nodes.TYPE_CAMERA_MC_PI )
            cam_node.data["ID"] = i
            self.scene_model.addNode( cam_node )
        # Prime with dummy data
        dummy_frame = ( 1., 0, np.zeros( (11,) ), np.array( [ ] ).reshape( 0, 3 ) )
        self.dets_q.put( dummy_frame )
        self.getNewFrame()

        # Central Widget
        self.splash.showMessage( "Creating The Main Viewport" )
        self.cam_view = QGLCameraView( self )
        self.cam_view.setModels( self.scene_model, self.selection_model )
        self.selection_model.selectionChanged.connect( self.cam_view.onSelectionChanged )
        self.frame_observers.append( self.cam_view )
        self.setCentralWidget( self.cam_view )

        # Add dockables
        self.splash.showMessage( "Creating Dockable Editors" )
        self.splash.showMessage( "Editor: Log" )
        logDockWidget = QDockingLog( self )
        self.addDockWidget( QtCore.Qt.BottomDockWidgetArea, logDockWidget )

        self.splash.showMessage( "Editor: Outliner" )
        self.outliner = QDockingOutliner( self )
        self.outliner.setModels( self.scene_model, self.selection_model )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, self.outliner )

        # setup the attribute editor = TODO: This better
        self.splash.showMessage( "Editor: Attributes" )
        self.atribs = QDockingAttrs( self )
        self.atribs.registerNodeType( Nodes.TYPE_CAMERA_MC_PI )
        self.atribs.setModels( self.scene_model, self.selection_model )
        self.selection_model.selectionChanged.connect( self.atribs.onSelectionChanged )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, self.atribs )

        # Region tool
        self.splash.showMessage( "Editor: Masking" )
        regions = QDockingRegions( self )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, regions )

        # activity monitor
        self.splash.showMessage( "Editor: Cameras" )
        self.cam_mon = QDockingCamActivityMon( self )
        self.cam_mon.setModels( self.scene_model, self.selection_model )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.cam_mon )

        # setup status bar
        self._buildStatusBar()

        # Handle windowClosing and stop threads / close sockets etc
        # Quit the ArbiterListen thread
        self._app.aboutToQuit.connect( self.dets_listen.quit )


if __name__ == "__main__":

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )


