import ctypes
import sys
import numpy as np

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
    # version 330 core

    in vec3 position ;

    void main() {
        gl_Position = vec4( position, 1.0 ) ;
    }
    """
    frg_src = """
    # version 330 core

    out vec4 colour ;

    void main() {
        colour = vec4( 1.0, 0.0, 0.0, 1.0 ) ;
    }
    """

    vtx2_src = """
    # version 330 core

    layout( location=0 ) in vec3 position ;
    layout( location=1 ) in vec3 colour ;

    out vec3 fcolour ;

    void main() {
        fcolour = colour ;
        gl_Position = vec4( position, 1.0 ) ;
    }
    """
    frg2_src = """
    # version 330 core

    in  vec3 fcolour ;

    out vec4 colour ;

    void main() {
        colour = vec4( fcolour, 1.0 ) ;
    }
    """
    vtx3_src = """
    # version 330 core

    layout( location=0 ) in vec3 position ;
    layout( location=1 ) in vec3 colour ;

    uniform mat4 rotation ;

    out vec3 fcolour ;

    void main() {
        fcolour = colour ;
        gl_Position = rotation * vec4( position, 1.0 ) ;
    }
    """


class Math3D( object ):

    @staticmethod
    def genRotMat( axis, angle, degrees=False ):
        angle = np.deg2rad( angle ) if degrees else angle
        axis = axis.upper()
        ret = np.eye(4)

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

class GLWidget( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        super( GLWidget, self ).__init__( parent )
        self.bgcolor = [ 0, 0.1, 0.1, 1 ]
        self.shader_attr_locs = {}

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # something to move it
        self.rot = 1.0
        self.rot_loc = None

    def _prepareResources( self ):
        # the item
        self.big_buff = np.asarray( [
            #  X     Y     Z    R    G    B
            [ -0.5, -0.5,  0.5, 1.0, 0.0, 0.0 ],
            [  0.5, -0.5,  0.5, 0.0, 1.0, 0.0 ],
            [  0.5,  0.5,  0.5, 0.0, 0.0, 1.0 ],
            [ -0.5,  0.5,  0.5, 1.0, 1.0, 0.0 ],
            
            [ -0.5, -0.5, -0.5, 1.0, 0.0, 0.0 ],
            [  0.5, -0.5, -0.5, 0.0, 1.0, 0.0 ],
            [  0.5,  0.5, -0.5, 0.0, 0.0, 1.0 ],
            [ -0.5,  0.5, -0.5, 1.0, 1.0, 0.0 ],
            
            ], dtype=np.float32 )

        self.bb_ln_sz = self.big_buff[0,:].nbytes
        self.bb_strides = [ 0, self.big_buff[0,:3].nbytes ]

        self.indexes = np.asarray(
            [ 0, 1, 2,  2, 3, 0,
              4, 5, 6,  6, 7, 4,
              4, 5, 1,  1, 0, 4,
              6, 7, 3,  3, 2, 6,
              5, 6, 2,  2, 1, 5,
              7, 4, 0,  0, 3, 7,
            ], dtype=np.uint16 )

        # VBO
        vbo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, vbo )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, self.big_buff.nbytes, self.big_buff, GL.GL_STATIC_DRAW )

        ebo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ELEMENT_ARRAY_BUFFER, ebo )
        GL.glBufferData( GL.GL_ELEMENT_ARRAY_BUFFER, self.indexes.nbytes, self.indexes, GL.GL_STATIC_DRAW )

    def _qglShader( self ):

        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.vtx3_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.frg2_src )

        program_attrs = ("position", "colour")

        for i, name in enumerate( program_attrs ):
            self.shader_attr_locs[ name ] = i
            GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ name ], name )

        self.shader.link()
        self.shader.bind()

        for name, stride in zip( program_attrs, self.bb_strides ):
            GL.glEnableVertexAttribArray( self.shader_attr_locs[ name ] )
            GL.glVertexAttribPointer( self.shader_attr_locs[ name ],
                                      3,
                                      GL.GL_FLOAT,
                                      GL.GL_FALSE,
                                      self.bb_ln_sz,
                                      ctypes.c_void_p( stride ) )

        self.rot_loc = self.shader.uniformLocation( "rotation" )

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
        GL.glEnable( GL.GL_DEPTH_TEST )
        GL.glClearColor( *self.bgcolor )

        # ticks for redraws
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )
        self.timer.start( 16 )

    def paintGL( self ):
        # guard against early drawing
        if( self.rot_loc is None ):
            pass

        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        hw, hh = int(self.wh[0] / 2), int(self.wh[1] / 2)

        # view1
        GL.glViewport( 0, 0, hw, hh )
        GL.glDrawArrays( GL.GL_TRIANGLE_STRIP, 0, 4 )

        # view2
        GL.glViewport( hw, 0, hw, hh )
        GL.glDrawArrays( GL.GL_LINE_LOOP, 0, len(self.big_buff) )

        # view3
        GL.glViewport( 0, hh, hw, hh )
        rot_x = Math3D.genRotMat( "X", self.rot, degrees=True )
        rot_y = Math3D.genRotMat( "Y", self.rot+90, degrees=True )

        GL.glUniformMatrix4fv( self.rot_loc, 1, GL.GL_TRUE, np.dot( rot_y, rot_x ) )
        GL.glDrawElements( GL.GL_TRIANGLES, len(self.indexes), GL.GL_UNSIGNED_SHORT, ctypes.c_void_p( 0 ) )

        # view4 - try out some points
        GL.glViewport( hw, hh, hw, hh )
        GL.glPointSize( 12 )
        GL.glDrawArrays( GL.GL_POINTS, 0, len(self.big_buff) )

        self.rot += 1.0

    def resizeGL( self, width, height ):
        self.wh = ( width, height )
        GL.glViewport( 0, 0, width, height )
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )