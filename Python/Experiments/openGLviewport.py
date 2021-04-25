import ctypes
import sys
import numpy as np

# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
sys.path.append( CODE_PATH )

from Core.math3D import *

import cv2

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import VoidPtr
from OpenGL import GL


class OGLWindow( QtWidgets.QWidget ):

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.glWidget = GLVP()

        mainLayout = QtWidgets.QHBoxLayout()  
        mainLayout.addWidget( self.glWidget )
        self.setLayout( mainLayout )
        self.setWindowTitle( "Testing OpenGL" )


class Shaders( object ):
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

    program_attrs = ( "a_position", "a_colour", "a_uvCoord" )
 
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
        self.shader_attr_locs = {}
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
        cube = np.array( cube, dtype=np.float32 )

        # ( element count, offset to first element in bytes )
        self.stride_data = [ [3, 0], [3, 3*cube.itemsize], [2, 6*cube.itemsize] ]
        self.line_sz = 8 * cube.itemsize

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

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.frg_src )

        for i, name in enumerate( Shaders.program_attrs ):
            self.shader_attr_locs[ name ] = i
            self.shader.bindAttributeLocation( name, i )

        is_linked = self.shader.link()
        if( not is_linked ):
            print( "Error linking shader!" )

        self.shader.bind()

        self.rot_loc = self.shader.uniformLocation( "u_rotation" )

        self.shader.release()

    def _configureVertexAttribs( self ):
        self.vbo.bind()
        f = QtGui.QOpenGLContext.currentContext().functions()
        f.initializeOpenGLFunctions()
        for name, (num, offset) in zip( Shaders.program_attrs, self.stride_data ):
            print( "Setting VAP on {}".format( name ) )
            ptr = VoidPtr( offset )
            f.glEnableVertexAttribArray( self.shader_attr_locs[ name ] )
            f.glVertexAttribPointer(  self.shader_attr_locs[ name ],
                                      num,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self.line_sz,
                                      ptr )
        self.vbo.release()

    def getGlInfo( self, context ):
        print( "Getting GL Info" )
        f = QtGui.QOpenGLFunctions( context )
        f.initializeOpenGLFunctions()
        ven = f.glGetString( GL.GL_VENDOR )
        ren = f.glGetString( GL.GL_RENDERER )
        ver = f.glGetString( GL.GL_VERSION )
        slv = f.glGetString( GL.GL_SHADING_LANGUAGE_VERSION )
        info = """Vendor: {}\nRenderer: {}\nOpenGL Version: {}\nShader Version: {}""".format( ven, ren, ver, slv )
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
        f.initializeOpenGLFunctions()

        # attach VAO
        vaoBinder = QtGui.QOpenGLVertexArrayObject.Binder( self.vao )
        self.shader.bind()

        # ??? I'm I supposed to bind these guys here?
        self.vbo.bind()
        self.ibo.bind()

        # Move the Cube
        rotation = QtGui.QMatrix4x4()
        rotation.rotate( self.rot, 1.0, 0.0, 0.0 )
        rotation.rotate( 17.5, 0.0, 1.0, 0.0 )

        self.shader.setUniformValue( self.rot_loc, rotation )

        # Draw
        f.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
        ptr = VoidPtr( self.first_idx )
        f.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_INT, ptr )

        self.rot += 1.0

        # Show em it's doing something...
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
        #GL.glViewport( 0, 0, width, height )
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )