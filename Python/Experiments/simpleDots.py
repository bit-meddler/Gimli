""" Non-OpenGL Viewer to experiment with dots
    - Display and highlight a Wand correctly (to test Wand finding)
    - Display and scrub dets files to see some MoCap
    - Allow selecting of Dets to manually label
    - Draw Dots with label colour, mouseover for x,y,r hint
    - Experiment with Tracking and Predicting Dets
    - Draw "Trails" of a Label
    - ???

    Not intended for 'prime time', the main UI should be OpenGL for performance
"""
from copy import deepcopy
import pickle

from PySide2 import QtWidgets, QtGui, QtCore
import numpy as np
np.set_printoptions( suppress=True, precision=3 )


# Mouse
RMB = QtCore.Qt.RightButton
LMB = QtCore.Qt.LeftButton
MMB = QtCore.Qt.MiddleButton

# Keyboard
MOD_ALT   = QtCore.Qt.AltModifier 
MOD_SHIFT = QtCore.Qt.ShiftModifier


class Viewer( QtWidgets.QGraphicsView ):

    # Signals
    sceneClicked = QtCore.Signal( QtCore.QPointF )

    # Consts
    DEFAULT_ZOOM = 1.05 #(5%)
    DEFAULT_BG = QtCore.Qt.black

    def __init__( self, parent, scene=None ):
        # manage my own Scene
        self.scene = scene or QtWidgets.QGraphicsScene( parent )

        super( Viewer, self ).__init__( self.scene )
        self._parent = parent

        self.scene.setBackgroundBrush( self.DEFAULT_BG )

        # Navigation
        self._zoom = 1.0
        self._pan_mode  = False
        self._panning   = False
        self._pan_start = None
        self.setTransformationAnchor( self.AnchorUnderMouse )
        self.setResizeAnchor( self.AnchorUnderMouse )
        self.setVerticalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )
        self.setHorizontalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )

        self.setFrameStyle( 0 )

    # overloads
    def wheelEvent( self, event ):

        oldPos = self.mapToScene( event.pos() )

        wheel_delta = event.angleDelta().y()
        wheel_delta /= 100.

        if( wheel_delta > 0.0 ): # Zoomed in
            self._zoom *= self.DEFAULT_ZOOM

        elif( wheel_delta < 0.0 ): # zoom out
            self._zoom /= self.DEFAULT_ZOOM

        self._applyScale()

        newPos = self.mapToScene( event.pos() )
        # Move scene to old position
        delta = newPos - oldPos
        self.translate( delta.x(), delta.y() )

        super( Viewer, self ).wheelEvent( event )

    def mousePressEvent( self, event ):

        pressed_left = event.button() == LMB
        pressed_right = event.button() == RMB
        pressed_mid = event.button() == MMB

        if pressed_left :
            if( self._pan_mode ):
                # Panning
                self._panning = True
                self._pan_start = event.pos()
                self.setDragMode( self.ScrollHandDrag )
            else:
                self.sceneClicked.emit( self.mapToScene( event.pos()) )

        elif pressed_right:

            pass

        elif pressed_mid:
            pass

        super( Viewer, self).mousePressEvent( event )

    def mouseReleaseEvent( self, event ):
        pressed_right = event.button() == RMB
        pressed_left = event.button() == LMB
        pressed_mid = event.button() == MMB

        if( self._panning and pressed_left ):
            self._panning = False
            self.setDragMode( self.NoDrag )

        elif pressed_right:

            pass
        elif pressed_mid:
            pass

        super( Viewer, self ).mouseReleaseEvent( event )

    def mouseMoveEvent( self, event ):
        super( Viewer, self ).mouseMoveEvent( event )

    def keyPressEvent( self, event ):
        key = event.key()
        if( key == QtCore.Qt.Key_Alt ):
            self._pan_mode = True
            self.setCursor( QtCore.Qt.OpenHandCursor )

        elif( key == QtCore.Qt.Key_F ):
            self._fit2Scene()

        super( Viewer, self ).keyPressEvent( event )

    def keyReleaseEvent( self, event ):
        key = event.key()
        if( key == QtCore.Qt.Key_Alt ):
            self.setCursor( QtCore.Qt.ArrowCursor )
            self._pan_mode = False

        super( Viewer, self ).keyReleaseEvent( event )

    # internals
    def _resetZoom( self ):
        self._zoom = 1.0
        self._applyScale()

    def _applyScale( self ):
        new_mat = QtGui.QTransform().scale( self._zoom, self._zoom )
        self.setTransform( new_mat )

    def _fit2Scene( self ):
        self._resetZoom()

class Player( QtWidgets.QMainWindow ):
    # Consts
    POINT_Z = 10
    PRIOR_Z = 5

    POINT_COL = QtCore.Qt.white
    PRIOR_COL = QtCore.Qt.lightGray
    TRAIL_COL = QtCore.Qt.darkBlue
    GRID_COL  = QtCore.Qt.darkGray

    DEFAULT_PATH = r"C:\code\Gimli\ExampleData"

    def __init__(self, parent=None):
        super( Player, self ).__init__( parent )
        self.setWindowTitle( "Tracking test Harness" )

        # Points
        self._points = []
        self._priors = []
        self._deltas = []
        self._ofsets = [] # hasher offsets the new points, visualize thsi

        self._point_gfx = {}
        self._proir_gfx = {}
        self._offs_gfx  = {}
        self._point_itm = {}

        # Tracks
        self._track_len = 12
        self._tracks = {}
        self._track_gfx = {}

        # The playing field
        self.dims = [ 512, 512 ]
        self._grid = QtWidgets.QGraphicsPathItem()
        self._grid_cells = 16

        # The data
        self.frames = []
        self.cameras = []
        self.camera_current = -1
        self.frame_current  = -1

        # Build UI
        self._buildUI()

        # timer for auto movement
        self._playTimer = QtCore.QTimer( self )
        self._playTimer.setTimerType( QtCore.Qt.PreciseTimer )
        self._playTimer.timeout.connect( self.doAuto )
        self._period = 250
        self._playing = False

    def addPoint( self, p_pos, force=False ):
        if( not self.but_point_add.isChecked() and not force ):
            return

        p_id = len( self._points )
        self._points.append( [p_pos.x(), p_pos.y()] )
        point_idx = len( self._points ) - 1

        # update table
        self.tab_pts.setRowCount( len( self._points ) )
        pi_pos = QtWidgets.QTableWidgetItem( "<{:.2f}, {:.2f}>".format( p_pos.x(), p_pos.y() ) )
        pi_id  = QtWidgets.QTableWidgetItem( "{}".format( p_id ) )
        pi_lab = QtWidgets.QTableWidgetItem( "" )
        pi_pos.setData( QtCore.Qt.UserRole, p_id )
        self.tab_pts.setItem( point_idx, 0, pi_pos )
        self.tab_pts.setItem( point_idx, 1, pi_id )
        self.tab_pts.setItem( point_idx, 2, pi_lab )

        # add point
        gfx = QtWidgets.QGraphicsEllipseItem( -2, -2, 4, 4 )
        gfx.setPen( QtGui.QPen( self.POINT_COL, 2, QtCore.Qt.SolidLine ) )
        gfx.setToolTip( "{}".format( p_id ) )
        self._point_gfx[ p_id ] = gfx
        gfx.setPos( p_pos )
        gfx.setZValue( self.POINT_Z )
        self._canvas.scene.addItem( gfx )
        if( p_id == -1 ):
            r = int( np.sqrt( self._hashpipe.threshold ) )
            gfx2 = QtWidgets.QGraphicsEllipseItem( (-r/2), (-r/2), r, r, parent=gfx )
            gfx2.setPen( QtGui.QPen( QtCore.Qt.yellow, 1, QtCore.Qt.SolidLine ) )
            #gfx2.setPos( 0, 0 )
            gfx2.setZValue( self.POINT_Z )

        # add a prior
        gfx = QtWidgets.QGraphicsEllipseItem( -2, -2, 4, 4 )
        gfx.setPen( QtGui.QPen( self.PRIOR_COL, 2, QtCore.Qt.SolidLine ) )
        gfx.setToolTip( "Prior {}".format( p_id ) )
        self._proir_gfx[ p_id ] = gfx
        gfx.setPos( p_pos )
        gfx.setZValue( self.PRIOR_Z )
        self._canvas.scene.addItem( gfx )

        # set this point's delta
        self._deltas.append( np.random.uniform( -15.0, 15.0, size=2 ).tolist() )

        # set up the tracks
        self._tracks[ p_id ] = [ p_pos for _ in range( self._track_len ) ]
        path = QtGui.QPainterPath()
        path.moveTo( p_pos )
        path.lineTo( p_pos  )

        gfx = QtWidgets.QGraphicsPathItem()
        gfx.setPath( path )
        gfx.setPen( QtGui.QPen( self.TRAIL_COL, 2, QtCore.Qt.DotLine ) )
        gfx.setZValue( self.PRIOR_Z )
        gfx.setVisible( bool( self.chk_tail.isChecked() ) )
        self._canvas.scene.addItem( gfx )
        self._track_gfx[ p_id ] = gfx

    def doAuto( self ):
        if( bool( self.but_auto.isChecked() ) ):
            if( not self._playing ):
                self._playTimer.start( self._period )
                self._playing = True

            self.movePoints()

        else:
            self._playTimer.stop()
            self._playing = False

    def movePoints( self ):
        # backup to the priors list
        self._priors = deepcopy( self._points )


        for i, (pos, delta) in enumerate( zip( self._points, self._deltas ) ):
            noise = np.random.uniform( -4.0, 4.0, size=2 ).tolist()
            pos[0], pos[1] = pos[0] + delta[0] + noise[0], pos[1] + delta[1] + noise[1]

        self.updateGfx()

        # update the track of the assigned ID (may be wrong
        for i, id in enumerate( range( len(self._points) ) ): # should be a label mapping
            if( id < 0):
                continue

            pos = self._points[ i ]
            _ = self._tracks[ id ].pop( self._track_len - 1 )
            self._tracks[ id ].insert( 0, QtCore.QPointF( pos[ 0 ], pos[ 1 ] ) )

    def updateGfx( self ):
        for i, (pos, pri) in enumerate( zip( self._points, self._priors ) ):
            gfx = self._point_gfx[ i ]
            gfx.setPos( QtCore.QPointF( *pos ) )

            gfx = self._proir_gfx[ i ]
            gfx.setPos( QtCore.QPointF( *pri ) )

            gfx = self._track_gfx[ i ]

            # rebuild the path as QT insists on trying to be cleaver
            path = QtGui.QPainterPath()
            path.moveTo( self._tracks[ i ][0] )
            for t_pos in self._tracks[ i ][1:]:
                path.lineTo( t_pos )
            gfx.setPath( path )

    def _togTail( self ):
        for gfx in self._track_gfx.values():
            gfx.setVisible( bool( self.chk_tail.isChecked() ) )

    def _togOffs( self ):
        for gfx in self._offs_gfx.values():
            gfx.setVisible( bool( self.chk_offs.isChecked() ) )

    def _togGrid( self ):
        self._grid.setVisible( bool( self.chk_grid.isChecked() ) )

    def updateGrid( self ):
        path = QtGui.QPainterPath()
        cell_width, cell_height = self.dims[ 0 ] / self._grid_cells, self.dims[ 1 ] / self._grid_cells
        for i in range( self._grid_cells + 1 ):
            path.moveTo( i * cell_width, 0 )
            path.lineTo( i * cell_width, self.dims[ 1 ] )
            path.moveTo( 0, i * cell_height )
            path.lineTo( self.dims[ 0 ], i * cell_height )
        self._grid.setPath( path )

    def fileOpen( self ):
        """Open some MoCap Detections """
        file_fq, _ = QtWidgets.QFileDialog.getOpenFileName( self, "Choose MoCap File", self.DEFAULT_PATH )

        if not file_fq:
            return

        print( file_fq )

        # load this pickled MoCap data
        with open( file_fq, "rb" ) as fh:
            self.frames = pickle.load( fh )

        #
        f_idx = 0
        strides, dets, labels = self.frames[ f_idx ]
        num_cams = len( strides ) - 1
        self.cameras = [ i for i in range( num_cams ) ]

        # Just for testing, convert a frame and show it
        optimal = None
        while( optimal is None ):
            for cam_id in range( len( strides ) - 1 ):
                s_in, s_out = strides[ cam_id ], strides[ cam_id + 1 ]
                num_dets = s_out - s_in
                if( num_dets == 5 ):
                    optimal = cam_id
                    break
                f_idx += 1
                strides, dets, labels = self.frames[ f_idx ]

        self.frame_current = f_idx
        self.camera_current = optimal

        h_w, h_h = self.dims[0] / 2, self.dims[1] / 2
        for (x_,y_,r) in dets[ strides[ optimal ] : strides[ optimal + 1 ] ]:
            # convert back to px based coords
            x, y = x_*h_w, y_*h_h
            x += h_w
            y += h_h
            self.addPoint( QtCore.QPointF( x, y ), force=True )

    def _buildUI( self ):
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget( self.widget )

        # Display
        self._canvas = Viewer( self )
        self._canvas.setFixedSize( *self.dims )
        self._canvas.setSceneRect( 0, 0, self.dims[0], self.dims[1] )
        self._canvas.fitInView( 0, 0, self.dims[0], self.dims[1], QtCore.Qt.KeepAspectRatio )

        # the grid
        self.updateGrid()
        self._grid.setPen( QtGui.QPen( self.GRID_COL, 1, QtCore.Qt.DashLine ) )
        self._canvas.scene.addItem( self._grid )

        # Tools
        tools = QtWidgets.QVBoxLayout()

        # Point list
        point_buts = QtWidgets.QHBoxLayout()
        self.but_point_add = QtWidgets.QPushButton( "Add Point(s)" )
        self.but_point_add.setCheckable( True )

        point_buts.addWidget( self.but_point_add )
        self.but_point_rem = QtWidgets.QPushButton( "Remove Point" )
        point_buts.addWidget( self.but_point_rem )
        tools.addLayout( point_buts )

        # Mask list
        self.tab_pts = QtWidgets.QTableWidget( self )
        self.tab_pts.setRowCount( 0 )
        self.tab_pts.setColumnCount( 3 )
        self.tab_pts.setHorizontalHeaderLabels( ["Point", "True ID", "Label ID"] )
        self.tab_pts.setColumnWidth( 0, 120 )
        self.tab_pts.setColumnWidth( 1,  40 )
        self.tab_pts.setColumnWidth( 2,  50 )
        tools.addWidget( self.tab_pts )

        # Transformations
        xform_buts = QtWidgets.QHBoxLayout()
        self.but_move = QtWidgets.QPushButton( "Move Points" )
        xform_buts.addWidget( self.but_move )

        self.but_auto = QtWidgets.QPushButton( "Animate Points" )
        self.but_auto.setCheckable( True )
        xform_buts.addWidget( self.but_auto )
        tools.addLayout( xform_buts )

        # drawing
        draw_buts = QtWidgets.QHBoxLayout()
        self.chk_offs = QtWidgets.QCheckBox( "Show Offset" )
        self.chk_offs.setChecked( False )
        draw_buts.addWidget( self.chk_offs )
        self.chk_grid = QtWidgets.QCheckBox( "Show Grid" )
        self.chk_grid.setChecked( False )
        draw_buts.addWidget( self.chk_grid )
        self.chk_tail = QtWidgets.QCheckBox( "Show Trails" )
        self.chk_tail.setChecked( False )
        draw_buts.addWidget( self.chk_tail )

        tools.addLayout( draw_buts )

        # Main Layout
        layout = QtWidgets.QHBoxLayout( self.widget )
        layout.addWidget( self._canvas )
        layout.addLayout( tools )

        # File Menu
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu( "File" )

        open_action = QtWidgets.QAction( "Load MoCap", self )
        file_menu.addAction( open_action )

        # Buttons etc
        self.but_move.clicked.connect( self.movePoints )
        self.but_auto.clicked.connect( self.doAuto )
        self.chk_offs.clicked.connect( self._togOffs )
        self.chk_grid.clicked.connect( self._togGrid )
        self.chk_tail.clicked.connect( self._togTail )

        open_action.triggered.connect( self.fileOpen )

        self._canvas.sceneClicked.connect( self.addPoint )

        # set the drawing
        self._togOffs()
        self._togGrid()
        self._togTail()

def main():
    app = QtWidgets.QApplication( [] )
    #app.setStyle( "Fusion" )

    player = Player()
    player.show()
    player.resize ( 800, 600 )

    app.exec_()

if __name__ == "__main__":
    main()