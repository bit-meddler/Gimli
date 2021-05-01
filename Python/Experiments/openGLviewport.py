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

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.glWidget = GLVP()

        mainLayout = QtWidgets.QHBoxLayout()  
        mainLayout.addWidget( self.glWidget )
        self.setLayout( mainLayout )
        self.setWindowTitle( "Testing OpenGL" )


class ShaderHelper( object ):
    # Overload these with your shader program
    vtx_src = None
    frg_src = None
    geo_src = None

    # or place a path to the file / QResource
    geo_f = None
    frg_f = None
    vtx_f = None

    LYT_RE = r".*(?:layout)" + \
             r"(?:\(\s*location\s*=\s*(?P<location>\d)\s*\))?" + \
             r"\s+(?P<specifier>\w+)" + \
             r"\s+(?P<type>[a-z]+)(?P<shape>\d*(?:x\d)?)" + \
             r"\s*(?P<name>.*?)\s*;"

    MAIN_RE = r".*void\s+main\(\).*"

    LAYOUT_MATCH = re.compile( LYT_RE  )
    MAIN_MATCH   = re.compile( MAIN_RE )

    def __init__( self ):
        # TODO: load from files

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


class BasicShaders( ShaderHelper ):
    vtx_src = """
        # version 330

        layout( location=0 ) in vec3 a_position ;
        layout( location=1 ) in vec3 a_colour ;
        layout( location=2 ) in vec2 a_uvCoord ;

        out vec3 v_colour ;
        out vec2 v_uvCoord ;

        uniform mat4 u_rotation ;

        void main() {
            gl_Position = u_rotation * vec4( a_position, 1.0f ) ;
            v_colour = a_colour ;
            v_uvCoord = a_uvCoord ;

        }
    """
    frg_src = """
        # version 330

        in vec3 v_colour ;
        in vec2 v_uvCoord ;

        out vec4 outColor ;
        uniform sampler2D s_texture ;

        void main() {
          // outColor = texture( s_texture, v_uvCoord ) ; // * vec4( v_colour, 1.0f ) ;
          outColor = vec4( v_colour, 1.0 ) ;
        }
    """


class GLVP( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        # Odd Super call required with multi inheritance
        QtWidgets.QOpenGLWidget.__init__( self, parent )

        # Lock out GLPaint
        self.configured = False

        # OpenGL setup
        self.bgcolour = [ 0.0, 0.1, 0.1, 1.0 ]
        self._shaders = BasicShaders()
        #self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # something to move it
        self.rot = 1.0
        self.rot_loc = None

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
        # OK Just try a tri :|
        cube = [-0.5, -0.5, 0.5,   1.0, 0.0, 0.0,  0.0, 0.0,
                 0.0,  0.5, 0.5,   0.0, 1.0, 0.0,  1.0, 0.0,
                 0.5, -0.5, 0.5,   0.0, 0.0, 1.0,  1.0, 1.0, ]
        cube = np.array( cube, dtype=np.float32 )

        indices = [
             0,  1,  2,  2,  3,  0,
             4,  5,  6,  6,  7,  4,
             8,  9, 10, 10, 11,  8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20,
        ]
        indices = [
            0, 1, 2,
        ]
        self.indices = np.array( indices, dtype=np.uint )

        self.num_idx = len( indices )
        self.first_idx = 0

        # Generate OGL Buffers

        # Main VAO
        self.vao = QtGui.QOpenGLVertexArrayObject()
        self.vao.create()
        vaoBinder = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )

        # Vertex Data VBO
        self.vbo = QtGui.QOpenGLBuffer( QtGui.QOpenGLBuffer.VertexBuffer )
        self.vbo.create()
        self.vbo.setUsagePattern( QtGui.QOpenGLBuffer.StaticDraw )

        # Load VBO
        self.vbo.bind()
        self.vbo.allocate( cube.tobytes(), cube.nbytes )
        self.vbo.release()

        # Index Buffer
        self.ibo = QtGui.QOpenGLBuffer( QtGui.QOpenGLBuffer.IndexBuffer )
        self.ibo.create()
        self.ibo.setUsagePattern( QtGui.QOpenGLBuffer.StaticDraw )

        # Load IBO
        self.ibo.bind()
        self.ibo.allocate( self.indices.tobytes(), self.indices.nbytes )
        self.ibo.release()

        # Skip texture for now, commented out in shader
        if( False ):
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

        # Release the VAO Mutex Binder
        del( vaoBinder )

    def _configureShaders( self ):

        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, self._shaders.vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, self._shaders.frg_src )

        for name, location in self._shaders.attr_locs.items():
            self.shader.bindAttributeLocation( name, location )

        is_linked = self.shader.link()
        if( not is_linked ):
            print( "Error linking shader!" )

        self.shader.bind()

        self.rot_loc = self.shader.uniformLocation( "u_rotation" )

        eye = QtGui.QMatrix4x4()
        self.shader.setUniformValue( self.rot_loc, eye )

        self.shader.release()

    def _configureVertexAttribs( self ):
        self.vbo.bind()
        f = QtGui.QOpenGLContext.currentContext().functions()
        f.initializeOpenGLFunctions()
        for name, num, offset in self._shaders.layout:
            location = self._shaders.attr_locs[ name ]
            print( "Setting VAP on '{}' @ {} with {} elems from {}b".format(
                name, location, num, offset ) )
            os_ptr = VoidPtr( offset )
            f.glEnableVertexAttribArray( location )
            f.glVertexAttribPointer(  location,
                                      num,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self._shaders.line_size,
                                      os_ptr )
        self.vbo.release()

    def getGlInfo( self, context, show_ext=False ):
        print( "Getting GL Info" )

        f = QtGui.QOpenGLFunctions( context )
        f.initializeOpenGLFunctions()
        ven = f.glGetString( GL.GL_VENDOR )
        ren = f.glGetString( GL.GL_RENDERER )
        ver = f.glGetString( GL.GL_VERSION )
        slv = f.glGetString( GL.GL_SHADING_LANGUAGE_VERSION )
        ext = f.glGetString( GL.GL_EXTENSIONS )

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

        del( self.shader )
        self.shader = None

        self.doneCurrent()


    # Qt funcs -------------------------------------------------------
    def minimumSizeHint(self):
        return QtCore.QSize( 50, 50 )

    def sizeHint(self):
        return QtCore.QSize( 400, 400 )


    # gl funs --------------------------------------------------------
    def initializeGL( self ):
        super( GLVP, self ).initializeGL()

        # init GL Context
        ctx = self.context()
        ctx.aboutToBeDestroyed.connect( self._onClosing )

        print( self.getGlInfo( ctx ) )

        f = QtGui.QOpenGLFunctions( ctx )
        f.initializeOpenGLFunctions()

        # shaders
        self._configureShaders()

        # buffers & Textures
        f.glEnable( GL.GL_TEXTURE_2D )
        self._prepareResources()

        # Attrs
        self._configureVertexAttribs()

        # misc
        f.glClearColor( *self.bgcolour )
        #f.glEnable( GL.GL_POINT_SMOOTH )
        #f.glEnable( GL.GL_DEPTH_TEST )
        #f.glEnable( GL.GL_BLEND )
        #f.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        #f.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )

        # Start auto updates
        self.timer.start( 16 )  # approx 60fps

        self.configured = True

    def paintGL( self ):
        # guard against early drawing
        if( not self.configured ):
            return

        # get Context
        ctx = self.context()
        f = QtGui.QOpenGLFunctions( ctx )
        #f.initializeOpenGLFunctions()

        # gl Viewport
        f.glViewport( 0, 0, self.wh[0], self.wh[1] )

        # attach VAO
        vaoBinder = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.shader.bind()

        # ??? am I supposed to bind these guys here?
        self.vbo.bind()
        self.ibo.bind()

        # Move the Cube
        rotation = QtGui.QMatrix4x4() # Remember these are transpose
        rotation.rotate( self.rot, 1.0, 0.0, 0.0 ) # ang, axis
        rotation.rotate( 17.5,     0.0, 1.0, 0.0 )

        self.shader.setUniformValue( self.rot_loc, rotation )

        # Draw
        f.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
        ptr = VoidPtr( self.first_idx )
        f.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_INT, ptr )

        self.rot += 1.0

        # Show me it's doing something, even if it's not drawing anything...
        if( self.rot % 80 == 0 ):
            print( ".", end="\n" )
        else:
            print( ".", end="" )


        # Done
        self.vbo.release()
        self.ibo.release()
        self.shader.release()
        del( vaoBinder )


    def resizeGL( self, width, height ):
        self.wh = ( width, height )
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )
