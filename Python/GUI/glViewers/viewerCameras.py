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

from Core.math3D import genOrthoProjectionPlans, FLOAT_T, ID_T, TWO_PI
import Core.labelling as lid

from GUI import getStdIcon, Nodes, ROLE_INTERNAL_ID, ROLE_NUMROIDS, ROLE_TYPEINFO

SQUARES = [ x ** 2 for x in range( 9 ) ]

class Shaders( object ):
    """
    Conveniane to hold Shaders used in the cameraviewer.
    ToDo: Something more elegant for this when the shaders are working properly.
    """
    dot_vtx_src = """
    # version 330 core

    layout( location=0 ) in vec3 a_position ;
    layout( location=1 ) in int  a_id ;
    
    uniform mat4 u_projection ;
    
    out vec3 v_colour ;
    
    void main() {
        gl_Position  = u_projection * vec4( a_position.x, a_position.y, 0.0, 1.0 ) ;
        gl_PointSize = a_position.z * 2.0 ;
        if( a_id < 0 ) {
            v_colour = vec3( 1.0, 1.0, 1.0 ) ;
        } else {
            v_colour = vec3( 0.0, 1.0, 0.0 ) ;
        }
    }
    """
    # ISSUE #9
    dot_vtx2_src = """
    # version 330 core

    layout( location=0 ) in vec3 a_position ;
    layout( location=1 ) in int  a_id ;
    
    uniform mat4 u_projection ;
    
    // colour tables
    uniform vec3 u_cols[{num_cols}] ;
    uniform vec3 u_sids[{num_sids}] ;
    
    out vec3 v_colour ;
    
    void main() {{
        gl_Position  = u_projection * vec4( a_position.x, a_position.y, 0.0, 1.0 ) ;
        gl_PointSize = a_position.z * 2.0 ;
        if( a_id < 0 ) {{
            // frozen or a sid
            if( a_id <= {sid_bound} ) {{
                v_colour = u_sids[ abs( a_id + {sid_conv} ) ] ;
            }} else {{
                v_colour = vec3( 0.0, 0.0, 1.0 ) ;
            }}
        }} else {{
            v_colour = u_cols[ a_id ] ;
        }}
    }}
    """ # It's supposed to work like this...

    dot_vtx_src3 = """
    # version 330 core

    layout( location=0 ) in vec3 a_position ;
    layout( location=1 ) in int  a_id ;
    
    uniform mat4 u_projection ;
    
    out vec3 v_colour ;
    
    void main() {
        gl_Position  = u_projection * vec4( a_position.x, a_position.y, 0.0, 1.0 ) ;
        gl_PointSize = a_position.z * 2.0 ;
        vec3 sel_col ;
        
        if( a_id <= 0 ) {
            // frozen or a sid
            if( a_id < -2147479551 ) {
                int s_id = abs( a_id + 2147479552 ) ;
                
                if(        s_id == 0 ) {
                    sel_col = vec3( 1.0, 1.0, 1.0 ) ;
                } else if( s_id == 1 ) {
                    sel_col = vec3( 1.0, 0.0, 0.0 ) ;
                } else if( s_id == 2 ) {
                    sel_col = vec3( 0.0, 1.0, 0.0 ) ;
                } else if( s_id == 3 ) {
                    sel_col = vec3( 0.0, 0.0, 1.0 ) ;
                }
            } else {
                sel_col = vec3( 0.0, 0.0, 1.0 ) ; // <-------------------------
            }
        } else {
            // A label
            sel_col = vec3( 1.0, 1.0, 1.0 ) ;
            
            if(        a_id == 1 ) {
                sel_col = vec3( 1.0, 0.0, 0.0 ) ;
            } else if( a_id == 2 ) {
                sel_col = vec3( 1.0, 1.0, 0.0 ) ;
            } else if( a_id == 3 ) {
                sel_col = vec3( 0.0, 1.0, 0.0 ) ;
            } else if( a_id == 4 ) {
                sel_col = vec3( 0.0, 1.0, 1.0 ) ;
            } else if( a_id == 5 ) {
                sel_col = vec3( 0.0, 0.0, 1.0 ) ;
            }
        }
        v_colour = sel_col ;
    }
    """ # Nasty Hack - Hard Coded Colours
    dot_frg_src = """
    # version 330 core
    
    in vec3 v_colour ;
    
    out vec4 color ;

    void main() {
        color = vec4( v_colour, 1.0 ) ;
    }
    """
    # ISSUE #8
    dot_geo_src = """
    #version 330 core

    layout (points) in ;
    layout (line_strip, max_vertices = 12) out;

    void circle( vec4 position, float radius ) {
        gl_Position = position + (vec4(1.0, 0.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.8660254037844387, 0.49999999999999994, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.5000000000000001, 0.8660254037844386, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.0, 1.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.4999999999999998, 0.8660254037844387, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.8660254037844385, 0.5000000000000003, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-1.0, 0.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.8660254037844388, -0.4999999999999997, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.5000000000000004, -0.8660254037844385, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.0, -1.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.49999999999999933, -0.866025403784439, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.8660254037844384, -0.5000000000000004, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        EndPrimitive() ;
    }

    void main() {
        circle( gl_in.gl_Position, gl_PointSize ) ;
    }
    """
    @staticmethod
    def genGeoSdr( divisions=12 ):
        # ISSUE #8
        ret = """
    #version 330 core
    
    layout (points) in ;
    layout (line_strip, max_vertices = {}) out;
    
    void circle( vec4 position, float radius ) {{
        """.format( divisions )

        step = TWO_PI / divisions
        for i in range( divisions ):
            x = np.cos( i * step )
            y = np.sin( i * step )
            x = 0.0 if np.abs(x) < 1.0e-8 else x
            y = 0.0 if np.abs(y) < 1.0e-8 else y
            ret += """gl_Position = position + (vec4({x:.5f}, {y:.5f}, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        """.format( x=x, y=y )

        ret += """EndPrimitive() ;
    }
    
    void main() {    
        circle( gl_in[0].gl_Position, gl_in[0].gl_PointSize ) ;
    }  
    """

        return ret


class QGLCameraPane( QtWidgets.QOpenGLWidget ):
    """
    A viewer for "Looking through" any selected MoCap Camera, or seeing a multi-view of several cameras at once.

    ToDo: Store camera Zoom, Width and Locus in the Scene Model - don't cache here
    ToDo: Current multi-viewport method is probably wrong.  Can we do this better?
    ToDo: Acumulate wand "Ribbons" when calibrating to visualize coverage of each camera's FoV.
    ToDo: Future cameras may be able to return images.  Display them on a texture in the BG.
    ToDo: With a sucessful camera calibration, we will have radial distortion data.  Use it.
    ToDo: With both above, unwarp the texture too!
    """
    # Camera view defaults
    ZOOM_SCALE    = 1.075
    TRUCK_SCALE   = 0.01
    DEFAULT_WIDTH = 2.5
    DEFAULT_ZOOM  = 1.075

    def __init__(self, parent=None ):
        super(QGLCameraPane, self).__init__( parent )

        # Setup the Canvas / Format
        format = QtGui.QSurfaceFormat.defaultFormat()
        format.setSamples( 4 )
        format.setRenderableType( QtGui.QSurfaceFormat.OpenGL )
        format.setProfile( QtGui.QSurfaceFormat.CoreProfile )

        self.setFormat( format )

        # canvas size
        self._wh = (self.geometry().width(), self.geometry().height())
        self._rc = (-1, -1) # ros and cols of cameras to display

        self._subwindow_sz = (0, 0)

        self._camera_group = None # reference to all cameras
        self.cam_list = []
        self.num_cams = 0
        self.draw_lead = False
        # reference to Controls in the status bar
        self._lead_button  = None
        self._label_button = None

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
        # In the future there may be other reticules so bound non-square sensors
        self._reticule = np.array(
            [ [-1.0,  1.0, 0.0], [ 1.0,   1.0,  0.0], # Box
              [ 1.0,  1.0, 0.0], [ 1.0,  -1.0,  0.0],
              [ 1.0, -1.0, 0.0], [-1.0,  -1.0,  0.0],
              [-1.0, -1.0, 0.0], [-1.0,   1.0,  0.0],
              # ticks
              [-1.0,  0.0, 0.0], [-0.95,  0.0,  0.0],
              [ 1.0,  0.0, 0.0], [ 0.95,  0.0,  0.0],
              [ 0.0, -1.0, 0.0], [ 0.0,  -0.95, 0.0],
              [ 0.0,  1.0, 0.0], [ 0.0,   0.95, 0.0],
              ], dtype=FLOAT_T ) # 16 Elems, 128 Bytes
        # ISSUE #9
        self._reticule_ids = np.array(
            [ lid.SID_WHITE,     lid.SID_WHITE,
              lid.SID_WHITE,     lid.SID_WHITE,
              lid.SID_WHITE,     lid.SID_WHITE,
              lid.SID_WHITE,     lid.SID_WHITE,

              lid.SID_WHITE,     lid.SID_RED,
              lid.SID_WHITE,     lid.SID_RED,
              lid.SID_WHITE,     lid.SID_GREEN,
              lid.SID_WHITE,     lid.SID_GREEN,
              ], dtype=ID_T )

        self._reticule_sz = 16
        self._reticule_block_sz = len( self._reticule )

        # prep GL Buffer Objects
        self._vao_cameras = None
        self._vbo_dets = None
        self._vbo_reticules = None # todo
        self._vbo_ids = None

        # early draw guard
        self._gl_ready = False

    def initializeGL( self ):
        """
        Setup penGL Render area and shader programs.
        """
        GL.glClearColor( 0.0, 0.0, 0.0, 1.0 )

        # ISSUE #9
        # prepare colours
        self._cols_sid = np.asarray( lid.SID_COLOURS, dtype=FLOAT_T )

        id_cols = [ [1.0, 1.0, 1.0] ]
        id_cols.extend( lid.WAND_COLOURS )
        self._cols_ids = np.asarray( id_cols, dtype=FLOAT_T )

        # ISSUE #9
        # compose the shader program
        dot_vtx_src = Shaders.dot_vtx2_src.format( num_cols=len( self._cols_ids ),
                                                   num_sids=len( self._cols_sid ), sid_bound=lid.SID_BASE+1, sid_conv=lid.SID_CONV )

        # Setup Dot shader
        self.shader = QtGui.QOpenGLShaderProgram( self.context() )

        #add_ok = self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, dot_vtx_src )
        add_ok = self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, Shaders.dot_vtx_src3  )
        if (not add_ok):
            print( "Add Error", self.shader.log() )
            exit()

        add_ok = self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, Shaders.dot_frg_src )
        if (not add_ok):
            print( "Add Error", self.shader.log() )
            exit()

        # ISSUE #8
        # add_ok = self.shader.addShaderFromSourceCode( QtGui.QOpenGLShader.Geometry, Shaders.dot_geo_src )
        if (not add_ok):
            print( "Add Error", self.shader.log() )
            exit()

        self.shader_attr_locs[ "a_position" ] = 0
        GL.glEnableVertexAttribArray( self.shader_attr_locs[ "a_position" ] )
        GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ "a_position" ], "a_position" )

        self.shader_attr_locs[ "a_id" ] = 1
        GL.glEnableVertexAttribArray( self.shader_attr_locs[ "a_id" ] )
        GL.glBindAttribLocation( self.shader.programId(), self.shader_attr_locs[ "a_id" ], "a_id" )

        link_ok = self.shader.link()
        if( not link_ok ):
            print( "Error", self.shader.log() )
            exit()
        self.shader.bind()

        # camera VAO
        self._vao_cameras = GL.glGenVertexArrays( 1 )

        # Buffers

        # configure position Attrib
        self._vbo_dets = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self._vbo_dets )
        GL.glVertexAttribPointer( self.shader_attr_locs[ "a_position" ], 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p( 0 ) )

        # the id attrib
        self._vbo_ids = GL.glGenBuffers( 1 )
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self._vbo_ids )
        GL.glVertexAttribPointer( self.shader_attr_locs[ "a_id" ], 1, GL.GL_INT, GL.GL_FALSE, 0, ctypes.c_void_p( 0 ) )

        # Setup uniform for Camera navigation
        self._proj_loc = self.shader.uniformLocation( "u_projection" )

        # ISSUE #9
        # set up colour uniforms
        self._cols_loc = self.shader.uniformLocation( "u_cols[0]" )
        self._sids_loc = self.shader.uniformLocation( "u_sids[0]" )

        # ISSUE #9
        # load colour uniforms
        print( self._cols_ids )
        print( self._cols_sid )
        #GL.glUniform3fv( self._cols_loc, len( self._cols_ids ), self._cols_ids )
        #GL.glUniform3fv( self._sids_loc, len( self._cols_sid ), self._cols_sid )

        self.shader.release()

        # Misc
        #GL.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )
        # ISSUE #8
        #GL.glEnable( GL.GL_PROGRAM_POINT_SIZE )

        # HACK!
        # dummy data so reticules are drawn
        self.acceptNewData( np.array([]).reshape(0,3), np.zeros( (11,) ), np.zeros( (10,) ) )

        self._gl_ready = True

    # OpenGL funtions ----------------------------------------------------------
    def resizeGL( self, width, height ):
        """
        Overload QOpenGLWidget.resizeGL.  Recompute the size of th esub-windows and update their 'cameras'
        Args:
            width: (int) New Canvas width
            height: (int) New Canvas height

        Returns:

        """
        self._wh = ( width, height )
        rows, cols = self._rc
        if( rows < 0 or cols < 0):
            return
        # compute subwindow dimentions
        sub_w = int( width / cols )
        sub_h = int( height / rows )
        self._subwindow_sz = ( sub_w, sub_h )
        for cam in self.cam_list:
            self.updateProjection( cam )

    def paintGL( self ):
        """
        Draw selected cameras, and display dets.
        """
        if( not self._gl_ready ):
            return

        # clear
        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        rows, cols = self._rc
        w, h = self._subwindow_sz

        # for text drawing
        text_x = int( w / 2 ) - 45
        text_y = self._wh[ 1 ] - 5
        overlays = []
        # get the right buffer ? - guess not
        #GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self._vbo_dets )

        # # ISSUE #8 - set dot size
        GL.glPointSize( 2 )
        #GL.glEnable( GL.GL_POINT_SMOOTH )

        self.shader.bind()

        if( self.draw_lead ):
            cam_idx = self.cam_list[-1]
        else:
            cam_idx = 0 # NOT cam Number, idx in cam_list

        for r in range( rows-1, -1, -1 ):
            for c in range( cols ):
                x, y =  c*w, r*h

                # setup an Orthogonal Projection
                GL.glUniformMatrix4fv( self._proj_loc, 1, GL.GL_TRUE, self._ortho_navigation[ cam_idx ][ "P" ] )

                GL.glViewport( x, y, w, h )

                # Draw Roids
                sin, sout = self._strider[ cam_idx ]
                idx_in    = self.stride_list[ sin ]
                num_dets  = self.stride_list[ sout ] - idx_in
                idx_in   += self._reticule_block_sz # Skip reticule

                if( num_dets > 0 ):
                    GL.glDrawArrays( GL.GL_POINTS, idx_in, num_dets )

                # Draw reticule
                GL.glDrawArrays( GL.GL_LINES, 0, self._reticule_sz )

                # Queue HUD text
                overlays.append( ( text_x + x, text_y - y, "Camera {}".format( self.cam_list[ cam_idx ]  ) ) )

                # Done?
                cam_idx += 1
                if( cam_idx >= self.num_cams ):
                    break

        self.shader.release()

        # Draw overlay text - Seems to kill the 3D renders?
        # painter = QtGui.QPainter( self )
        # painter.setPen( QtCore.Qt.green )
        # painter.setFont( QtGui.QFont( "Helvetica", 8 ) )
        # painter.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing )
        # painter.begin( self )
        # for x, y, text in overlays:
        #     painter.drawText( x, y, text )
        # painter.end()

    # Qt Functions -------------------------------------------------------------
    def wheelEvent( self, event ):
        """
        Overloaded QWidget function - Zoom in or out the display of the camera the cursor is in
        Args:
            event: (QMouseEvent?) The mouse event
        """
        x, y = event.x(), event.y()
        cam_idx = self._camFromXY( x, y )
        if( cam_idx < 0 ):
            return

        cam = self._ortho_navigation[ cam_idx ]

        wheel_delta = event.angleDelta().y()
        wheel_delta /= 100.

        if( wheel_delta < 0.0 ):
            cam["zoom"] *= self.ZOOM_SCALE

        elif( wheel_delta > 0.0 ):
            cam["zoom"] /= self.ZOOM_SCALE

        self.updateProjection( cam_idx )

    def mousePressEvent( self, event ):
        """
        Overloaded QWidget function - Truck or Zoom the Camera's view
        Args:
            event: (QMouseEvent?) The mouse event
        """
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
        """
        Overloaded QWidget function - Complete the interaction
        Args:
            event: (QMouseEvent?) The mouse event
        """
        update_camera = False

        if( self._panning ):
            # complete the pan
            update_camera = True
            self._panning = False

        elif( self._zooming ):
            # complete the Zoom
            update_camera = True
            self._zooming = False

        if( update_camera and self._navigate is not None ):
            self.updateProjection( self._navigate )

        self._navigate = None

    def mouseMoveEvent( self, event ):
        """
        Overloaded QWidget function - Update the camera's projection if needed
        Args:
            event: (QMouseEvent?) The mouse event
        """
        update_camera = False

        if( self._panning or self._zooming ):
            # get the positional delta
            hz = event.x() - self._move_start.x()
            vt = event.y() - self._move_start.y()
            self._move_start = event.pos()


        if( self._panning and self._navigate is not None ):
            cam = self._ortho_navigation[ self._navigate ]
            cam["locus"][0] += (hz * cam["zoom"]) * self.TRUCK_SCALE
            cam["locus"][1] += (vt * cam["zoom"]) * self.TRUCK_SCALE

            update_camera = True


        elif( self._zooming and self._navigate is not None ):
            cam = self._ortho_navigation[ self._navigate ]
            if( vt > 0.0 ):
                cam["zoom"] *= self.ZOOM_SCALE
            elif( vt < 0.0 ):
                cam["zoom"] /= self.ZOOM_SCALE

            update_camera = True


        if( update_camera ):
            self.updateProjection( self._navigate )

    def mouseDoubleClickEvent( self, event ):
        """ DEBUG
        Overloaded QWidget function - Shortcut to reset given camera's projection.
        For Debug will print out the camera's projection matrix
        Args:
            event: (QMouseEvent?) The mouse event
        """
        x, y = event.x(), event.y()
        cam_idx = self._camFromXY( x, y )
        if( cam_idx < 0 ):
            return

        if( event.modifiers() & QtCore.Qt.AltModifier ):

            # Alt Double Click resets the camera
            cam = self._ortho_navigation[ cam_idx ]
            cam[ "zoom" ]  = self.DEFAULT_ZOOM
            cam[ "width" ] = self.DEFAULT_WIDTH
            cam[ "locus" ] = [ 0.0, 0.0 ]

            self.updateProjection( cam_idx )
        else:
            #print( cam_idx, self._ortho_navigation[ cam_idx ] )
            self._lead_button.toggle()
            if( self.draw_lead ):
                # clicked camera is lead
                self.reorderCamList( cam_idx )
            else:
                # back to normal
                self.reorderCamList()

    def minimumSizeHint( self ):
        """
        Overloaded QWidget function - minimum usable space
        """
        return QtCore.QSize( 640, 480 )


    # functional ---------------------------------------------------------------
    def acceptNewData( self, dets, strides, ids ):
        """
        When a new "Data Frame" comes in, put the detections on the VBO.  If Labelling enabled, attempt this and put the
        resulting ID data on it's VBO to colour code the dets.

        Args:
            dets: (ndarray) Nx3 Array of detections, [x,y,r]
            strides: ndarray) N+1 strides array
            ids: (ndarray) Nx1 Array of IDs

        Emits:
            self.update(): requests a redraw
        """
        self.stride_list = np.asarray( strides, dtype=np.int32 )

        # conform dets
        my_dets = np.asarray( dets, dtype=FLOAT_T )
        packed_data = np.concatenate( (self._reticule, my_dets) )

        # load to VBO
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self._vbo_dets )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, packed_data.nbytes, packed_data, GL.GL_STATIC_DRAW )

        # get ids
        if( ids is None ):
            my_ids = np.full( len( my_dets ), 0, dtype=np.int32 )
        else:
            my_ids = np.asarray( ids, dtype=np.int32 )

        # attempt to label
        if( self._label_button.isChecked() ):
            for i, (s_in, s_out) in enumerate( zip( self.stride_list[:-1], self.stride_list[1:] ) ):
                labels, score = lid.labelWand( my_dets, s_in, s_out, False )
                if( labels is not None ):
                    my_ids[s_in:s_out] = labels
                    #print( "labelled wand in camera {}".format(i) )

        packed_data2 = np.concatenate( (self._reticule_ids, my_ids) )

        #print( packed_data2 )

        # load to VBO
        GL.glBindBuffer( GL.GL_ARRAY_BUFFER, self._vbo_ids )
        GL.glBufferData( GL.GL_ARRAY_BUFFER, packed_data2.nbytes, packed_data2, GL.GL_STATIC_DRAW )

        # call redraw
        self.update()

    def updateProjection( self, cam_idx ):
        """
        Compute the given camera's projection matrix based on current sub-window size and it's view paramiters.
        Args:
            cam_idx: (int) Index of camera to update
        """
        if( cam_idx is None ):
            return
        cam = self._ortho_navigation[ cam_idx ]
        cam[ "P" ] = self.projectionFromNav( cam[ "zoom" ], cam[ "width" ], cam["locus"][0], cam["locus"][1] )
        self.update()

    def _camlistChanged( self ):
        """
        The internal camera list is controled by the shared selection model, for convenience we're only interested in
        the selected cameras.
        """
        self.num_cams = len( self.cam_list )
        self._rc = self.genDimsSquare( self.num_cams )

        self._marshelStrides()

        # Hack: This should be a sceneMan thing.
        self.resetAllCams()

        self.resizeGL( *self._wh ) # recalculate the sub windows & redraw

    def resetAllCams( self ):
        """
        Set all camera's views to the default and generate their Projection matrix
        """
        self._ortho_navigation = []
        for i in range( self.num_cams ):
            self._ortho_navigation.append( { "zoom"  : self.DEFAULT_ZOOM,
                                             "width" : self.DEFAULT_WIDTH,
                                             "locus" : [ 0.0, 0.0 ],
                                             "P"     : None } )
        for cam in self._ortho_navigation:
            cam[ "P" ] = self.projectionFromNav( cam[ "zoom" ], cam[ "width" ], cam[ "locus" ][ 0 ], cam[ "locus" ][ 1 ] )
        self.update()

    def projectionFromNav( self, zoom, width, orig_x, orig_y  ):
        """
        Create a Projection Matrix based on the current subwindow size and the parameters.

        Args:
            zoom: (float) Zoom factor
            width: (float) Horizontal FoV in NDCs
            orig_x: (float) "interest" X
            orig_y: (float) "interest" Y

        Returns:
            projection matrix (ndarray) 4x4 OpenGL Projection matrix
        """
        w, h = self._subwindow_sz
        if( w < 1 or h < 1 ):
            return np.eye( 4, dtype=FLOAT_T )

        span = width * zoom
        extent = span / (w/h)

        o_l = orig_x + span
        o_r = orig_x - span
        o_t = orig_y + extent
        o_b = orig_y - extent

        return genOrthoProjectionPlans( o_l, o_r, o_b, o_t, self.clip_nr, self.clip_far )

    def _marshelStrides( self ):
        """
        Precompute a stride list for the number of cameras we are displaying
        """
        self._strider = []
        for _in, _out in zip( range(0,self.num_cams), range(1,self.num_cams+1) ):
            self._strider.append( (_in,_out) )

    def reorderCamList( self, lead=None ):
        """
        As Cameras are added to or removed from the selection Queue the "lean" camera will change.  we need to keep
        track of this camera.
        Args:
            lead: (int) cam_id of the lead camera
        """
        self.cam_list = sorted( self.cam_list )
        if( lead is not None and lead in self.cam_list ):
            self.cam_list.remove( lead )
            self.cam_list.append( lead )

    def modeToggle( self ):
        """
        Toggle the view mode between Selected cameras or Lead camera only
        """
        self.draw_lead = bool( self._lead_button.isChecked() )
        width, height = self._wh
        if( self.draw_lead ):
            self._rc = self.genDimsSquare( 1 )
        else:
            self._rc = self.genDimsSquare( self.num_cams )
        self.resizeGL( width, height )

    def _camFromXY( self, x, y ):
        """
        From the x,y coordinates (in the space of th eWidget's canvas) find out the camera the coordinates are in.

        Args:
            x: (int) event coordinate
            y: (int) event coordinate

        Returns:
            idx: (int) index of camera under the coordinates, or -1
        """
        if (self.draw_lead):
            return self.cam_list[ -1 ]

        rows, cols = self._rc
        w, h = self._subwindow_sz
        #y = y - self._wh[ 1 ]  # top left to bottom left conversion
        c = x // w
        r = y // h
        idx = (cols * r) + c
        if (idx >= len( self.cam_list )):
            idx = -1
        return idx

    @staticmethod
    def genDimsSquare( num_cams ):
        """
        Determine the rows / cols needed to pack 'num_cams' views into to keep square.
        Args:
            num_cams: (int) number of cameras to arrange

        Returns:
            size: (tuple)
                rows: (int)
                cols: (int)
        """
        if( num_cams < 1 ):
            return (-1, -1)

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


class QGLCameraView( QtWidgets.QMainWindow ):
    """
    Container for the QGLWidget, gives us space for Toolbars, etc.
    """

    def __init__( self, parent, live=True ):
        """
        Setup the viewer
        Args:
            parent: (Q?) widget this widget is inside
            live: (bool) Live or Offline mode flag
        """
        super( QGLCameraView, self ).__init__()

        # selection Model and data Model
        self._select = None
        self._model  = None

        #live or offline
        self.live = live
        self._qgl_pane = QGLCameraPane( self )
        self._setupToolBar()
        self._qgl_pane._lead_button  = self.lead_mode
        self._qgl_pane._label_button = self.label_mode
        self.setCentralWidget( self._qgl_pane )

        self._qgl_pane.update()

    def setModels( self, item_model, selection_model ):
        """
        Once instanciated, all Gimli Editors and views need to get the shared  Model and Selection attached.
        Args:
            item_model: Main Application's Model
            selection_model: Main Application's Model
        """
        self._model = item_model
        self._model.dataChanged.connect( self.onDataChange )
        self._select = selection_model
        # the camera groups
        # todo: 'default' to all cameras in the group....
        self._qgl_pane._camera_group = item_model.groups[ Nodes.TYPE_GROUP_MOCAP ]

    def onDataChange( self, change_idx ):
        """
        Slot triggered when main application gets or selects a new frame
        Args:
            change_idx: (any) I can't remember, but it was a good idea at the tiem
        """
        self._qgl_pane.acceptNewData( self._model.dets_dets, self._model.dets_strides, None )

    def onSelectionChanged( self, _selected, _deselected ):
        """
        Slot triggered on selection changes.
        This updates the internal camera list of the GL viewer.
        Args:
            _selected:
            _deselected:
        """
        if( self._select is None ):
            return

        # walk selected and find cameras
        cam_list = []
        last_cam = -1
        for idx in self._select.selection().indexes():
            if( idx.data( role=ROLE_TYPEINFO ) == Nodes.TYPE_CAMERA_MC_PI ):
                cam = idx.data( role=ROLE_INTERNAL_ID )
                cam_list.append( cam )
                last_cam = cam

        self._qgl_pane.cam_list = cam_list
        self._qgl_pane.reorderCamList( lead=last_cam )
        self._qgl_pane._camlistChanged()

    def _setupToolBar( self ):
        """
        Setup the Toolbar.  Only enable wand detection in "live" mode.

        """
        toolbar = QtWidgets.QToolBar( "Camera view tools" )
        toolbar.setIconSize( QtCore.QSize( 16, 16 ) )
        toolbar.setMovable( False )
        self.addToolBar( toolbar )

        # Display Options
        self.lead_mode = QtWidgets.QToolButton( self )
        self.lead_mode.setIcon( getStdIcon( QtWidgets.QStyle.SP_ArrowUp ) )
        self.lead_mode.setStatusTip( "Focus Lead" )
        self.lead_mode.setToolTip( "Focus Lead Camera" )
        self.lead_mode.setCheckable( True )
        self.lead_mode.toggled.connect( self._qgl_pane.modeToggle )
        toolbar.addWidget( self.lead_mode )

        self.show_all = QtWidgets.QToolButton( self )
        self.show_all.setIcon( getStdIcon( QtWidgets.QStyle.SP_FileDialogListView ) )
        self.show_all.setStatusTip( "Show All" )
        self.show_all.setToolTip( "Show All Cameras" )
        self.show_all.setCheckable( False )
        #self.show_all.toggled.connect( self._qgl_pane.modeToggle )
        toolbar.addWidget( self.show_all )

        self.reset_all = QtWidgets.QToolButton( self )
        self.reset_all.setIcon( getStdIcon( QtWidgets.QStyle.SP_FileDialogContentsView ) )
        self.reset_all.setStatusTip( "Reset Zoom" )
        self.reset_all.setToolTip( "Reset Zoom on All Cameras" )
        self.reset_all.setCheckable( False )
        self.reset_all.clicked.connect( self._qgl_pane.resetAllCams )
        toolbar.addWidget( self.reset_all )

        # Labelling Options
        self.label_mode = QtWidgets.QToolButton( self )

        # only draw if live
        if( not self.live ):
            return

        toolbar.addSeparator()

        # Toggling Icon
        two_state = QtGui.QIcon()
        temp_pm = getStdIcon( QtWidgets.QStyle.SP_DialogYesButton ).pixmap(128)
        two_state.addPixmap( temp_pm, QtGui.QIcon.Normal, QtGui.QIcon.On )
        temp_pm = getStdIcon( QtWidgets.QStyle.SP_DialogNoButton ).pixmap(128)
        two_state.addPixmap( temp_pm,  QtGui.QIcon.Normal, QtGui.QIcon.Off )

        self.label_mode.setIcon( two_state )
        self.label_mode.setStatusTip( "Label Wand" )
        self.label_mode.setToolTip( "Enable Visual Wand Labelling" )
        self.label_mode.setCheckable( True )
        toolbar.addWidget( self.label_mode )

        self.selector = QtWidgets.QComboBox()
        self.selector.addItems( ["5-mkr Wand", "3-mkr Wand", "1 Point"] )
        toolbar.addWidget( self.selector )

