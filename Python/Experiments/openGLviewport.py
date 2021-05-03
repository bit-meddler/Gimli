#import ctypes
import sys
import numpy as np

# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) )
CODE_PATH = os.path.join( _git_root_, "Python" )
print( CODE_PATH )
sys.path.append( CODE_PATH )

from Core.math3D import *
from GUI.shaders import ShaderHelper

import cv2

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import VoidPtr
from OpenGL import GL

from textwrap import TextWrapper


class OGLWindow( QtWidgets.QWidget ):

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.setWindowTitle( "Testing OpenGL" )

        self.glWidget = GLVP()

        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.addWidget( self.glWidget )

        toolLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout( toolLayout )

        but = QtWidgets.QPushButton( "Change BG Colour", self )
        but.clicked.connect( self._onSetCol )
        toolLayout.addWidget( but )

        self.setLayout( mainLayout )

    def _onSetCol( self ):
        colour = QtWidgets.QColorDialog.getColor( QtGui.QColor.fromRgbF( *self.glWidget.DEFAULT_BG ),
                    self, "Select Background Colour",
                    options=QtWidgets.QColorDialog.ShowAlphaChannel|QtWidgets.QColorDialog.DontUseNativeDialog
        )
        self.glWidget.bgcolour = colour.getRgbF()


class LoadShaders( ShaderHelper ):
    shader_path = os.path.join( CODE_PATH, "GUI", "Shaders" )
    vtx_f = "simpleVCTpackMVP.vert"
    frg_f = "simpleCTadd.frag"


class NavCam( object ):

    UP = QtGui.QVector3D( 0.0, 1.0, 0.0 )

    def __init__( self ):
        # locked camera
        self.locked = False

        # Camera extrinsics
        self.pos = QtGui.QVector3D( 0.0, 180.0, 200.0 ) #

        self.rot = QtGui.QVector3D( 0.0, 0.0, 0.0 ) # Roll, Pitch, Yaw
        self.int = QtGui.QVector3D( 0.0, 0.0, 0.0 ) # Compute from above?
        self.dst = 0.0 # Distance to interest

        # camera intrinsics
        self.vFoV   = 90.0  # Generic
        self.aspect = 1.777 # 16:9

        # GL Darwing
        self.nr_clip = 0.1
        self.fr_clip = 10000.0

        # GL Matrixes
        self.view = QtGui.QMatrix4x4()
        self.proj = QtGui.QMatrix4x4()

    def lookAtInterest( self ):
        if( self.locked ):
            return

        self.view.lookAt( self.pos, self.int, self.UP )
        self.dst = self.pos.distanceToPoint( self.int )
        print( self.dst )

    def updateProjection( self ):
        if (self.locked):
            return

        self.proj.perspective( self.vFoV, self.aspect, self.nr_clip, self.fr_clip )


class GLVP( QtWidgets.QOpenGLWidget ):

    DEFAULT_BG = ( 0.0, 0.1, 0.1, 1.0 )
    NAVIGATION_MODES = ( "TUMBLE", "TRUCK", "DOLLY", "ZOOM" )

    def __init__( self, parent=None ):
        # Odd Super call required with multi inheritance
        QtWidgets.QOpenGLWidget.__init__( self, parent )

        # Lock out GLPaint
        self.configured = False

        # OpenGL setup
        self.bgcolour = self.DEFAULT_BG
        self._sinfo = LoadShaders()

        self.shader_pg = None # Shader Program
        self.f = None # glFunctions

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )
        self.aspect = float(self.wh[0]) / float(self.wh[1])

        # Transform & MVP
        self.rot = 0.0

        # Navigation Camera
        self.camera = NavCam()
        self.camera.aspect = self.aspect
        self.nav_mode = None

        # ticks for redraws / updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )

    def _prepareResources( self ):
        #        positions         colors          texture coords
        cube = [-0.5, -0.5, 0.5,   1.0, 0.0, 0.0,  0.0, 0.0,
                 0.5, -0.5, 0.5,   0.0, 1.0, 0.0,  1.0, 0.0,
                 0.5,  0.5, 0.5,   0.0, 0.0, 1.0,  1.0, 1.0,
                -0.5,  0.5, 0.5,   1.0, 1.0, 1.0,  0.0, 1.0,

                -0.5, -0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
                 0.5, -0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
                 0.5,  0.5, -0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
                -0.5,  0.5, -0.5,  1.0, 1.0, 1.0,  0.0, 1.0,

                 0.5, -0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
                 0.5,  0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
                 0.5,  0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
                 0.5, -0.5,  0.5,  1.0, 1.0, 1.0,  0.0, 1.0,

                -0.5,  0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
                -0.5, -0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
                -0.5, -0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
                -0.5,  0.5,  0.5,  1.0, 1.0, 1.0,  0.0, 1.0,

                -0.5, -0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
                 0.5, -0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
                 0.5, -0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
                -0.5, -0.5,  0.5,  1.0, 1.0, 1.0,  0.0, 1.0,

                 0.5,  0.5, -0.5,  1.0, 0.0, 0.0,  0.0, 0.0,
                -0.5,  0.5, -0.5,  0.0, 1.0, 0.0,  1.0, 0.0,
                -0.5,  0.5,  0.5,  0.0, 0.0, 1.0,  1.0, 1.0,
                 0.5,  0.5,  0.5,  1.0, 1.0, 1.0,  0.0, 1.0,
        ]
        obj = np.array( cube, dtype=np.float32 )

        indices = [
             0,  1,  2,  2,  3,  0,
             4,  5,  6,  6,  7,  4,
             8,  9, 10, 10, 11,  8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20,
        ]

        self.indices = np.array( indices, dtype=np.uint )

        self.num_idx = len( indices )
        self.first_idx = 0

        # Generate OGL Buffers

        # Main VAO
        self.vao = QtGui.QOpenGLVertexArrayObject()
        self.vao.create()
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )

        # Vertex Data VBO
        self.vbo = QtGui.QOpenGLBuffer( QtGui.QOpenGLBuffer.VertexBuffer )
        self.vbo.create()
        self.vbo.setUsagePattern( QtGui.QOpenGLBuffer.StaticDraw )

        # Load VBO
        self.vbo.bind()
        self.vbo.allocate( obj.tobytes(), obj.nbytes )
        self.vbo.release()

        # Index Buffer
        self.ibo = QtGui.QOpenGLBuffer( QtGui.QOpenGLBuffer.IndexBuffer )
        self.ibo.create()
        self.ibo.setUsagePattern( QtGui.QOpenGLBuffer.StaticDraw )

        # Load IBO
        self.ibo.bind()
        self.ibo.allocate( self.indices.tobytes(), self.indices.nbytes )
        self.ibo.release()

        # Load Texture Image
        img = cv2.imread( "wood.jpg", cv2.IMREAD_COLOR )
        rgb_img = cv2.cvtColor( img, cv2.COLOR_BGR2RGB )
        i_h, i_w, _ = rgb_img.shape

        # convert cv2 Image to QImage
        q_img = QtGui.QImage( rgb_img.data, i_w, i_h, (3 * i_w), QtGui.QImage.Format_RGB888 )

        # Create Texture
        self.texture = QtGui.QOpenGLTexture( QtGui.QOpenGLTexture.Target2D ) # Target2D === GL_TEXTURE_2D
        self.texture.create()
        self.texture.bind()
        self.texture.setData( q_img )
        self.texture.setMinMagFilters( QtGui.QOpenGLTexture.Linear, QtGui.QOpenGLTexture.Linear )
        self.texture.setWrapMode( QtGui.QOpenGLTexture.DirectionS, QtGui.QOpenGLTexture.ClampToEdge )
        self.texture.setWrapMode( QtGui.QOpenGLTexture.DirectionT, QtGui.QOpenGLTexture.ClampToEdge )
        self.texture.release()

        # Release the VAO Mutex Binder
        del( vao_lock )

    # Generic GL Config --------------------------------------------------------
    def _configureShaders( self ):

        self.shader_pg = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader_pg.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, self._sinfo.vtx_src  )
        self.shader_pg.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, self._sinfo.frg_src )

        # Bind attrs
        for name, location in self._sinfo.attr_locs.items():
            self.shader_pg.bindAttributeLocation( name, location )

        # Link Shader
        is_linked = self.shader_pg.link()
        if( not is_linked ):
            print( "Error linking shader!" )

        # Locate uniforms
        for uniform, data in self._sinfo.vtx_uniforms.items():
            location = self.shader_pg.uniformLocation( uniform )
            self._sinfo.vtx_unis[ uniform ] = location
            print( "Vtx uniform '{}' ({}{}) bound @ {}".format(
                   uniform, data[ "type"  ], data[ "shape" ], location )
            )

    def _configureVertexAttribs( self ):
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.vbo.bind()
        for name, num, offset in self._sinfo.layout:
            location = self._sinfo.attr_locs[ name ]
            print( "Setting VAP on '{}' @ {} with {} elems from {}b".format(
                name, location, num, offset )
            )
            os_ptr = VoidPtr( offset )
            self.f.glEnableVertexAttribArray( location )
            self.f.glVertexAttribPointer(  location,
                                           num,
                                           GL.GL_FLOAT,
                                           GL.GL_FALSE,
                                           self._sinfo.line_size,
                                           os_ptr )
        self.vbo.release()
        del( vao_lock )

    def getGlInfo( self, show_ext=False ):
        print( "Getting GL Info" )

        ven = self.f.glGetString( GL.GL_VENDOR )
        ren = self.f.glGetString( GL.GL_RENDERER )
        ver = self.f.glGetString( GL.GL_VERSION )
        slv = self.f.glGetString( GL.GL_SHADING_LANGUAGE_VERSION )
        ext = self.f.glGetString( GL.GL_EXTENSIONS )

        exts = ""
        if (show_ext):
            pad = "            "
            w = TextWrapper( width=100, initial_indent="", subsequent_indent=pad )
            lines = w.wrap( ext )
            exts = "\n".join( lines )

        else:
            exts = "{} installed".format( len( ext.split() ) )

        info = "Vendor: {}\nRenderer: {}\nOpenGL Version: {}\nShader Version: {}\nExtensions: {}".format(
            ven, ren, ver, slv, exts )

        # Get context Info?

        return info

    def _onClosing( self ):
        """ Clean close of OGL resources """
        print( "Clean Close" )
        self.context().makeCurrent()

        self.vbo.destroy()
        self.ibo.destroy()
        self.texture.destroy()
        self.vao.destroy()

        del( self.shader_pg )
        self.shader_pg = None

        self.doneCurrent()

    # Navigation funcs ---------------------------------------------------------
    def _beginNav( self, mode ):
        """ begin or change a navigation interaction """
        if( self.nav_mode == mode ):
            return # still in the same mode

        # Complete the last interaction
        self._endNav()

        self.nav_mode = mode

    def _endNav( self ):
        self.nav_mode = None

    # Qt funcs -----------------------------------------------------------------
    def mousePressEvent(self, event):
        """ Determine what interactions we're making with the scene. """
        buttons = event.buttons()
        modifiers = event.modifiers()

        # All interactions need to calculate a delta from the start point
        self._last_x, self._last_y = event.x(), event.y()

        lmb = bool( buttons & QtCore.Qt.LeftButton  )
        mmb = bool( buttons & QtCore.Qt.MidButton   )
        rmb = bool( buttons & QtCore.Qt.RightButton )

        if( bool(modifiers & QtCore.Qt.AltModifier) ):
            # 3D Navigation has begun
            if( lmb ):
                if( rmb ):
                    self._beginNav( "TRUCK" )

                else:
                    self._beginNav( "TUMBLE" )

            elif( rmb ):
                self._beginNav( "DOLLY" )

            elif( mmb ):
                self._beginNav( "ZOOM" )

    def mouseReleaseEvent( self, event ):
        buttons = event.buttons()

        if( buttons == 0 ):
            self._endNav()
            #super( GLVP, self ).mouseReleaseEvent( event ) #???

        else:
            # use the new button mask to change tools,
            # e.g. toggle between Truck & Tumble
            self.mousePressEvent( event )

    def mouseMoveEvent( self, event ):
        """ The real meat of navigation goes on here. """
        if( self.nav_mode is None ):
            return

        # mouse motion computations
        new_x, new_y = event.x(), event.y()
        d_x, d_y = new_x - self._last_x, new_y - self._last_y

        if(   self.nav_mode == "TRUCK" ):
            """ Move camera position in X and Y, move interest to match. """
            offset = QtGui.QVector3D( d_x * 0.1, d_y * 0.1, 0.0 )
            self.camera.pos += offset
            self.camera.int += offset
            self.camera.lookAtInterest()

        elif( self.nav_mode == "TUMBLE" ):
            """ Arc Ball interaction? move camera position around surface of ball
                centred at interest, with r being interest distance.
            """
            pass

        elif( self.nav_mode == "DOLLY" ):
            """ Translate along the vector from camera pos to interest, move
                interest away an equal amount.
            """
            pass

        elif( self.nav_mode == "ZOOM" ):
            """ Narrow the FoV """
            pass

        self._last_x, self._last_y = new_x, new_y

    def minimumSizeHint( self ):
        return QtCore.QSize( 400, 400 )

    def sizeHint( self ):
        return QtCore.QSize( 400, 400 )


    # gl funs ------------------------------------------------------------------
    def initializeGL( self ):
        super( GLVP, self ).initializeGL()

        # init GL Context
        ctx = self.context()
        ctx.aboutToBeDestroyed.connect( self._onClosing )

        # get Context bound GL Funcs
        self.f = QtGui.QOpenGLFunctions( ctx )
        self.f.initializeOpenGLFunctions()

        # shaders
        self._configureShaders()

        # buffers & Textures
        self.f.glEnable( GL.GL_TEXTURE_2D )
        self._prepareResources()

        # Attrs
        self._configureVertexAttribs()

        # misc
        self.f.glClearColor( *self.bgcolour )

        self.f.glEnable( GL.GL_DEPTH_TEST )
        self.f.glDepthFunc( GL.GL_LESS )

        self.f.glEnable( GL.GL_BLEND )
        self.f.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )

        self.f.glEnable( GL.GL_POINT_SMOOTH )
        self.f.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )

        # Setup Camera
        self.camera.lookAtInterest()
        self.camera.updateProjection()

        # Start auto updates
        self.timer.start( 16 )  # approx 60fps

        self.configured = True

    def paintGL( self ):
        # guard against early drawing
        if( not self.configured ):
            return

        # Going to try overpainting again...
        painter = QtGui.QPainter()
        painter.begin( self )

        # Enable GL
        painter.beginNativePainting()

        # gl Viewport
        self.f.glEnable( GL.GL_DEPTH_TEST ) # Has to be reset because painter :(
        self.f.glClearColor( *self.bgcolour )
        #self.f.glViewport( 0, 0, self.wh[0], self.wh[1] )

        # attach VAO
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.shader_pg.bind()

        # ??? am I supposed to bind these guys here?
        self.vbo.bind()
        self.ibo.bind()
        self.texture.bind()

        # Move the Cube
        transform = QtGui.QMatrix4x4() # Remember these are transpose

        # start drawing
        self.f.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
        ptr = VoidPtr( self.first_idx )

        # Update View / Projection mats
        self.shader_pg.setUniformValue( self._sinfo.vtx_unis[ "u_view" ], self.camera.view )
        self.shader_pg.setUniformValue( self._sinfo.vtx_unis[ "u_projection" ], self.camera.proj )

        # Draw a field of cubes
        scale = 25.0
        for i in range( 10 ):
            y_rot = (self.rot/11.0) + (i*6.0)
            for j in range( 10 ):
                for k in range( 10 ):
                    x = (i-5) * 4.5
                    y = (j-5) * 4.5
                    z = (-1-k) * 4.5

                    x *= scale
                    y *= scale
                    z *= scale
                    #print( x, y, z )
                    transform.setToIdentity()
                    transform.translate( x, y, z )
                    transform.rotate( self.rot, 1.0, 0.0, 0.0 ) # ang, axis
                    transform.rotate( y_rot, 0.0, 1.0, 0.0 )
                    transform.rotate( i+j+k, 0.0, 0.0, 1.0 )
                    transform.scale( 12.0 )

                    self.shader_pg.setUniformValue( self._sinfo.vtx_unis[ "u_model" ], transform )

                    self.f.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_INT, ptr )

        self.rot += 1.0

        # Done GL
        self.vbo.release()
        self.ibo.release()
        self.texture.release()
        self.shader_pg.release()
        del( vao_lock )
        self.f.glDisable( GL.GL_DEPTH_TEST )
        painter.endNativePainting()

        # Try drawing some text
        painter.setRenderHint( QtGui.QPainter.TextAntialiasing )
        painter.setPen( QtCore.Qt.white )
        painter.drawText( 10, 10, "Ha Ha I'm using the Internet" )

        painter.end()

    def resizeGL( self, width, height ):
        self.wh = ( width, height )

        self.aspect = float( self.wh[ 0 ] ) / float( self.wh[ 1 ] )
        self.camera.aspect = self.aspect
        self.f.glViewport( 0, 0, self.wh[ 0 ], self.wh[ 1 ] )
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )
