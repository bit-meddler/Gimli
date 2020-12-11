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

from Core.math3D import genOrthoProjectionPlains, FLOAT_T, ID_T, TWO_PI
import Core.labelling as lid

from GUI import getStdIcon

SQUARES = [ x ** 2 for x in range( 9 ) ]

class Shaders( object ):
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

    ZOOM_SCALE    = 1.075
    TRUCK_SCALE   = 0.01
    DEFAULT_WIDTH = 2.5
    DEFAULT_ZOOM  = 1.075

    def __init__(self, parent=None ):
        super(QGLCameraPane, self).__init__( parent )
        # canvas size
        self._wh = (self.geometry().width(), self.geometry().height())
        self._rc = (-1, -1) # ros and cols of cameras to display

        self._subwindow_sz = (0, 0)

        self.cam_list = []
        self.num_cams = 0
        self.draw_lead = False

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
        """ Draw the cameras """
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

                # ToDo: Far in the future, draw an image - texture on a quad in BG?

                # Draw Roids
                sin, sout = self._strider[ cam_idx ]
                idx_in    = self.stride_list[ sin ]
                num_dets  = self.stride_list[ sout ] - idx_in
                idx_in   += self._reticule_block_sz # Skip reticule

                if( num_dets > 0 ):
                    GL.glDrawArrays( GL.GL_POINTS, idx_in, num_dets )

                # Draw reticule
                GL.glDrawArrays( GL.GL_LINES, 0, self._reticule_sz )


                # Kills redrawws?
                overlays.append( ( text_x + x, text_y - y, "Camera {}".format( cam_idx+1 ) ) )

                # Done?
                cam_idx += 1
                if( cam_idx >= self.num_cams ):
                    break

        self.shader.release()

        # Draw overlay text
        # # Enable a painter, but switch to Native Painting immediatly
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

        if( update_camera and self._navigate is not None ):
            self.updateProjection( self._navigate )

        self._navigate = None

    def mouseMoveEvent( self, event ):
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
            print( cam_idx, self._ortho_navigation[ cam_idx ] )
            self.modeToggle()
            if( self.draw_lead ):
                # clicked camera is lead
                self.reorderCamList( cam_idx )
            else:
                # back to normal
                self.reorderCamList()

    def minimumSizeHint( self ):
        return QtCore.QSize( 640, 480 )


    # functional ---------------------------------------------------------------
    def acceptNewData( self, dets, strides, ids ):
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
        if( cam_idx is None ):
            return
        cam = self._ortho_navigation[ cam_idx ]
        cam[ "P" ] = self.projectionFromNav( cam[ "zoom" ], cam[ "width" ], cam["locus"][0], cam["locus"][1] )
        self.update()

    def _camlistChanged( self ):
        self.num_cams = len( self.cam_list )
        self._rc = self.genDimsSquare( self.num_cams )
        self._marshelStrides()

        # Hack: This should be a sceneMan thing.
        self.resetAllCams()

    def resetAllCams( self ):
        # Populate cameras with Ortho Navigation
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
        w, h = self._subwindow_sz
        if( w < 1 or h < 1 ):
            return np.eye( 4, dtype=FLOAT_T )

        span = width * zoom
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

    def reorderCamList( self, lead=None ):
        self.cam_list = sorted( self.cam_list )
        if( lead is not None and lead in self.cam_list ):
            self.cam_list.remove( lead )
            self.cam_list.append( lead )

    def modeToggle( self ):
        self.draw_lead = not self.draw_lead
        width, height = self._wh
        if( self.draw_lead ):
            self._rc = self.genDimsSquare( 1 )
        else:
            self._rc = self.genDimsSquare( self.num_cams )
        self.resizeGL( width, height )

    def _camFromXY( self, x, y ):
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
        Determine rows / cols needed to pack num_cams into to keep square

        :param num_cams: (int) number of cameras to arrange
        :return: (int,int) Rows, Cols
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


# ah. no it needs to be in a widget
class QGLCameraView( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QGLCameraView, self ).__init__()

        self._qgl_pane = QGLCameraPane( self )

        self._setupToolBar()

        self.setCentralWidget( self._qgl_pane )

        self._qgl_pane.update()

    def _camlistChanged( self ):
        self._qgl_pane._camlistChanged()

    def acceptNewData( self, dets, strides, ids ):
        self._qgl_pane.acceptNewData( dets, strides, ids )

    def _setupToolBar( self ):
        toolbar = QtWidgets.QToolBar( "Camera view tools" )
        toolbar.setIconSize( QtCore.QSize( 16, 16 ) )
        toolbar.setMovable( False )
        self.addToolBar( toolbar )

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

