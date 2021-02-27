""" calExplore.py - UI for exploring camera parameters and camera Calibrations.

"""
from functools import partial
import logging
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets
from queue import SimpleQueue
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

from GUI import QDarkPalette, QBrownPalette, getStdIcon, getPrefDims, SceneModel, Nodes

from GUI.editors.dockingLog        import QDockingLog
from GUI.editors.dockingAttributes import QDockingAttrs
from GUI.editors.dockingOutliner   import QDockingOutliner

from GUI.glViewers.viewerCameras import QGLCameraView
#from GUI.glViewers.viewer3D      import QGLView


class QMain( QtWidgets.QMainWindow ):


    def __init__( self, parent ):
        """
        The Main Application.
        Args:
            parent: the Parent QApplication - but as this *is* the application, do we need to do this?
        """
        super( QMain, self ).__init__()
        self._app = parent # This could be QtWidgets.QApplication()?

        # app config
        self._app.setApplicationName( "Gimli Calibration Explorer" )
        self._app.setOrganizationName( "Gimli" )
        self._app.setOrganizationDomain( "" )

        screen, placement = getPrefDims( self._app )

        # BlackStyle
        self.palette = QDarkPalette()
        #self.palette = QBrownPalette()
        self.palette.apply2Qapp( self._app )

        # Splash Screen & Test Card
        self.test_card = QtGui.QPixmap( os.path.join( RES_PATH, "cardK.png" ) )
        self.splash = QtWidgets.QSplashScreen( self, pixmap=self.test_card )
        self.splash.move( screen.availableGeometry().center() - self.splash.rect().center() )
        self.splash.show()

        # Qt MVC System
        self.splash.showMessage( "Assemble Scene Model" )
        self.scene_model = SceneModel()
        # Register Nodes we expect in this scene
        self.scene_model.registerNode( Nodes.TYPE_CAMERA_MC_PI )
        self.scene_model.registerNode( Nodes.TYPE_VIEW )

        # Shared Selection Model
        self.selection_model = QtCore.QItemSelectionModel( self.scene_model )

        # attach the app to the selection model
        self.selection_model.selectionChanged.connect( self.onSelectionChanged )

        self.splash.showMessage( "Building UI" )
        self._buildUI()

        # Show the Interface
        self.setGeometry( placement )
        self.splash.showMessage( "01 Ready" )
        self.show()
        self.splash.finish( self )


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

    # UI Assembly
    def _buildStatusBar( self ):
        self.status_bar = QtWidgets.QStatusBar()
        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setRange( 0, 100 )

        self.status_lbl = QtWidgets.QLabel( "" )

        self.status_bar.addPermanentWidget( self.status_progress, 0 )
        self.status_bar.addPermanentWidget( self.status_lbl, 0 )

        self.setStatusBar( self.status_bar )


    def _buildUI( self ):
        """
        Assemble the UI Components and attach to Data Model and Selection Model, Register relevant events
        """
        self.setWindowTitle( "Main Window" )

        self.splash.showMessage( "Setting up Dummy Scene" )

        # Add some dumy cams
        for i in range( 10 ):
            cam_node =  Nodes.factory( Nodes.TYPE_CAMERA_MC_PI )
            cam_node.data["ID"] = i
            self.scene_model.addNode( cam_node )

        # Add 3D Views
        for name in ("Ortho Left", "Ortho Right", "Ortho Front", "Ortho Back", "Ortho Top", "Ortho Bottom"):
            view_node = Nodes.factory( Nodes.TYPE_VIEW, name=name )
            self.scene_model.addNode( view_node )

        # Central Widget
        self.splash.showMessage( "Creating The Main Viewport" )
        self.cam_view = QGLCameraView( self )
        self.cam_view.setModels( self.scene_model, self.selection_model )
        self.selection_model.selectionChanged.connect( self.cam_view.onSelectionChanged )
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
        self.atribs.registerNodeType( Nodes.TYPE_VIEW )

        self.atribs.setModels( self.scene_model, self.selection_model )
        self.selection_model.selectionChanged.connect( self.atribs.onSelectionChanged )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, self.atribs )

        # setup status bar
        self._buildStatusBar()


if __name__ == "__main__":

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QtWidgets.QApplication.setAttribute( QtCore.Qt.AA_EnableHighDpiScaling )
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )


