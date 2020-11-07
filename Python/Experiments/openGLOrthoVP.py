import ctypes
import sys
import numpy as np

import cv2

from PySide2 import QtCore, QtGui, QtWidgets

from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram

class OGLWindow( QtWidgets.QWidget ):

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.glWidget = GLWidget()

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

        out vec3 colour ;
        out vec2 uvCoord ;

        uniform mat4 u_transform ;
        uniform mat4 u_model ;
        uniform mat4 u_view ;
        uniform mat4 u_projection ;

        void main() {
            gl_Position = u_projection * u_view * u_model * u_transform * vec4( a_position, 1.0f ) ;
            colour = a_colour ;
            uvCoord = a_uvCoord ;

        }
    """
 
    frg_src = """
        # version 330

        in vec3 colour ;
        in vec2 uvCoord ;

        out vec4 outColor ;
        uniform sampler2D samplerTex ;

        void main() {
          // outColor = texture( samplerTex, uvCoord ) ;
          outColor = vec4( colour, 1.0 ) ;
        }
    """

class Math3D( object ):

    @staticmethod
    def genRotMat( axis, angle, degrees=False ):
        angle = np.deg2rad( angle ) if degrees else angle
        axis = axis.upper()
        ret = np.eye( 4, dtype=np.float32 )

        ca = np.cos( angle )
        sa = np.sin( angle )

        if( axis == "X" ):
            mat = [ [  1.0, 0.0, 0.0 ],
                    [  0.0,  ca, -sa ],
                    [  0.0,  sa,  ca ] ]
        elif( axis == "Y" ):
            mat = [ [  ca,  0.0,  sa ],
                    [ 0.0,  1.0, 0.0 ],
                    [ -sa,  0.0,  ca ] ]
        elif( axis == "Z" ):
            mat = [ [  ca, -sa, 0.0 ],
                    [  sa,  ca, 0.0 ],
                    [ 0.0, 0.0, 1.0 ] ]

        ret[:3,:3] = np.asarray( mat, dtype=np.float32 )

        return ret

    @staticmethod
    def genPerspProjectionFrust( h_fov, aspect, near_clip, far_clip ):
        ymax = near_clip * np.tan( np.deg2rad(h_fov) )
        xmax = ymax * aspect
        return Math3D.genPerspProjectionPlaines( -xmax, xmax, -ymax, ymax, near_clip, far_clip )

    @staticmethod
    def genPerspProjectionPlaines( left, right, bottom, top, near, far ):
        return np.array((
            (      2.0 * near / (right - left),                              0.0,                              0.0,  0.0 ),
            (                              0.0,      2.0 * near / (top - bottom),                              0.0,  0.0 ),
            (  (right + left) / (right - left),  (top + bottom) / (top - bottom),     -(far + near) / (far - near), -1.0 ),
            (                              0.0,                              0.0, -2.0 * far * near / (far - near),  0.0 ),
        ), dtype=np.float32 )

class GLWidget( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        super( GLWidget, self ).__init__( parent )
        self.bgcolor = [ 0, 0.1, 0.1, 1 ]
        self.shader_attr_locs = {}

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # something to move it
        self.rot = 1.0

        # Guard
        self.ready = True

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

        # Set the texture wrapping parameters
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT )
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT )

        # Set texture filtering parameters
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR )
        GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR )

        img = cv2.imread( "wood.jpg" , cv2.IMREAD_COLOR )
        i_h, i_w, _ = img.shape

        GL.glTexImage2D( GL.GL_TEXTURE_2D, 0, GL.GL_RGB, i_w, i_h, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, img )
        GL.glEnable( GL.GL_TEXTURE_2D )

    def _qglShader( self ):

        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.frg_src )

        program_attrs = ( "a_position", "a_colour", "a_uvCoord" )

        for i, name in enumerate( program_attrs ):
            self.shader_attr_locs[ name ] = i
            GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ name ], name )

        self.shader.link()
        self.shader.bind()

        for name, (num, offset) in zip( program_attrs, self.stride_data ):
            GL.glEnableVertexAttribArray( self.shader_attr_locs[ name ] )
            GL.glVertexAttribPointer( self.shader_attr_locs[ name ],
                                      num,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self.line_sz,
                                      ctypes.c_void_p( offset ) )

        self.xform_loc = self.shader.uniformLocation( "u_transform" )
        self.model_loc = self.shader.uniformLocation( "u_model" )
        self.view_loc  = self.shader.uniformLocation( "u_view" )
        self.proj_loc  = self.shader.uniformLocation( "u_projection" )
        self.shader.release()

    # Qt funcs -------------------------------------------------------
    def minimumSizeHint(self):
        return QtCore.QSize( 50, 50 )

    def sizeHint(self):
        return QtCore.QSize( 400, 400 )


    # gl funs --------------------------------------------------------
    def initializeGL( self ):
        # buffers
        self._prepareResources()
        # shaders
        self._qglShader()
        # misc
        GL.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        GL.glEnable( GL.GL_POINT_SMOOTH )
        #GL.glEnable( GL.GL_DEPTH_TEST )
        GL.glClearColor( *self.bgcolor )

        # ticks for redraws
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )
        self.timer.start( 16 )

        # setup camera matrixes
        self.model = np.eye( 4, dtype=np.float32 )
        self.view  = np.eye( 4, dtype=np.float32 )
        self.projection = np.eye( 4, dtype=np.float32 )
        self.view[:3,3] = [0., 0., -.4]

        # assemble a projection
        w, h = self.wh
        self.projection = Math3D.genPerspProjectionFrust( 35.0, w/h, 0.10, 100.0 )
        print( self.projection )

        # Load Uniforms
        self.shader.bind()
        GL.glUniformMatrix4fv( self.model_loc, 1, GL.GL_TRUE, self.model )
        GL.glUniformMatrix4fv( self.view_loc,  1, GL.GL_TRUE, self.view )
        GL.glUniformMatrix4fv( self.proj_loc,  1, GL.GL_TRUE, self.projection )
        self.shader.release()

        self.ready = True

    def paintGL( self ):
        # guard against early drawing
        if( not self.ready ):
            return

        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        GL.glViewport( 0, 0, self.wh[0], self.wh[1] )

        rot_x = Math3D.genRotMat( "X", self.rot, degrees=True )
        rot_y = Math3D.genRotMat( "Y", self.rot+90, degrees=True )

        self.shader.bind()
        GL.glUniformMatrix4fv( self.xform_loc, 1, GL.GL_TRUE, np.dot( rot_y, rot_x ) )

        GL.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_SHORT, ctypes.c_void_p( 0 ) )
        self.shader.release()
        self.rot += 1.0

    def resizeGL( self, width, height ):
        self.wh = ( width, height )
        GL.glViewport( 0, 0, width, height )

        #self.projection = Math3D.genPerspProjectionFrust( 90.0, width/height, 0.1, 100.0 )

        self.shader.bind()
        GL.glUniformMatrix4fv( self.proj_loc,  1, GL.GL_TRUE, self.projection )
        self.shader.release()


if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )