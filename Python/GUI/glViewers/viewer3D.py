"""
    A 3D scene viewer,  This is just "Hello World".  Need a real one.
"""
import logging
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
from OpenGL import GL, GLU, GLUT


class QGLView( QtOpenGL.QGLWidget ):
    def __init__(self, parent=None):
        super().__init__( parent )
        self._frame_counter = QtCore.QElapsedTimer()
        self._wh = ( 0, 0 )# hopefully get this on first resize
        self.fps = 1
        self.shape1 = None

        self.x_rot_speed = 4
        self.x_shape_rot = 0
        self.y_rot_speed = 2
        self.y_shape_rot = 0
        self.z_rot_speed = 1
        self.z_shape_rot = 0

        timer = QtCore.QTimer( self)
        timer.timeout.connect( self.advance )
        timer.start( 10 ) #ms
        self._frame_counter.restart()

    def initializeGL( self ):
        """Set up the rendering context, define display lists etc."""
        GL.glEnable( GL.GL_DEPTH_TEST )
        #GL.glEnable( GL.GL_LIGHTING )
        #GL.glEnable( GL.GL_LIGHT0 )
        #GL.glLight( GL.GL_LIGHT0, GL.GL_POSITION, [5., 5., -3.] )
        self.shape1 = self.make_shape()
        GL.glEnable( GL.GL_NORMALIZE )
        GL.glClearColor( 0.0, 0.0, 0.0, 1.0 )

    def paintGL(self):
        """ Draw the scene """
        fps = 1000./ (float( self._frame_counter.restart() ) + 1e-6)
        if( fps > 150. or fps < 0.1):
            fps = self.fps
        self.fps = fps
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glPushMatrix()
        self.draw_shape(self.shape1, -1.0, -1.0, 0.0, (self.x_shape_rot, self.y_shape_rot, self.z_shape_rot))
        GL.glPopMatrix()
        self.renderText( 5, 10, "{:3.2f} fps".format( self.fps ) )


    def resizeGL(self, width, height):
        """ Setup viewport projection """
        side = min(width, height)
        if side < 0:
            return
        self._wh = ( width, height )
        # Constant aspect
        GL.glViewport(int((width - side) / 2), int((height - side) / 2), side, side)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glFrustum(-1.2, +1.2, -1.2, 1.2, 6.0, 70.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslated(0.0, 0.0, -20.0)

    def set_x_rot_speed(self, speed):
        self.x_rot_speed = speed
        self.updateGL()

    def set_y_rot_speed(self, speed):
        self.y_rot_speed = speed
        self.updateGL()

    def set_z_rot_speed(self, speed):
        self.z_rot_speed = speed
        self.updateGL()

    def advance(self):
        """Used in timer to actually rotate the shape."""
        self.x_shape_rot += self.x_rot_speed
        self.x_shape_rot %= 360
        self.y_shape_rot += self.y_rot_speed
        self.y_shape_rot %= 360
        self.z_shape_rot += self.z_rot_speed
        self.z_shape_rot %= 360
        self.updateGL()

    def make_shape(self):
        """Helper to create the shape and return list of resources."""
        list = GL.glGenLists(1)
        GL.glNewList(list, GL.GL_COMPILE)

        GL.glNormal3d(0.0, 0.0, 0.0)

        # Vertices
        a = ( 1, -1, -1),
        b = ( 1,  1, -1),
        c = (-1,  1, -1),
        d = (-1, -1, -1),
        e = ( 1, -1,  1),
        f = ( 1,  1,  1),
        g = (-1, -1,  1),
        h = (-1,  1,  1)

        edges = [
            (a, b), (a, d), (a, e),
            (c, b), (c, d), (c, h),
            (g, d), (g, e), (g, h),
            (f, b), (f, e), (f, h)
        ]

        GL.glBegin(GL.GL_LINES)
        for edge in edges:
            GL.glVertex3fv(edge[0])
            GL.glVertex3fv(edge[1])
        GL.glEnd()

        GL.glEndList()

        return list

    def draw_shape(self, shape, dx, dy, dz, rotation):
        """Helper to translate, rotate and draw the shape."""
        GL.glPushMatrix()
        GL.glTranslated(dx, dy, dz)
        GL.glRotated(rotation[0], 1.0, 0.0, 0.0)
        GL.glRotated(rotation[1], 0.0, 1.0, 0.0)
        GL.glRotated(rotation[2], 0.0, 0.0, 1.0)
        GL.glCallList(shape)
        GL.glPopMatrix()