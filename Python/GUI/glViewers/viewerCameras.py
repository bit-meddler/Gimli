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

from Core.math3D import genOrthoProjectionPlains, FLOAT_T

SQUARES = [ x ** 2 for x in range( 9 ) ]

class Shaders( object ):
    dot_vtx_src = """
    # version 330 core

    layout( location=0 ) in vec2 a_position ;
    
    uniform mat4 u_projection ;
    
    void main() {
        gl_Position = u_projection * vec4( position, 0.0, 1.0 ) ;
    }
    """
    dot_frg_src = """
    # version 330 core

    out vec4 color ;

    void main() {
        color = vec4( 0.0, 1.0, 0.0, 1.0 ) ;
    }
    """

class QGLCameraView( QtWidgets.QOpenGLWidget ):

    DEFAULT_ZOOM = 1.05
    TRUCK_SCALE  = 0.01

    def __init__(self, parent=None ):
        super(QGLCameraView, self).__init__( parent )
        # canvas size
        self._wh = (self.geometry().width(), self.geometry().height())
        self._rc = ( 1, 1 ) # ros and cols of cameras to display

        self._subwindow_sz = ( 0, 0 )

        self.cam_list = []
        self.num_cams = 0

        # Global Camera settings
        self.clip_nr = -100.0
        self.clip_far = 100.0

        # per camera settings for OrthoGraphic Projection
        self._ortho_navigation = [] # should be in sceneMan

        # internals for camera movement
        self._panning = False
        self._zooming = False
        self._move_start = None
        self._navigate = None

        # OK, for now assume we display all camera, not a selected sub-set
        self.stride_list = []
        # helper for s_in and s_out indexes
        self._strider = [] # but around here, he's known as Strider.

        # OpenGL attrs
        self.shader = None
        self.shader_attr_locs = {}
        self._proj_loc = -1

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
            ], dtype=FLOAT_T ) # 16 Elems, 128 Bytes
        self._reticule *= 0.99 # just smaller than NDC limits?
        self.vbo = None
        self.has_data = False

    def acceptNewData( self, dets, strides, ids ):
        my_dets = np.asarray( dets[:,:2], dtype=FLOAT_T ) # ignore r for now
        self.stride_list = np.asarray( strides, dtype=np.int32 )
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

        self.shader_attr_locs[ "a_position" ] = 0
        GL.glEnableVertexAttribArray( self.shader_attr_locs[ "a_position" ] )
        GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ "a_position" ], "a_position" )

        self.shader.link()
        self.shader.bind()

        # Get a buffer
        self.vbo = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self.vbo )

        # configure Attrib
        GL.glVertexAttribPointer( 0, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p( 0 ) )

        # Setup uniform for Camera navigation
        self._proj_loc = self.shader.uniformLocation( "u_projection" )

        self.shader.release()

        # Misc
        GL.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )


    def resizeGL( self, width, height ):
        self._wh = ( width, height )
        # compute subwindow dimentions
        rows, cols = self._rc
        sub_w = int( width / cols )
        sub_h = int( height / rows )
        self._subwindow_sz = ( sub_w, sub_h )
        for view in self._ortho_navigation:
            x, y = view["locus"]
            view["P"] = self.projectionFromNav( view["zoom"], view["width"], x, y )

    def paintGL( self ):
        """ Draw the cameras """
        if( not self.has_data ):
            return

        # Enable a painter, but switch to Native Painting immediatly
        # painter = QtGui.QPainter( self )
        # painter.setPen( QtCore.Qt.green )
        # painter.setFont( QtGui.QFont( "Helvetica", 8 ) )
        # painter.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing )
        # painter.begin( self )
        # painter.beginNativePainting()

        # clear
        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        rows, cols = self._rc
        w, h = self._subwindow_sz
        hw = int( w / 2 )
        height = self._wh[1]
        overlays = []
        # get the right buffer ? - guess not
        #GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self.vbo )

        # set dot size
        GL.glPointSize( 2 )
        GL.glEnable( GL.GL_POINT_SMOOTH )

        cam_idx = 0 # NOT cam Number, idx in cam_list
        for r in range( rows-1, -1, -1 ):
            for c in range( cols ):
                x, y =  c*w, r*h

                # setup an Orthogonal Projection
                # Todo: correct aspect ratio.  What do we do with non-square sensors? /=(1920/2) -= [1,1280/1920] - Do in arbiter

                self.shader.bind()

                GL.glUniformMatrix4fv( self._proj_loc, 1, GL.GL_TRUE, self._ortho_navigation[ cam_idx ][ "P" ] )

                GL.glViewport( x, y, w, h )

                # ToDo: Far in the future, draw an image - texture on a quad in BG?

                # Draw Roids
                sin, sout = self._strider[ cam_idx ]
                idx_in    = self.stride_list[ sin ]
                num_dets  = self.stride_list[ sout ] - idx_in
                idx_in += 16 # Skip reticlue

                if( num_dets > 0 ):
                    GL.glDrawArrays( GL.GL_POINTS, idx_in, num_dets )

                # Draw reticule
                GL.glDrawArrays( GL.GL_LINES, 0, 16 )

                self.shader.release()

                # Kills redrawws?
                overlays.append( ( x+hw-45, height-y-5, "Camera {}".format( cam_idx+1 ) ) )

                # Done?
                cam_idx += 1
                if( cam_idx >= self.num_cams ):
                    break

        # # Draw overlay text
        # painter.endNativePainting()
        # for x, y, text in overlays:
        #     painter.drawText( x, y, text )
        # painter.end()

    def _camFromXY( self, x, y ):
        rows, cols = self._rc
        w, h = self._subwindow_sz
        #y = y - self._wh[ 1 ]  # top left to bottom left conversion
        c = x // w
        r = y // h
        idx = (cols * r) + c
        if (idx >= len( self.cam_list )):
            idx = -1
        return idx

    def wheelEvent( self, event ):
        x, y = event.x(), event.y()
        cam_idx = self._camFromXY( x, y )
        if( cam_idx < 0 ):
            return

        cam = self._ortho_navigation[ cam_idx ]

        wheel_delta = event.angleDelta().y()
        wheel_delta /= 100.

        if( wheel_delta > 0.0 ):
            cam["zoom"] *= self.DEFAULT_ZOOM

        elif( wheel_delta < 0.0 ):
            cam["zoom"] /= self.DEFAULT_ZOOM

        self.updateProjection( cam_idx )

    def mousePressEvent( self, event ):
        x, y = event.x(), event.y()
        cam_idx = self._camFromXY( x, y )
        if( cam_idx < 0 ):
            return

        buttons = event.buttons()

        pressed_left = bool( buttons & QtCore.Qt.LeftButton )
        pressed_right = bool( buttons & QtCore.Qt.RightButton )
        pressed_mid = bool( buttons & QtCore.Qt.MiddleButton )

        if ((pressed_left and pressed_right) or pressed_mid):
            # trucking
            self._panning = True
            self._move_start = event.pos()
            self._navigate = cam_idx

        elif (pressed_right):
            # Zooming
            self._zooming = True
            self._move_start = event.pos()
            self._navigate = cam_idx

    def mouseReleaseEvent( self, event ):
        update_camera = False

        if( self._panning ):
            # complete the pan
            update_camera = True
            self._panning = False

        elif( self._zooming ):
            # complete the Zoom
            update_camera = True
            self._zooming = False

        if( update_camera ):
            self.updateProjection( self._navigate )

        self._navigate = None

    def mouseMoveEvent( self, event ):
        update_camera = False

        if( self._panning or self._zooming ):
            # get the positional delta
            hz = event.x() - self._move_start.x()
            vt = event.y() - self._move_start.y()
            self._move_start = event.pos()


        if( self._panning ):
            cam = self._ortho_navigation[ self._navigate ]
            cam["locus"][0] += (hz * cam["zoom"]) * self.TRUCK_SCALE
            cam["locus"][1] += (vt * cam["zoom"]) * self.TRUCK_SCALE

            update_camera = True


        elif( self._zooming ):
            cam = self._ortho_navigation[ self._navigate ]
            if( vt > 0.0 ):
                cam["zoom"] *= self.DEFAULT_ZOOM
            elif( vt < 0.0 ):
                cam["zoom"] /= self.DEFAULT_ZOOM

            update_camera = True


        if( update_camera ):
            self.updateProjection( self._navigate )


    def mouseDoubleClickEvent( self, event ):
        x, y = event.x(), event.y()
        cam_idx = self._camFromXY( x, y )
        if( cam_idx < 0 ):
            return

        if( event.modifiers() & QtCore.Qt.AltModifier ):

            # Alt Double Click resets the camera
            cam = self._ortho_navigation[ cam_idx ]
            cam[ "zoom" ]  = 1.0
            cam[ "width" ] = 2.0
            cam[ "locus" ] = [ 0.0, 0.0 ]

            self.updateProjection( cam_idx )
        else:
            print( self._ortho_navigation[ cam_idx ] )


    def updateProjection( self, cam_idx ):
        cam = self._ortho_navigation[ cam_idx ]
        cam[ "P" ] = self.projectionFromNav( cam[ "zoom" ], cam[ "width" ], cam["locus"][0], cam["locus"][1] )
        self.update()

    def _camlistChanged( self ):
        self.num_cams = len( self.cam_list )
        self._rc = self.genDimsSquare( self.num_cams )
        self._marshelStrides()

        # Hack: This should be a sceneMan thing.
        # Populate cameras with Ortho Navigation
        self._ortho_navigation = []
        for i in range( self.num_cams ):
            self._ortho_navigation.append( { "zoom"  : 1.0,
                                             "width" : 3.0,
                                             "locus" : [ 0.0, 0.0 ],
                                             "P"     : np.eye( 4, dtype=FLOAT_T )} )

    def projectionFromNav( self, zoom, width, orig_x, orig_y  ):
        w, h = self._subwindow_sz
        span = width *zoom
        extent = span / (w/h)

        o_l = orig_x + span
        o_r = orig_x - span
        o_t = orig_y + extent
        o_b = orig_y - extent

        return genOrthoProjectionPlains( o_l, o_r, o_b, o_t, self.clip_nr, self.clip_far )

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
