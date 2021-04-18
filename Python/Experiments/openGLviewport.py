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


class GLVP( QtWidgets.QOpenGLWidget, QtGui.QOpenGLFunctions ):

    def __init__( self, parent=None ):
        # Odd Super call required with multi inheritance
        QtWidgets.QOpenGLWidget.__init__( self, parent )
        QtGui.QOpenGLFunctions.__init__( self )

        # OpenGL setup
        self.bgcolor = [ 0.0, 0.1, 0.1, 1.0 ]
        self.shader_attr_locs = {}
        #self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # something to move it
        self.rot = 1.0
        self.rot_loc = None

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
        indices = np.array( indices, dtype=np.uint16 )

        self.num_idx = len( indices )

        # VBO
        vbo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, vbo )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, cube.nbytes, cube, GL.GL_STATIC_DRAW )

        ebo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ELEMENT_ARRAY_BUFFER, ebo )
        GL.glBufferData( GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW )

        # load and setup texture
        texture = GL.glGenTextures( 1 )
        GL.glBindTexture( GL.GL_TEXTURE_2D, texture )


        img = cv2.imread( "wood.jpg" , cv2.IMREAD_COLOR )
        rgb_img = cv2.cvtColor( img, cv2.COLOR_BGR2RGB )
        i_h, i_w, _ = img.shape
        
        GL.glTexImage2D( GL.GL_TEXTURE_2D, 0, GL.GL_RGB, i_w, i_h, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, rgb_img )

        # Set the texture wrapping parameters
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE )
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE )

        # Set texture filtering parameters
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR )
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR )


    def _configureShaders( self ):

        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.frg_src )

        for i, name in enumerate( Shaders.program_attrs ):
            self.shader_attr_locs[ name ] = i
            self.shader.bindAttributeLocation( name, i )

        self.shader.link()
        self.shader.bind()

    def _configureVertexAttribs( self ):
        f = QtGui.QOpenGLContext.currentContext().functions()
        for name, (num, offset) in zip( Shaders.program_attrs, self.stride_data ):
            ptr = VoidPtr( offset )
            f.glEnableVertexAttribArray( self.shader_attr_locs[ name ] )
            f.glVertexAttribPointer( self.shader_attr_locs[ name ],
                                      num,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self.line_sz,
                                      ptr )

        self.rot_loc = self.shader.uniformLocation( "u_rotation" )


    # Qt funcs -------------------------------------------------------
    def minimumSizeHint(self):
        return QtCore.QSize( 50, 50 )

    def sizeHint(self):
        return QtCore.QSize( 400, 400 )


    # gl funs --------------------------------------------------------
    def initializeGL( self ):
        # shaders
        self._configureShaders()

        # buffers
        self._prepareResources()

        # Attrs
        self._configureVertexAttribs()

        # misc
        #self.glEnable( GL.GL_TEXTURE_2D )
        #GL.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        #GL.glEnable( GL.GL_POINT_SMOOTH )
        #GL.glEnable( GL.GL_DEPTH_TEST )
        #GL.glEnable( GL.GL_CULL_FACE )

        GL.glEnable( GL.GL_BLEND )
        GL.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )
        GL.glClearColor( *self.bgcolor )

        # ticks for redraws
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )
        self.timer.start( 16 ) # approx 60fps

    def paintGL( self ):
        # guard against early drawing
        if( self.rot_loc is None ):
            return

        self.shader.bind()


        # Drawing Settings
        #self.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        #self.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
        #self.glEnable( GL.GL_POINT_SMOOTH )
        #self.glEnable( GL.GL_DEPTH_TEST )

        rotation = QtGui.QMatrix4x4()
        rotation.rotate( self.rot, 1.0, 0.0, 0.0 )
        rotation.rotate( 17.5, 0.0, 1.0, 0.0 )

        self.shader.setUniformValue( self.rot_loc, rotation )

        self.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_SHORT, 0 )

        self.shader.release()

        self.rot += 1.0

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