import sys
import numpy as np

from PySide2 import QtCore, QtGui, QtWidgets

from OpenGL import GL, GLU, GLUT


class OGLWindow( QtWidgets.QWidget ):

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.glWidget = GLWidget()

        mainLayout = QtWidgets.QHBoxLayout()  
        mainLayout.addWidget( self.glWidget )
        self.setLayout( mainLayout )
        self.setWindowTitle( "Testing OpenGL" )


class GLWidget( QtWidgets.QOpenGLWidget ):

    def __init__( self, parent=None ):
        super( GLWidget, self ).__init__( parent )
        self.bgcolor = [ 0, 0.1, 0.1, 1 ]
        self._prepareResources()

    def _prepareResources( self ):
        self.verts = np.asarray( [ -0.5, -0.5, 0.0,
                                    0.5, -0.5, 0.0,
                                    0.0,  0.5, 0.0, ], dtype=np.float32 )
        self.vert_cols = np.eye( 3, dtype=np.float32 )
        self.rot = 0.1


    # Qt funcs -------------------------------------------------------
    def minimumSizeHint(self):
        return QtCore.QSize( 50, 50 )

    def sizeHint(self):
        return QtCore.QSize( 400, 400 )


    # gl funs --------------------------------------------------------
    def initializeGL( self ):
        GL.glClearColor( *self.bgcolor )
        GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
        GL.glEnableClientState( GL.GL_COLOR_ARRAY )

        GL.glVertexPointer( 3, GL.GL_FLOAT, 0, self.verts )
        GL.glColorPointer( 3, GL.GL_FLOAT, 0, self.vert_cols )

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