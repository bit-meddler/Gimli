"""
    Cameras view, will show centroids and maybe an image from the camera
    maybe visualize a wandwave in here as well
"""

import logging
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
from OpenGL import GL, GLU, GLUT



SQUARES = [ x ** 2 for x in range( 9 ) ]

class QGLCameraView( QtOpenGL.QGLWidget ):

    def __init__(self, parent=None ):
        super(QGLCameraView, self).__init__( parent )
        self._wh = ( 0, 0 ) # canvas wh
        self._rc = ( 1, 1 ) # ros and cols of cameras to display

        self._subwindow_sz = ( 0, 0 )

        self.cam_list = []

        self.centroid_list = []
        self.stride_list = []
        self._strider = [] # but around here, he's known as Strider.

    def initializeGL( self ):
        GL.glClearColor( 0.0, 0.0, 0.0, 1.0 )

    def resizeGL( self, width, height ):
        self._wh = ( width, height )
        # compute subwindow dimentions
        rows, cols = self._rc
        sub_w = width / cols
        sub_h = height / rows
        self._subwindow_sz = ( sub_w, sub_h )

    def paintGL( self ):
        """ Draw the cameras """
        rows, cols = self._rc
        w, h = self._subwindow_sz

        cam_idx = 0 # NOT cam Number, idx in cam_list
        for r in range( rows ):
            for c in range( cols ):
                # setup an Orthogonal Projection
                GL.glViewport( c*w, r*h, w, h )
                GL.glMatrixMode( GL.GL_PROJECTION )
                GL.glLoadIdentity()

                # ToDo: draw an image - texture on a quad in BG?

                # Draw Roids
                sin, sout = self.strider[ cam_idx ]
                _in, _out = self.stride_list[ sin ], self.stride_list[ sout ]
                for det in self.centroid_list[_in:_out]:
                    x, y, rad = det
                    self._drawCircle( x, y, rad )

                # Draw reticule


    def _drawCircle( self, x, y, r ):
        """ Generateed circle code"""
        glBegin( GL_POLYGON )
        px = x + (r *  1.000)
        py = y + (r *  0.000)
        GL.glVertex2f( px, py )
        px = x + (r *  0.866)
        py = y + (r *  0.500)
        GL.glVertex2f( px, py )
        px = x + (r *  0.500)
        py = y + (r *  0.866)
        GL.glVertex2f( px, py )
        px = x + (r *  0.000)
        py = y + (r *  1.000)
        GL.glVertex2f( px, py )
        px = x + (r * -0.500)
        py = y + (r *  0.866)
        GL.glVertex2f( px, py )
        px = x + (r * -0.866)
        py = y + (r *  0.500)
        GL.glVertex2f( px, py )
        px = x + (r * -1.000)
        py = y + (r *  0.000)
        GL.glVertex2f( px, py )
        px = x + (r * -0.866)
        py = y + (r * -0.500)
        GL.glVertex2f( px, py )
        px = x + (r * -0.500)
        py = y + (r * -0.866)
        GL.glVertex2f( px, py )
        px = x + (r * -0.000)
        py = y + (r * -1.000)
        GL.glVertex2f( px, py )
        px = x + (r *  0.500)
        py = y + (r * -0.866)
        GL.glVertex2f( px, py )
        px = x + (r *  0.866)
        py = y + (r * -0.500)
        GL.glVertex2f( px, py )
        glEnd()

    def _camlistChanged( self ):
        num_cams = len( self.cam_list )
        self._rc = self.genDimsSquare( num_cams )

    def _marshelStrides( self ):
        self._strider = []
        num_cams = len( self.stride_list ) - 1
        for _in, _out in zip( range(0,num_cams), range(1,num_cams+1) ):
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
