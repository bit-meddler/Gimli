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

#import ctypes
import sys
import numpy as np

# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) )
CODE_PATH = os.path.join( _git_root_, "Python" )
sys.path.append( CODE_PATH )

from Core.math3D import *
from GUI.shaders import ShaderHelper

import cv2

from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import VoidPtr
from OpenGL import GL

from textwrap import TextWrapper


class OGLWindow( QtWidgets.QWidget ):

    def __init__( self, parent=None ):
        super( OGLWindow, self ).__init__( parent )
        self.setWindowTitle( "Testing OpenGL" )

        self.glWidget = GLVP()
        self.glWidget.setSizePolicy( QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding )
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.addWidget( self.glWidget )

        toolLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout( toolLayout )

        but = QtWidgets.QPushButton( "Change BG Colour", self )
        but.clicked.connect( self._onSetCol )
        toolLayout.addWidget( but )

        self.setLayout( mainLayout )

    def _onSetCol( self ):
        colour = QtWidgets.QColorDialog.getColor( QtGui.QColor.fromRgbF( *self.glWidget.DEFAULT_BG ),
                    self, "Select Background Colour",
                    options=QtWidgets.QColorDialog.ShowAlphaChannel|QtWidgets.QColorDialog.DontUseNativeDialog
        )
        self.glWidget.bgcolour = colour.getRgbF()


class PackedColourTexture( ShaderHelper ):
    shader_path = os.path.join( CODE_PATH, "GUI", "Shaders" )
    vtx_f = "simpleVCTpack.vert"
    frg_f = "simpleCTadd.frag"


class SimpleColour( ShaderHelper ):
    shader_path = os.path.join( CODE_PATH, "GUI", "Shaders" )
    vtx_f = "simpleVuC.vert"
    frg_f = "simpleC.frag"


def genFloorGridData( divs, size=100.0, y_height=0.0 ):
    """ Generate a Floor plane, -1, 1 spread into divisions of size at y_height

    :param divs: int or [int,int] of X,Z shape of grind
    :param size: spacing of 'tiles' 100 = 1m, 30.5 = 1ft
    :param y_height: hight of grid (default=0.0)
    :return: (vtx, indxs) vertex array, index array
    """
    vtx_np, idx_np = None, None
    dim_x, dim_z = 2, 2

    if( type( divs ) in (list, tuple) ):
        dim_x, dim_z = divs[0], divs[1]
    else:
        dim_x = dim_z = int( divs )

    h_x, h_z = dim_x // 2, dim_z // 2
    last_x, last_z = dim_x + 1, dim_z + 1

    # Vertexs
    step_x = 1.0 / (h_x)
    step_z = 1.0 / (h_z)

    vtx = []
    for z in range( last_z ):
        z_point = (step_z * z) - 1.0
        for x in range( last_x ):
            vtx.append( [(step_x * x) - 1.0, 0.0, z_point] )

    vtx_np = np.asarray( vtx, dtype=FLOAT_T )
    vtx_np[:,0] *= size * h_x
    vtx_np[:,2] *= size * h_z

    # insert y_height
    height = np.ones( vtx_np.shape[0], dtype=FLOAT_T )
    height *= y_height
    vtx_np[:,1] = height


    # Indexs
    # line in/out pairs to draw each grid, slice list for the perimeter, the major axis
    row = [ [] for _ in range( last_z ) ]
    col = [ [] for _ in range( last_x ) ]
    for z in range( last_z ):
        for x in range( last_x ):
            idx = (z * last_x) + x

            row[z].append( idx )
            col[x].append( idx )

            if( not (x==0 or x==dim_x) ):
                row[z].append( idx )

            if( not (z==0 or z==dim_z) ):
                col[x].append( idx )

    row_stride = len( row[0] )
    col_stride = len( col[0] )

    rows = [ idx for line in row for idx in line ]
    cols = [ idx for line in col for idx in line ]

    col_offset = len( rows )

    outline = ( (0,row_stride),                 (col_offset+(dim_z*col_stride),col_stride),
                (dim_x*row_stride, row_stride), (col_offset, col_stride), )

    majors = ( (col_offset+(h_x*col_stride), col_stride),
               (h_z*row_stride, row_stride))
    idxs = np.asarray( rows + cols, dtype=GLIDX_T )

    # index slices
    return (vtx_np, idxs, (outline, majors))


class NavCam( object ):

    UP = QtGui.QVector3D( 0.0, 1.0, 0.0 )
    DEFAULT_POS = QtGui.QVector3D( 200.0, 180.0, 200.0 )
    DEFAULT_INT = QtGui.QVector3D( 0.0, 0.0, 0.0 )

    def __init__( self ):
        # locked camera
        self.locked = False

        # Camera extrinsics
        self.pos = self.DEFAULT_POS
        self.int = self.DEFAULT_INT

        self.rot = QtGui.QVector3D( 0.0, 0.0, 0.0 ) # Roll, Pitch, Yaw
        self.dst = 0.0 # Distance to interest

        # Navigation Representation
        self.fwd = QtGui.QVector3D( 0.0, 0.0, -1.0 )  # Camera Forward Vector
        self.cup = QtGui.QVector3D( 0.0, 1.0,  0.0 )  # Camera up
        self.rgt = QtGui.QVector3D( 1.0, 0.0,  0.0 )  # Right Vector

        # camera intrinsics
        self.vFoV   = 90.0  # Generic
        self.aspect = 1.777 # 16:9

        # GL Darwing
        self.nr_clip = 0.1
        self.fr_clip = 10000.0
        self.port    = [ 1920, 1080 ] # Viewport dimensions

        # GL Matrixes
        self.view = QtGui.QMatrix4x4()
        self.proj = QtGui.QMatrix4x4()

    def lookAtInterest( self ):
        if( self.locked ):
            return

        self.view.setToIdentity()
        self.view.lookAt( self.pos, self.int, self.UP )
        self.dst = self.pos.distanceToPoint( self.int )

    def updateProjection( self ):
        if (self.locked):
            return

        self.proj.setToIdentity()
        self.proj.perspective( self.vFoV, self.aspect, self.nr_clip, self.fr_clip )

    def setFov( self, newFov ):
        FoV = np.clip( newFov, 1.0, 120.0 )
        self.vFoV = FoV
        self.updateProjection()

    def changeFoV( self, delta ):
        self.setFov( self.vFoV + delta )

    def changePort( self, width, height ):
        self.port = [ width, height ]
        self.aspect = float( self.port[ 0 ] ) / float( self.port[ 1 ] )

    def truck( self, d_x, d_y ):
        """ Translate the view Left/Right and Up/Down

        :param d_x: (float) change in x
        :param d_y: (float) change in y
        """
        offset = QtGui.QVector3D( d_x, d_y, 0.0 )
        self.pos += offset
        self.int += offset
        self.lookAtInterest()

    def dolly( self, delta ):
        """ Translate along the vector from camera pos to interest.
        :param delta (float) amount to move in or out
        """
        direction = self.pos - self.int
        direction.normalize()
        direction *= delta
        new = self.pos + direction

        test = QtGui.QMatrix4x4()
        test.lookAt( new, self.int, self.UP )
        dst = new.distanceToPoint( self.int )
        if( dst < 0.1 ):
            # Too close
            return

        self.pos = new
        self.lookAtInterest()

    def tumble( self, d_x, d_y ):
        """ Move camera position around surface of a ball centred at the interest,
            Maintain the radius (self.dst)

        """
        offset = QtGui.QVector3D( d_x, d_y, 0.0 )
        new = self.pos + offset
        direction = self.int - new
        direction.normalize()
        direction *= self.dst * -1.0
        self.pos = direction
        self.lookAtInterest()

    def resetView( self ):
        """ Reset to default view position """
        self.int = self.DEFAULT_INT
        self.pos = self.DEFAULT_POS
        self.lookAtInterest()

    def compuuteLookAt( self, eye_pos, tgt_pos, up ):
        # Forward
        Z = eye_pos - tgt_pos
        Z.normalise()

        # Camera Right
        X = QtGui.QVector3D.crossProduct( up.normalized(), Z )
        X.normalise()

        # Camera Up
        Y = QtGui.QVector3D.crossProduct( Z, X )
        Y.normalise()


class QGLWhelper( QtWidgets.QOpenGLWidget ):

    DEFAULT_BG = (0.0, 0.1, 0.1, 1.0)

    def __init__( self, parent=None ):
        super( QGLWhelper, self ).__init__( parent )

        # Lock out GLPaint
        self.configured = False

        # OpenGL setup
        self.bgcolour = self.DEFAULT_BG
        self.vaos = {}
        self.buffers = {}
        self.buffer_data = {}
        self.shaders = {}
        self.textures = {}
        self.f = None # glFunctions

        # Shader registry
        self.shader_sources = {}

        # canvas size
        self.wh = ( self.geometry().width(), self.geometry().height() )
        self.aspect = float(self.wh[0]) / float(self.wh[1])

    def _confBuffer( self, kind, pattern, data=None ):

        gl_buf = QtGui.QOpenGLBuffer( kind )
        gl_buf.create()
        gl_buf.setUsagePattern( pattern )

        if( data is not None ):
            gl_buf.bind()
            gl_buf.allocate( data.tobytes(), data.nbytes )
            gl_buf.release()

        return gl_buf

    def loadImage( self, image_fq ):
        """ Use OpenCV to load an image

        :param image_fq: (string) fully qualified path to the image
        :return: (ndarray) the image in CV2 format

        WARNING: Inexplicably, you cannot load the image and convert to a QImage in a single function!!!
        """
        img = cv2.imread( image_fq, cv2.IMREAD_COLOR )
        return img

    def cv2Q( self, cv_img ):
        rgb_img = cv2.cvtColor( cv_img, cv2.COLOR_BGR2RGB )
        img_h, img_w, img_ch = rgb_img.shape
        q_img = QtGui.QImage( rgb_img.data, img_w, img_h, (img_ch * img_w), QtGui.QImage.Format_RGB888 )
        return q_img

    def bindTexture( self, image, filter_min, filter_mag, blend_s, blend_t ):
        # Create Texture
        target = QtGui.QOpenGLTexture( QtGui.QOpenGLTexture.Target2D ) # Target2D === GL_TEXTURE_2D
        target.create()
        target.bind()
        target.setData( image )
        target.setMinMagFilters( filter_min, filter_mag )
        target.setWrapMode( QtGui.QOpenGLTexture.DirectionS, blend_s )
        target.setWrapMode( QtGui.QOpenGLTexture.DirectionT, blend_t )
        target.release()
        return target

    def _configureVertexAttribs( self, vao_name, shader_name ):

        print( "Attaching VAPs on '{}' to shader '{}'".format( vao_name, shader_name ) )
        vao = self.vaos[ vao_name ]
        buffer = self.buffers[ vao_name ][ "vbo" ]
        helper = self.shader_sources[ shader_name ]
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( vao )
        buffer.bind()
        for name, num, offset in helper.layout:
            location = helper.attr_locs[ name ]
            print( "  Setting VAP on '{}' @ {} with {} elems from {}b".format(
                name, location, num, offset )
            )
            os_ptr = VoidPtr( offset )
            self.f.glEnableVertexAttribArray( location )
            self.f.glVertexAttribPointer( location,
                                          num,
                                          GL.GL_FLOAT,
                                          GL.GL_FALSE,
                                          helper.line_size,
                                          os_ptr )
        buffer.release()
        del (vao_lock)
        print( "This buffer line size is {}b".format( helper.line_size ) )

    def _configureAttribBindings( self ):
        """
        Must be implemented by user
        """
        pass

    def _configureShaders( self ):

        for shader in self.shader_sources.values():
            shader.compose()

        for shader, helper in self.shader_sources.items():
            print( "Preparing shader '{}'".format( shader ) )

            self.shaders[ shader ] = QtGui.QOpenGLShaderProgram( self.context() )

            self.shaders[ shader ].addShaderFromSourceCode( QtGui.QOpenGLShader.Vertex, helper.vtx_src )
            self.shaders[ shader ].addShaderFromSourceCode( QtGui.QOpenGLShader.Fragment, helper.frg_src )

            # Bind attrs
            for attr, location in helper.attr_locs.items():
                self.shaders[ shader ].bindAttributeLocation( attr, location )

            # Link Shader
            is_linked = self.shaders[ shader ].link()
            if (not is_linked):
                print( "  Error linking shader!" )

            # Locate uniforms
            for uniform, data in helper.vtx_uniforms.items():
                location = self.shaders[ shader ].uniformLocation( uniform )
                helper.vtx_unis[ uniform ] = location
                print( "  Vtx uniform '{}' ({}{}) bound @ {}".format(
                    uniform, data[ "type" ], data[ "shape" ], location )
                )

    def getGlInfo( self, show_ext=False ):
        print( "Getting GL Info" )

        ven = self.f.glGetString( GL.GL_VENDOR )
        ren = self.f.glGetString( GL.GL_RENDERER )
        ver = self.f.glGetString( GL.GL_VERSION )
        slv = self.f.glGetString( GL.GL_SHADING_LANGUAGE_VERSION )
        ext = self.f.glGetString( GL.GL_EXTENSIONS )

        exts = ""
        if (show_ext):
            pad = "            "
            w = TextWrapper( width=100, initial_indent="", subsequent_indent=pad )
            lines = w.wrap( ext )
            exts = "\n".join( lines )

        else:
            exts = "{} installed".format( len( ext.split() ) )

        info = "Vendor: {}\nRenderer: {}\nOpenGL Version: {}\nShader Version: {}\nExtensions: {}".format(
            ven, ren, ver, slv, exts )

        # Get context Info?

        return info

    def _onClosing( self ):
        """ Clean close of OGL resources """
        print( "Clean Close" )
        self.context().makeCurrent()

        for buff in self.buffers.values():
            buff.destroy()

        self.texture.destroy()

        for vao in self.vaos.values():
            vao.destroy()

        for shader in self.shaders.items():
            del (shader)

        self.doneCurrent()

    def initalizeApp( self ):
        """
        Implement in user

        self.configured must be set True!!!
        """
        pass

    def initializeGL( self ):
        super( QGLWhelper, self ).initializeGL()

        # init GL Context
        ctx = self.context()
        ctx.aboutToBeDestroyed.connect( self._onClosing )

        # get Context bound GL Funcs
        self.f = QtGui.QOpenGLFunctions( ctx )
        self.f.initializeOpenGLFunctions()

        # shaders
        self._configureShaders()

        # buffers & Textures
        self.f.glEnable( GL.GL_TEXTURE_2D )
        self._prepareResources()

        # Attrs
        self._configureAttribBindings()

        # misc
        self.f.glClearColor( *self.bgcolour )

        self.f.glEnable( GL.GL_DEPTH_TEST )
        self.f.glDepthFunc( GL.GL_LESS )

        self.f.glEnable( GL.GL_BLEND )
        self.f.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )

        self.f.glEnable( GL.GL_POINT_SMOOTH )
        self.f.glHint( GL.GL_POINT_SMOOTH_HINT, GL.GL_NICEST )

        self.initalizeApp()


class GLVP( QGLWhelper ):

    NAVIGATION_MODES = ( "TUMBLE", "TRUCK", "DOLLY", "ZOOM" )

    def __init__( self, parent=None ):
        super( GLVP, self ).__init__( parent )

        # Shader registry
        self.shader_sources = {
            "packedCT" : PackedColourTexture(),
            "simpleC"  : SimpleColour(),
        }

        # Transform & MVP
        self.rot = 0.0

        # Navigation Camera
        self.camera = NavCam()
        self.camera.aspect = self.aspect
        self.nav_mode = None
        self._last_x = 0
        self._last_y = 0

        # ticks for redraws / updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.update )

    def genCubeX( self, xs, ys, zs, sz=20.0, spacing=50.0 ):
        h_x, h_y, h_z = xs // 2, ys // 2, zs // 2
        last_x, last_y, last_z = xs + 1, ys + 1, zs + 1

        # Vertexs
        step_x = 1.0 / (h_x)
        step_y = 1.0 / (h_y)
        step_z = 1.0 / (h_z)

        transforms = [ ]
        for z in range( last_z ):
            z_pos = ((step_z * z) - 1.0) * spacing * h_z

            for y in range( last_y ):
                y_pos = ((step_y * y) - 1.0) * spacing * h_y
                y_rot = (self.rot / 11.0) + (y * 6.0)

                for x in range( last_x ):
                    x_pos = ((step_x * x) - 1.0) * spacing * h_x

                    transform = QtGui.QMatrix4x4()
                    transform.translate( x_pos, y_pos, z_pos )
                    transform.rotate( self.rot, 1.0, 0.0, 0.0 ) # ang, axis
                    transform.rotate( y_rot, 0.0, 1.0, 0.0 )
                    transform.rotate( x+y+z, 0.0, 0.0, 1.0 )
                    transform.scale( sz )

                    transforms.append( transform )

        return transforms

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
        obj = np.array( cube, dtype=FLOAT_T )

        indices = [
             0,  1,  2,  2,  3,  0,
             4,  5,  6,  6,  7,  4,
             8,  9, 10, 10, 11,  8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20,
        ]

        indices = np.array( indices, dtype=GLIDX_T )


        # Generate a Floor Grid
        floor_vtx, floor_idx, (floor_line, floor_mjrs) = genFloorGridData( 8, 100.0 )

        # Generate OGL Buffers
        ########################################################################


        # Cube Data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        task = "cube"
        self.vaos[task] = QtGui.QOpenGLVertexArrayObject()
        self.vaos[task].create()
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vaos[task] )

        self.buffers[task] = {}
        self.buffer_data[task] = {}
        buffers = self.buffers[task]

        buffers["vbo"] = self._confBuffer( QtGui.QOpenGLBuffer.VertexBuffer,
                                           QtGui.QOpenGLBuffer.StaticDraw,
                                           data=obj )
        buffers["ibo"] = self._confBuffer( QtGui.QOpenGLBuffer.IndexBuffer,
                                           QtGui.QOpenGLBuffer.StaticDraw,
                                           data=indices )

        self.buffer_data[task]["ibo.in"] = 0
        self.buffer_data[task]["ibo.idxs"] = len( indices )

        # Load Texture Image
        image_fq = "wood.jpg"
        img = self.loadImage( image_fq )
        q_img = self.cv2Q( img )

        # Create Texture
        self.textures[task] = self.bindTexture( q_img, QtGui.QOpenGLTexture.Linear, QtGui.QOpenGLTexture.Linear,
                                                QtGui.QOpenGLTexture.ClampToEdge, QtGui.QOpenGLTexture.ClampToEdge )
        # Release the VAO Mutex Binder
        del( vao_lock )

        # Grid Data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        task = "grid"
        self.vaos[task] = QtGui.QOpenGLVertexArrayObject()
        self.vaos[task].create()
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vaos[task] )

        self.buffers[task] = {}
        self.buffer_data[task] = {}
        buffers = self.buffers[task]

        buffers["vbo"] = self._confBuffer( QtGui.QOpenGLBuffer.VertexBuffer,
                                           QtGui.QOpenGLBuffer.StaticDraw,
                                           data=floor_vtx )
        buffers["ibo"] = self._confBuffer( QtGui.QOpenGLBuffer.IndexBuffer,
                                           QtGui.QOpenGLBuffer.StaticDraw,
                                           data=floor_idx )

        self.buffer_data[task]["ibo.in"] = 0
        self.buffer_data[task]["ibo.idxs"] = len( floor_idx )
        self.buffer_data[task]["ibo.str.outline"] = floor_line
        self.buffer_data[task]["ibo.str.major"] = floor_mjrs

        del (vao_lock)

    # Application specific GL Config -------------------------------------------

    def _configureAttribBindings( self ):
        self._configureVertexAttribs( "grid", "simpleC" )
        self._configureVertexAttribs( "cube", "packedCT" )

    def initalizeApp( self ):
        # Setup Camera
        self.camera.lookAtInterest()
        self.camera.updateProjection()

        # Start auto updates
        self.timer.start( 16 )  # approx 60fps

        self.configured = True

    # Navigation funcs ---------------------------------------------------------
    def _beginNav( self, mode ):
        """ begin or change a navigation interaction """
        if( self.nav_mode == mode ):
            return # still in the same mode

        # Complete the last interaction
        self._endNav()

        self.nav_mode = mode

    def _endNav( self ):
        self.nav_mode = None

    # Qt funcs -----------------------------------------------------------------
    def mousePressEvent(self, event):
        """ Determine what interactions we're making with the scene. """
        buttons = event.buttons()
        modifiers = event.modifiers()

        # All interactions need to calculate a delta from the start point
        self._last_x, self._last_y = event.x(), event.y()

        lmb = bool( buttons & QtCore.Qt.LeftButton  )
        mmb = bool( buttons & QtCore.Qt.MidButton   )
        rmb = bool( buttons & QtCore.Qt.RightButton )

        if( bool(modifiers & QtCore.Qt.AltModifier) ):
            # 3D Navigation has begun
            if( lmb ):
                if( rmb ):
                    self._beginNav( "TRUCK" )

                else:
                    self._beginNav( "TUMBLE" )

            elif( rmb ):
                self._beginNav( "DOLLY" )

            elif( mmb ):
                self._beginNav( "ZOOM" )

    def mouseReleaseEvent( self, event ):
        buttons = event.buttons()

        if( buttons == 0 ):
            self._endNav()
            #super( GLVP, self ).mouseReleaseEvent( event ) #???

        else:
            # use the new button mask to change tools,
            # e.g. toggle between Truck & Tumble
            self.mousePressEvent( event )

    def mouseDoubleClickEvent( self, event ):
        modifiers = event.modifiers()
        if( bool( modifiers & QtCore.Qt.AltModifier ) ):
            # Navigation + Double Click = Reset View
            self.camera.resetView()

    def mouseMoveEvent( self, event ):
        """ The real meat of navigation goes on here. """
        if( self.nav_mode is None ):
            return

        modifiers = event.modifiers()

        # mouse motion computations
        new_x, new_y = event.x(), event.y()
        d_x, d_y = new_x - self._last_x, new_y - self._last_y

        scale = 0.5 if bool(modifiers & QtCore.Qt.ShiftModifier) else 1.2

        s_x, s_y = d_x * scale, d_y * scale

        if(   self.nav_mode == "TRUCK" ):
            self.camera.truck( s_x * -1.0, s_y )

        elif( self.nav_mode == "TUMBLE" ):
            self.camera.tumble( s_x * -1.0, s_y )

        elif( self.nav_mode == "DOLLY" ):
            self.camera.dolly( s_x * 2.0 )

        elif( self.nav_mode == "ZOOM" ):
            self.camera.changeFoV( (s_y/2.0) * -1.0 )

        self._last_x, self._last_y = new_x, new_y

    def minimumSizeHint( self ):
        return QtCore.QSize( 400, 400 )

    def sizeHint( self ):
        return QtCore.QSize( 400, 400 )

    # gl funs ------------------------------------------------------------------
    def paintGL( self ):
        # guard against early drawing
        if( not self.configured ):
            return

        # Going to try overpainting again...
        painter = QtGui.QPainter()
        painter.begin( self )

        # Enable GL
        painter.beginNativePainting()

        # gl Viewport
        self.f.glEnable( GL.GL_DEPTH_TEST ) # Has to be reset because painter :(
        self.f.glClearColor( *self.bgcolour )
        #self.f.glViewport( 0, 0, self.wh[0], self.wh[1] )
        self.f.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )

        # Update View / Projection mats
        pv = self.camera.proj * self.camera.view

        # Cube Drawing
        task = "cube"
        # attach VAO
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vaos[task] )

        # Get Shader
        shader = self.shaders["packedCT"]
        helper = self.shader_sources["packedCT"]
        shader.bind()

        self.buffers[task]["vbo"].bind()
        self.buffers[task]["ibo"].bind()
        self.textures[task].bind()

        # striding data
        ptr = VoidPtr( self.buffer_data[task]["ibo.in" ] )
        num_idx = self.buffer_data[task]["ibo.idxs" ]

        # Draw a field of cubes
        for transform in self.genCubeX( 10, 5, 6 ):

            # Make ravey if above ground
            n = 1.0 if (transform.column( 3 ).y() > 0.0) else 0.0
            shader.setUniformValue( helper.vtx_unis[ "u_hilight" ], n  )

            mvp = pv * transform
            shader.setUniformValue( helper.vtx_unis[ "u_mvp" ], mvp )
            self.f.glDrawElements( GL.GL_TRIANGLES, num_idx, GL.GL_UNSIGNED_INT, ptr )

        self.rot += 1.0

        # Done Cubes
        self.buffers[task]["vbo"].release()
        self.buffers[task]["ibo"].release()
        self.textures[task].release()
        shader.release()
        helper = None
        del (vao_lock)

        # Draw Grid
        task = "grid"
        vao_lock = QtGui.QOpenGLVertexArrayObject.Binder( self.vaos[ task ] )

        shader = self.shaders["simpleC"]
        helper = self.shader_sources["simpleC"]
        shader.bind()
        self.buffers[task]["vbo"].bind()

        transform = QtGui.QMatrix4x4()
        transform.setToIdentity()

        mvp = pv * transform

        shader.setUniformValue( helper.vtx_unis[ "u_mvp" ], mvp )
        shader.setUniformValue( helper.vtx_unis[ "u_colour" ], 0.8, 0.8, 0.8 )

        # draw grid
        ptr = VoidPtr( self.buffer_data[task]["ibo.in"] )
        num_idx = self.buffer_data[task]["ibo.idxs" ]
        self.f.glDrawArrays( GL.GL_POINTS, ptr, num_idx )
        #self.f.glDrawElements( GL.GL_LINES, num_idx, GL.GL_UNSIGNED_INT, ptr )

        # draw outline
        # shader.setUniformValue( helper.vtx_unis[ "u_colour" ], 1.0, 1.0, 1.0 )
        # for os, num in self.buffer_data[task]["ibo.str.outline" ]:
        #     print( os, num )
        #     ptr = VoidPtr( os )
        #     num_idx = num
        #     self.f.glDrawElements( GL.GL_LINES, num_idx, GL.GL_UNSIGNED_INT, ptr )

        # highlight majors
        os, num = self.buffer_data[task]["ibo.str.major" ][0]
        shader.setUniformValue( helper.vtx_unis[ "u_colour" ], 1.0, 0.0, 0.0 )
        ptr = VoidPtr( os )
        num_idx = num
        self.f.glDrawArrays( GL.GL_POINTS, ptr, num_idx )
        #self.f.glDrawElements( GL.GL_LINES, num_idx, GL.GL_UNSIGNED_INT, ptr )

        os, num = self.buffer_data[task]["ibo.str.major" ][1]
        shader.setUniformValue( helper.vtx_unis[ "u_colour" ], 0.0, 0.0, 1.0 )
        ptr = VoidPtr( os )
        num_idx = num
        self.f.glDrawArrays( GL.GL_POINTS, ptr, num_idx )
        #self.f.glDrawElements( GL.GL_LINES, num_idx, GL.GL_UNSIGNED_INT, ptr )

        # Done Grid
        self.buffers[task]["vbo"].release()
        shader.release()
        del( vao_lock )

        # Done with GL
        self.f.glDisable( GL.GL_DEPTH_TEST )
        painter.endNativePainting()

        # Try drawing some text
        painter.setRenderHint( QtGui.QPainter.TextAntialiasing )
        painter.setPen( QtCore.Qt.white )

        # Camera Info
        c = self.camera
        text  = "Camera "
        text += "T:{:.3f}, {:.3f}, {:.3f}".format( c.pos.x(), c.pos.y(), c.pos.z() )
        text += "N:{:.3f}, {:.3f}, {:.3f}".format( c.int.x(), c.int.y(), c.int.z() )
        text += "FoV:{:.3f}".format( c.vFoV )
        painter.drawText( 10, 10, text )

        painter.end()

    def resizeGL( self, width, height ):
        self.wh = ( width, height )

        self.camera.changePort( width, height )
        self.aspect = float( self.wh[ 0 ] ) / float( self.wh[ 1 ] )
        self.f.glViewport( 0, 0, self.wh[ 0 ], self.wh[ 1 ] )


if( __name__ == "__main__" ):
    app = QtWidgets.QApplication( sys.argv )

    mainWindow = OGLWindow()
    mainWindow.resize( mainWindow.sizeHint() )
    mainWindow.show()

    res = app.exec_()
    sys.exit( res )
