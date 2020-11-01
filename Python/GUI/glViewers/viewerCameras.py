"""
    Cameras view, will show centroids and maybe an image from the camera
    maybe visualize a wandwave in here as well
"""

import logging
import numpy as np
np.set_printoptions( precision=3, suppress=True )
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
import ctypes
from OpenGL import GL, GLU, GLUT



SQUARES = [ x ** 2 for x in range( 9 ) ]

class Shaders( object ):
    dot_vtx_src = """
    # version 330 core

    layout( location=0 ) in vec2 position ;

    void main() {
        gl_Position = vec4( position, 0.0, 1.0 ) ;
    }
    """
    dot_frg_src = """
    # version 330 core

    out vec4 colour ;

    void main() {
        colour = vec4( 0.0, 1.0, 0.0, 1.0 ) ;
    }
    """

class QGLCameraView( QtWidgets.QOpenGLWidget ):

    def __init__(self, parent=None ):
        super(QGLCameraView, self).__init__( parent )
        # canvas size
        self._wh = (self.geometry().width(), self.geometry().height())
        self._rc = ( 1, 1 ) # ros and cols of cameras to display

        self._subwindow_sz = ( 0, 0 )

        self.cam_list = []
        self.num_cams = 0

        # OK, for now assume we display all camera, not a selected sub-set
        self.stride_list = []
        # helper for s_in and s_out indexes
        self._strider = [] # but around here, he's known as Strider.

        # OpenGL attrs
        self.shader = None
        self.shader_attr_locs = {}

        # The Reticule (pairs for glLines)
        self._reticule = np.array(
            [ [-1.0,  1.0], [ 1.0,  1.0], # Box
              [ 1.0,  1.0], [ 1.0, -1.0],
              [ 1.0, -1.0], [-1.0, -1.0],
              [-1.0, -1.0], [-1.0,  1.0],
              # ticks
              [-1.0, 0.0], [-0.95, 0.0],
              [ 1.0, 0.0], [ 0.95, 0.0],
              [ 0.0,-1.0], [ 0.0, -0.95],
              [ 0.0, 1.0], [ 0.0,  0.95 ],
            ], dtype=np.float32 ) # 16 Elems, 128 Bytes
        self.vbo = None
        self.has_data = False

    def acceptNewData( self, dets, strides, ids ):
        my_dets = np.asarray( dets[:,:2], dtype=np.float32 ) # ignore r for now
        self.stride_list = np.asarray( strides, dtype=np.integer )
        packed_data = np.concatenate( (self._reticule, my_dets) )

        # load to VBO
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self.vbo )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, packed_data.nbytes, packed_data, GL.GL_STATIC_DRAW )

        # call redraw
        self.has_data = True
        self.update()

    def initializeGL( self ):
        GL.glClearColor( 0.0, 0.0, 0.0, 1.0 )

        # Setup Dot shader
        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.dot_vtx_src  )
        self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.dot_frg_src )

        self.shader_attr_locs[ "position" ] = 0
        GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ "position" ], "position" )

        self.shader.link()
        self.shader.bind()

        # configure Attrib
        GL.glVertexAttribPointer( 0, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p( 0 ) )

        # Get a buffer
        self.vbo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self.vbo )

    def resizeGL( self, width, height ):
        self._wh = ( width, height )
        # compute subwindow dimentions
        rows, cols = self._rc
        sub_w = int( width / cols )
        sub_h = int( height / rows )
        self._subwindow_sz = ( sub_w, sub_h )

    def paintGL( self ):
        """ Draw the cameras """
        if( not self.has_data ):
            return
        
        # clear
        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        rows, cols = self._rc
        w, h = self._subwindow_sz
        hw = int( w / 2 )
        height = self._wh[1]

        # get the right buffer ? 0 - guess not
        #GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self.vbo )
        # set dot size
        GL.glPointSize( 4 )

        cam_idx = 0 # NOT cam Number, idx in cam_list
        for r in range( rows-1, -1, -1 ):
            for c in range( cols ):
                x, y =  c*w, r*h

                # setup an Orthogonal Projection
                GL.glViewport( x, y, w, h )

                # ToDo: draw an image - texture on a quad in BG?

                # Draw Roids
                sin, sout = self._strider[ cam_idx ]
                idx_in, idx_out = self.stride_list[ sin ]+16, self.stride_list[ sout ]+16
                GL.glDrawArrays( GL.GL_POINTS, idx_in, idx_out )

                # Draw reticule
                #GL.glDrawArrays( GL.GL_LINES, 0, 16 ) # Size of reticule

                self.hudText( x+hw-50, height-y-5, "Camera {}".format( cam_idx ) )

                # Done?
                cam_idx += 1
                if( cam_idx >= self.num_cams ):
                    break

    def hudText( self, x, y, text ):
        painter = QtGui.QPainter( self )
        painter.setPen( QtCore.Qt.green )
        painter.setFont( QtGui.QFont( "Helvetica", 8 ) )
        painter.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing )
        painter.drawText( x, y, text )
        painter.end()

    def _camFromXY( self, x, y ):
        rows, _ = self._rc
        w, h = self._subwindow_sz
        y = y - self._wh[ 1 ]  # top left to bottom left conversion
        c = x // w
        r = y // h
        idx = (rows * r) + c
        if (idx > len( self.cam_list )):
            idx = -1
        return idx

    def _camlistChanged( self ):
        self.num_cams = len( self.cam_list )
        self._rc = self.genDimsSquare( self.num_cams )
        self._marshelStrides()

    def _marshelStrides( self ):
        self._strider = []
        for _in, _out in zip( range(0,self.num_cams), range(1,self.num_cams+1) ):
            self._strider.append( (_in,_out) )

    @staticmethod
    def genDimsSquare( num_cams ):
        """
        Determine rows / cols needed to pack num_cams into to keep square

        :param num_cams: (int) number of cameras to arrange
        :return: (int,int) Rows, Cols
        """
        x = 0
        while( SQUARES[ x ] < num_cams ):
            x += 1

        if (x > 0):
            y, r = divmod( num_cams, x )
        else:
            y, r = 0, 0

        if (r > 0):
            y += 1

        return (x, y)
