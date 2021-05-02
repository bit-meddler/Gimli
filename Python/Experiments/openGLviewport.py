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

import cv2

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import VoidPtr
from OpenGL import GL

import re
from textwrap import TextWrapper


class OGLWindow( QtWidgets.QWidget ):

    DEFAULT_BG = QtGui.QColor.fromRgbF( 0.0, 0.1, 0.1, 1.0 )

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
        colour = QtWidgets.QColorDialog.getColor(
                    self.DEFAULT_BG, self, "Select Background Colour",
                    options=QtWidgets.QColorDialog.ShowAlphaChannel|QtWidgets.QColorDialog.DontUseNativeDialog
        )
        self.glWidget.setBgCol( colour )


class ShaderHelper( object ):
    # Overload these with your shader program
    vtx_src = None
    frg_src = None
    geo_src = None

    # or place a path to the file / QResource
    vtx_f = None
    frg_f = None
    geo_f = None

    LAYOUT_RE = r".*(?:layout)" + \
                r"(?:\(\s*location\s*=\s*(?P<location>\d)\s*\))?" + \
                r"\s+(?P<specifier>\w+)" + \
                r"\s+(?P<type>[a-z]+)(?P<shape>\d*(?:x\d)?)" + \
                r"\s*(?P<name>.*?)\s*;"

    MAIN_RE = r".*void\s+main\(\).*"

    LAYOUT_MATCH = re.compile( LAYOUT_RE  )
    MAIN_MATCH   = re.compile( MAIN_RE )

    def __init__( self ):
        # Attempt to load files
        for file_path in (self.vtx_f,self.frg_f,self.geo_f,):
            if( file_path is None ):
                continue

            # there is a path, attempt to load
            if( os.path.exists( file_path ) ):
                with open( file_path, "r" ) as fh:
                    program = fh.read()

                if( file_path.endswith(".vert") ):
                    self.vtx_src = program

                elif( file_path.endswith(".frag") ):
                    self.frg_src = program

                elif( file_path.endswith(".geom") ):
                    self.geo_src = program

                # elif( file_path.endswith(".tesc") ):
                #     self.unimp = program

                # elif( file_path.endswith(".tese") ):
                #     self.unimp = program

                # elif( file_path.endswith(".comp") ):
                #     self.unimp = program

        # Examine the Vertex Shader's attributes
        attr_data = []
        for line in self.vtx_src.splitlines():
            if (not line):
                continue

            match = self.LAYOUT_MATCH.match( line )
            if (match):
                attr_data.append( match.groupdict() )
                continue

            match = self.MAIN_MATCH.match( line )
            if (match):
                break

        # Determine the layout data
        offset = 0
        encountered = set()
        layout_data = {}

        for idx, attr in enumerate( attr_data ):
            # some preemptive error checks
            if (attr[ "name" ] in encountered):
                print( "Warning, already processed a variable called '{}'".format( attr[ "name" ] ) )
            encountered.add( attr[ "name" ] )

            if (attr[ "location" ] in layout_data):
                print( "Warning, already processed data in location '{}'".format( attr[ "location" ] ) )

            # New in GLSL 4.0 double, dvecN, dmatN, dmatNxM
            size = 8 if (attr[ "type" ].startswith( "d" )) else 4  # even a bool is a 32-bit value

            dims = 0
            if (attr[ "shape" ] == ""):  # Scaler
                dims = 1

            elif ("x" in attr[ "shape" ]):  # Has to be a matrix
                N, M = map( int, attr[ "shape" ].split( "x" ) )
                dims = N * M

            else:  # either a vec or a square mat
                N = int( attr[ "shape" ] )
                if ("mat" in attr[ "type" ]):
                    dims = N * N
                else:
                    dims = N

            layout_data[ int( attr[ "location" ] ) ] = ( attr[ "name" ], dims, offset )
            offset += dims * size

        # Stash the layout data
        self.attr_locs = {}

        layout = []
        for idx in sorted( layout_data.keys() ):
            data = layout_data[ idx ]
            layout.append( data )
            self.attr_locs[ data[0] ] = idx

        self.layout = tuple( layout )
        self.line_size = offset

        # TODO: Look for uniforms as well
        # TODO: Validate vtx 'outs' match frg 'in's


class TestLoadingShaders( ShaderHelper ):
    vtx_f = "simpleVCTpack.vert"
    frg_f = "simpleCTadd.frag"


class GLVP( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        # Odd Super call required with multi inheritance
        QtWidgets.QOpenGLWidget.__init__( self, parent )

        # Lock out GLPaint
        self.configured = False

        # OpenGL setup
        self.bgcolour = [ 0.0, 0.1, 0.1, 1.0 ]
        self._shaders = TestLoadingShaders()

        self.shader_pg = None
        self.f = None

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # something to move it
        self.rot = 1.0
        self.xform_loc = None

        # ticks for redraws / updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )


    def setBgCol( self, colour ):
        self.bgcolour = colour.getRgbF()

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

    def _configureShaders( self ):

        self.shader_pg = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader_pg.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, self._shaders.vtx_src  )
        self.shader_pg.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, self._shaders.frg_src )

        # Bind attrs
        for name, location in self._shaders.attr_locs.items():
            self.shader_pg.bindAttributeLocation( name, location )

        is_linked = self.shader_pg.link()
        if( not is_linked ):
            print( "Error linking shader!" )

        self.shader_pg.bind()

        # Locate uniforms
        self.xform_loc = self.shader_pg.uniformLocation( "u_transform" )

        eye = QtGui.QMatrix4x4()
        self.shader_pg.setUniformValue( self.xform_loc, eye )

        self.shader_pg.release()

    def _configureVertexAttribs( self ):
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.vbo.bind()
        for name, num, offset in self._shaders.layout:
            location = self._shaders.attr_locs[ name ]
            print( "Setting VAP on '{}' @ {} with {} elems from {}b".format(
                name, location, num, offset ) )
            os_ptr = VoidPtr( offset )
            self.f.glEnableVertexAttribArray( location )
            self.f.glVertexAttribPointer(  location,
                                      num,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self._shaders.line_size,
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
        self.vao.destroy()
        self.texture.destroy()

        del( self.shader_pg )
        self.shader_pg = None

        self.doneCurrent()


    # Qt funcs -------------------------------------------------------
    def minimumSizeHint(self):
        return QtCore.QSize( 400, 400 )

    def sizeHint(self):
        return QtCore.QSize( 400, 400 )


    # gl funs --------------------------------------------------------
    def initializeGL( self ):
        super( GLVP, self ).initializeGL()

        # init GL Context
        ctx = self.context()
        ctx.aboutToBeDestroyed.connect( self._onClosing )

        self.f = QtGui.QOpenGLFunctions( ctx )
        self.f.initializeOpenGLFunctions()

        print( self.getGlInfo() )

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
        self.f.glEnable( GL.GL_BLEND )
        self.f.glEnable( GL.GL_POINT_SMOOTH )
        self.f.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        self.f.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )

        # Start auto updates
        self.timer.start( 16 )  # approx 60fps

        self.configured = True

    def paintGL( self ):
        # guard against early drawing
        if( not self.configured ):
            return

        # gl Viewport
        self.f.glClearColor( *self.bgcolour )
        self.f.glViewport( 0, 0, self.wh[0], self.wh[1] )

        # attach VAO
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.shader_pg.bind()

        # ??? am I supposed to bind these guys here?
        self.vbo.bind()
        self.ibo.bind()
        self.texture.bind()

        # Move the Cube
        transform = QtGui.QMatrix4x4() # Remember these are transpose
        transform.rotate( self.rot, 1.0, 0.0, 0.0 ) # ang, axis
        transform.rotate( 17.5,     0.0, 1.0, 0.0 )

        self.shader_pg.setUniformValue( self.xform_loc, transform )

        # Draw
        self.f.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
        ptr = VoidPtr( self.first_idx )
        self.f.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_INT, ptr )

        self.rot += 1.0

        # Done
        self.vbo.release()
        self.ibo.release()
        self.texture.release()
        self.shader_pg.release()
        del( vao_lock )


    def resizeGL( self, width, height ):
        self.wh = ( width, height )
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )
