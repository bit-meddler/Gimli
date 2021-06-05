# 
# Copyright (C) 2016~2021 The Gimli Project
# This file is part of Gimli <https://github.com/bit-meddler/Gimli>.
#
# Gimli is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Gimli is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gimli.  If not, see <http://www.gnu.org/licenses/>.
#

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

        uniform mat4 u_model ;
        uniform mat4 u_view ;
        uniform mat4 u_projection ;

        void main() {
            gl_Position = u_projection * u_view * u_model * vec4( a_position, 1.0f ) ;
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
        ymax = near_clip * np.tan( np.deg2rad( h_fov ) / 2.0 )
        xmax = ymax * aspect
        return Math3D.genPerspProjectionPlaines( -xmax, xmax, -ymax, ymax, near_clip, far_clip )

    @staticmethod
    def genPerspProjectionPlaines( left, right, base, top, near, far ):
        rml = right - left
        tmb = top - base
        fmn = far - near
        tnr = 2.0 * near
        return np.array((
            ( tnr / rml,       0.0, (right + left) / rml,              0.0 ),
            (       0.0, tnr / tmb,   (top + base) / tmb,              0.0 ),
            (       0.0,       0.0,  -(far + near) / fmn, -far * tnr / fmn ),
            (       0.0,       0.0,                 -1.0,              0.0 ),
        ), dtype=np.float32 )

    @staticmethod
    def genOrthoProjectionPlains( left, right, base, top, near, far ):
        rml = right - left
        tmb = top - base
        fmn = far - near
        return np.array((
            ( 2.0 / rml,       0.0,        0.0, -(right + left) / rml ),
            (       0.0, 2.0 / tmb,        0.0,   -(top + base) / tmb ),
            (       0.0,       0.0, -2.0 / fmn,   -(far - near) / fmn ),
            (       0.0,       0.0,        0.0,                   1.0 ),
        ), dtype=np.float32 )


class GLWidget( QtWidgets.QOpenGLWidget ):

    DEFAULT_ZOOM = 1.05
    TRUCK_SCALE  = 0.01

    def __init__( self, parent=None ):
        super( GLWidget, self ).__init__( parent )
        self.bgcolor = [ 0, 0.1, 0.1, 1 ]
        self.shader_attr_locs = {}

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )

        # Persp Camera Setup
        self.fov = 45.0
        self.clip_nr = -100.0#0.1
        self.clip_far = 100.0

        # Ortho Camera Setup
        self._zoom = 1.0
        self._ortho_width = 2.0
        self._locus = [ 1.0, 0.0 ]

        # internals for camera movement
        self._panning = False
        self._zooming = False
        self._move_start = None

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

        # textures have been abandoned, don't know why they won't work

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

        self.model_loc = self.shader.uniformLocation( "u_model" )
        self.view_loc  = self.shader.uniformLocation( "u_view" )
        self.proj_loc  = self.shader.uniformLocation( "u_projection" )
        self.shader.release()

    def updateProjection( self, width=None, height=None ):
        width = width or self.wh[0]
        height = height or self.wh[1]
        aspect = width / height

        # assemble a projection
        #self.projection = Math3D.genPerspProjectionFrust( self.fov, aspect, self.clip_nr, self.clip_far )

        orig_x, orig_y = self._locus
        span = self._ortho_width * self._zoom
        extent = span / aspect

        o_l = orig_x + span
        o_r = orig_x - span
        o_t = orig_y + extent
        o_b = orig_y - extent

        self.projection = Math3D.genOrthoProjectionPlains( o_l, o_r, o_b, o_t, self.clip_nr, self.clip_far )

        # upload to uniform
        self.shader.bind()
        GL.glUniformMatrix4fv( self.proj_loc,  1, GL.GL_TRUE, self.projection )
        self.shader.release()
        
        self.update()

    def reportMats( self ):
        print( "Projection\n", self.projection )
        print( "View\n", self.view )
        print( "Model\n", self.model )


    # Qt funcs -------------------------------------------------------
    def minimumSizeHint( self ):
        return QtCore.QSize( 50, 50 )

    def sizeHint( self ):
        return QtCore.QSize( 400, 400 )

    def wheelEvent( self, event ):
        wheel_delta = event.angleDelta().y()
        wheel_delta /= 100.

        if( wheel_delta > 0.0 ):
            self._zoom *= self.DEFAULT_ZOOM

        elif( wheel_delta < 0.0 ):
            self._zoom /= self.DEFAULT_ZOOM

        self.updateProjection()

    def mousePressEvent( self, event ):
        buttons = event.buttons()
        mods = event.modifiers()

        pressed_left  = bool( buttons & QtCore.Qt.LeftButton   )
        pressed_right = bool( buttons & QtCore.Qt.RightButton  )
        pressed_mid   = bool( buttons & QtCore.Qt.MiddleButton )
        pressed_alt   = bool( mods    & QtCore.Qt.AltModifier  )

        if( (pressed_left and pressed_right) or pressed_mid ):
            # trucking
            self._panning = True
            self._move_start = event.pos()

        elif( pressed_right ):
            # Zooming
            self._zooming = True
            self._move_start = event.pos()

    def mouseReleaseEvent( self, event ):
        super( GLWidget, self ).mouseReleaseEvent( event )
        
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
            self.updateProjection()

    def mouseMoveEvent( self, event ):
        update_camera = False

        if( self._panning or self._zooming ):
            # get the positional delta
            hz = event.x() - self._move_start.x() 
            vt = event.y() - self._move_start.y()
            self._move_start = event.pos()


        if( self._panning ):
            self._locus[0] += (hz * self._zoom) * self.TRUCK_SCALE
            self._locus[1] += (vt * self._zoom) * self.TRUCK_SCALE

            update_camera = True


        elif( self._zooming ):
            if( vt > 0.0 ):
                self._zoom *= self.DEFAULT_ZOOM
            elif( vt < 0.0 ):
                self._zoom /= self.DEFAULT_ZOOM

            update_camera = True


        if( update_camera ):
            self.updateProjection()

    def mouseDoubleClickEvent( self, event ):
        if( event.modifiers() & QtCore.Qt.AltModifier ):
            # Alt Double Click resets the camera
            self._zoom = 1.0
            self._ortho_width = 2.0
            self._locus = [ 0.0, 0.0 ]

            self.updateProjection()


    # gl funcs --------------------------------------------------------
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

        # setup camera / world matrices
        self.model = np.eye( 4, dtype=np.float32 )
        self.view  = np.eye( 4, dtype=np.float32 )
        self.projection = np.eye( 4, dtype=np.float32 )

        # move some stuff
        self.model[:3,3] = [0., 0., -3.1]
        #self.view[:3,3] = [0., 0., -.4]

        # Load Uniforms
        self.shader.bind()
        GL.glUniformMatrix4fv( self.model_loc, 1, GL.GL_TRUE, self.model )
        GL.glUniformMatrix4fv( self.view_loc,  1, GL.GL_TRUE, self.view )
        self.shader.release()

        # Initalize Projection
        self.updateProjection()

        # Report
        self.reportMats()

        # unlock the saftey
        self.ready = True

    def paintGL( self ):
        # guard against early drawing
        if( not self.ready ):
            return

        GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        GL.glViewport( 0, 0, self.wh[0], self.wh[1] )

        rot_x = Math3D.genRotMat( "X", self.rot, degrees=True )
        rot_y = Math3D.genRotMat( "Y", (self.rot/3)+90, degrees=True )
        xform = self.model
        xform[:3,:3] = np.dot( rot_y, rot_x )[:3,:3]

        self.shader.bind()

        GL.glUniformMatrix4fv( self.model_loc, 1, GL.GL_TRUE, xform )

        GL.glDrawElements( GL.GL_TRIANGLES, self.num_idx, GL.GL_UNSIGNED_SHORT, ctypes.c_void_p( 0 ) )

        self.shader.release()
        self.rot += 0.15

    def resizeGL( self, width, height ):
        self.wh = ( width, height )
        self.updateProjection()


if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )