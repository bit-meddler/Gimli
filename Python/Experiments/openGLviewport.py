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

    in vec3 position ;
    in vec3 colour ;

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

class GLWidget( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        super( GLWidget, self ).__init__( parent )
        self.bgcolor = [ 0, 0.1, 0.1, 1 ]
        self.shader_attr_locs = {}

    def _prepareResources( self ):
        # the item
        self.verts = np.asarray( [ -0.5, -0.5, 0.0,
                                    0.5, -0.5, 0.0,
                                    0.0,  0.5, 0.0, ], dtype=np.float32 )
        self.vert_cols = np.eye( 3, dtype=np.float32 )

        # VBOs
        vbo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, vbo )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, self.verts.nbytes, self.verts, GL.GL_STATIC_DRAW )

        #col = GL.glGenBuffers( 1 )
        #GL.glBindBuffer( GL.GL_ARRAY_BUFFER, col )
        #GL.glBufferData( GL.GL_ARRAY_BUFFER, self.vert_cols.nbytes, self.vert_cols, GL.GL_STATIC_DRAW )

        #self.buffers = ( vbo, col )

        # something to move it
        self.rot = 1.0


    def _qglShader( self ):
        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.frg_src )

        program_attrs = ("position")#, "colour")

        for i, name in enumerate( program_attrs ):
            self.shader_attr_locs[ name ] = i
            GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ name ], name )

        self.shader.link()
        self.shader.bind()

        for name in program_attrs:
            GL.glEnableVertexAttribArray( self.shader_attr_locs[ name ] )
            GL.glVertexAttribPointer( self.shader_attr_locs[ name ], 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None )

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
        GL.glClearColor( *self.bgcolor )

    def paintGL( self ):
        GL.glClear( GL.GL_COLOR_BUFFER_BIT )
        GL.glRotate( self.rot, 0.0, 0.0, 1.0 )
        GL.glDrawArrays( GL.GL_TRIANGLES, 0, 3 )
        self.rot += 1.0

    def resizeGL( self, width, height ):
        pass
    
    
if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )