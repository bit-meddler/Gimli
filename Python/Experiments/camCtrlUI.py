""" camCtrlUI.py - experimental UI for controlling Camera settings

    TODO: Ok this has gone far beyond an experiment, need to break down all the
          inner classes into a mGUI module so they can be reused in future Apps

"""
from functools import partial
import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
from OpenGL import GL, GLU, GLUT 

import sys, os
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
sys.path.append( CODE_PATH )

logging.basicConfig()
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

detailed_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s][%(name)-16s] %(message)s {%(filename)s@%(lineno)s}", "%y%m%d %H:%M:%S" )
terse_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s] %(message)s", "%y%m%d %H:%M:%S" )

from Comms import ArbiterControl

# Look and Feel Helpers
def _getStdIcon( icon_enum ):
    return QtGui.QIcon( QtWidgets.QApplication.style().standardIcon( icon_enum ) )

class QDarkPalette( QtGui.QPalette ):
    """ Dark palette for a Qt application, meant to be used with the Fusion theme.
        from Gist: https://gist.github.com/lschmierer/443b8e21ad93e2a2d7eb
    """
    WHITE     = QtGui.QColor( 255, 255, 255 )
    BLACK     = QtGui.QColor(   0,   0,   0 )
    RED       = QtGui.QColor( 255,   0,   0 )
    PRIMARY   = QtGui.QColor(  53,  53,  53 )
    SECONDARY = QtGui.QColor(  35,  35,  35 )
    TERTIARY  = QtGui.QColor(  87, 140, 178 )

    def __init__( self, *args):
        super( QDarkPalette, self ).__init__( *args )

        self.setColor( QtGui.QPalette.Window,          self.PRIMARY  )
        self.setColor( QtGui.QPalette.WindowText,      self.WHITE    )
        self.setColor( QtGui.QPalette.Base,            self.SECONDARY)
        self.setColor( QtGui.QPalette.AlternateBase,   self.PRIMARY  )
        self.setColor( QtGui.QPalette.ToolTipBase,     self.WHITE    )    
        self.setColor( QtGui.QPalette.ToolTipText,     self.WHITE    )
        self.setColor( QtGui.QPalette.Text,            self.WHITE    )
        self.setColor( QtGui.QPalette.Button,          self.PRIMARY  )
        self.setColor( QtGui.QPalette.ButtonText,      self.WHITE    )
        self.setColor( QtGui.QPalette.BrightText,      self.RED      )    
        self.setColor( QtGui.QPalette.Link,            self.TERTIARY )
        self.setColor( QtGui.QPalette.Highlight,       self.TERTIARY )
        self.setColor( QtGui.QPalette.HighlightedText, self.BLACK    )
        
    @staticmethod
    def css_rgb( colour, a=False ):
        """Get a CSS rgb or rgba string from a QtGui.QColor."""
        return ("rgba({}, {}, {}, {})" if a else "rgb({}, {}, {})").format( *colour.getRgb() )

    @staticmethod
    def set_stylesheet( _app ):
        _app.setStyleSheet(
            "QToolTip {{"
                "color: {white};"
                "background-color: {primary};"
                "border: 1px solid {white};"
            "}}"
            "QToolButton:checked {{"
                "background-color: {tertiary};"
                "border: 1px solid;"
                "border-radius: 2px;"
            "}}".format( white=QDarkPalette.css_rgb( QDarkPalette.WHITE ),
                         primary=QDarkPalette.css_rgb( QDarkPalette.PRIMARY ),
                         secondary=QDarkPalette.css_rgb( QDarkPalette.SECONDARY ),
                         tertiary=QDarkPalette.css_rgb( QDarkPalette.TERTIARY ) )
        )


    def apply2Qapp( self, _app ):
        _app.setStyle( "Fusion" )
        _app.setPalette( self )
        self.set_stylesheet( _app )


class Selectable( object ):
    TRAITS = {}
    HAS_ADV = False
    TRAIT_ORDER = []
    PRIORITY = 666

    @staticmethod
    def getTreeIcon():
        return _getStdIcon( QtWidgets.QStyle.SP_TitleBarMenuButton )

    def getAttrs( self, advanced=False ):
        return self.TRAITS


class Camera( Selectable ):

    TRAITS = {      # def, lo,  hi, name, desc, advanced?
        "fps"      : ( 60,  0,  60, "Frame rate", "Frames per second or 0 for external control", True),
        "strobe"   : ( 20,  0,  70, "Strobe Power", "Power output of strobe (Watts)", False),
        "shutter"  : (  8,  2, 250, "Shutter Period", "Shutter speed of sensor (100's of uSec)", False),
        "mtu"      : (  0,  0,   8, "Jumbo Frames", "Max Packet size (1500 + Xkb)", True),
        "iscale"   : (  0,  0,  16, "Image Decimation", "Image Scale in powers of 2 (1/2, 1/4, 1/8)", True),
        "idelay"   : ( 15,  3, 255, "Image Delay", "Delay between sending Image fragments", True),
        "threshold": (130,  0, 255, "Threshold", "Grey level threshold for centroid detection", False),
        "numdets"  : ( 13,  0,  80, "Max Centroids", "Max Centroids in a Packet (10s of Centroids)", True),
        "arpdelay" : ( 15,  0, 255, "ARP Delay", "Gratuatous ARP Delay", True),
    }
    HAS_ADV = True
    TRAIT_ORDER = [ "strobe", "shutter", "threshold", "fps", "mtu", "numdets", "iscale", "idelay", "arpdelay" ]
    PRIORITY = 5
    def __init__( self, name, id ):
        self.name = name
        self.id = id

    def getAttrs( self, advanced=False ):
        if( advanced ):
            return [ (t, self.TRAITS[ t ]) for t in self.TRAIT_ORDER ]
        else:
            return [ (t, self.TRAITS[ t ]) for t in self.TRAIT_ORDER if not self.TRAITS[t][5] ]


class Mesh( Selectable ):
    PRIORITY = 50

class QKnob( QtWidgets.QHBoxLayout ):

    valueChanged = QtCore.Signal( int ) # Spam while sliding
    valueSet     = QtCore.Signal( int ) # Mouse release, or box entry is "SET"

    class KSlider( QtWidgets.QSlider ):

        def __init__( self, parent=None ):
            super( QKnob.KSlider, self).__init__( parent )
            self.setFocusPolicy( QtCore.Qt.ClickFocus )  # can't be tabbed to
            self.setOrientation( QtCore.Qt.Horizontal )
            self.setTickPosition( QtWidgets.QSlider.NoTicks )
            self.default = 0

        def wheelEvent( self, event ):
            if( self.hasFocus() ):
                super( QKnob.KSlider, self ).wheelEvent( event )
            else:
                event.ignore()

        def focusInEvent( self, event ):
            event.accept()
            self.setFocusPolicy( QtCore.Qt.WheelFocus )
            super( QKnob.KSlider, self ).focusInEvent( event )

        def focusOutEvent( self, event ):
            event.accept()
            self.setFocusPolicy( QtCore.Qt.ClickFocus )
            super (QKnob.KSlider, self ).focusOutEvent( event )

        def mouseDoubleClickEvent( self, event ):
            if( event.modifiers() & QtCore.Qt.ControlModifier ):
                # Return to default, and do a "Set" like signal
                prev_state = self.blockSignals( True )
                self.setValue( self.default )
                self.blockSignals( prev_state )
                self.sliderReleased.emit()


    class KEdit( QtWidgets.QLineEdit ):

        def __init__( self, text, parent ):
            super( QKnob.KEdit, self ).__init__( text, parent )
            self.setFocusPolicy( QtCore.Qt.StrongFocus )
            self.returnPressed.connect( self._returnPressed )

        def wheelEvent( self, event ):
            if (self.hasFocus()):
                # dial up or down the value
                delta = 1 if event.angleDelta().y() > 0 else -1
                val = int( self.text() )
                val += delta
                self.setText( str( val ) )
                self.editingFinished.emit()
                event.accept()
            else:
                event.ignore()

        def focusInEvent( self, event ):
            event.accept()
            self.setFocusPolicy( QtCore.Qt.WheelFocus )
            super( QKnob.KEdit, self ).focusInEvent( event )

        def focusOutEvent( self, event ):
            event.accept()
            self.setFocusPolicy( QtCore.Qt.StrongFocus )
            super( QKnob.KEdit, self ).focusOutEvent( event )

        def _returnPressed( self ):
            prev_state = self.blockSignals( True )
            self.focusNextChild()
            self.blockSignals( prev_state )


    def __init__( self, parent, hi, lo, default, desc ):
        super( QKnob, self ).__init__( parent )
        self.box = self.KEdit( "", parent )
        self.slider = self.KSlider( parent )
        self.slider.default = default
        self.slider.setToolTip( desc )
        self.slider.setMinimum( lo )
        self.slider.setMaximum( hi )

        self.dialing = False
        self._value = default

        self.addWidget( self.box, 1 )
        self.addWidget( self.slider, 4 )

        self.slider.setValue( self._value )
        self.box.setText( str( self._value ) )

        self.slider.valueChanged.connect( self._sliderMove )
        self.slider.sliderReleased.connect( self._sliderSet )
        self.box.editingFinished.connect( self._boxSet )

    def _sliderMove( self, value ):
        if( self.dialing ):
            return # Hopw did we get here?

        self.dialing = True
        self.box.setText( str( value ) )
        self.valueChanged.emit( value )
        self.dialing = False

    def _sliderSet( self ):
        if( self.dialing ):
            return  # Hopw did we get here?

        self.dialing = True
        val = self.slider.value()
        if( val == self._value ):
            self.dialing = False
            return
        self._value = val
        self.box.setText( str( val ) )
        self.valueSet.emit( val )
        self.dialing = False

    def _boxSet( self ):
        # slider clamps between min / max.  need to do that here...
        if( self.dialing ):
            return  # Hopw did we get here?

        self.dialing = True
        val = int( self.box.text() )
        if( val == self._value ):
            self.dialing = False
            return
        self._value = val
        val = min( val, self.slider.maximum() )
        val = max( val, self.slider.minimum() )
        self.setSilent( val )
        self.valueSet.emit( val )
        self.dialing = False

    def setSilent( self, value ):
        """Will not emit an event"""
        prev_state = self.slider.blockSignals( True )
        self.box.setText( str( value ) )
        self.slider.setValue( value )
        self.slider.blockSignals( prev_state )

    def setValue( self, value ):
        self.box.setText( str( value ) )
        self.slider.setValue( value )

    def value( self ):
        return self.value


class QDockingAttrs( QtWidgets.QDockWidget ):

    def __init__(self, parent):
        super( QDockingAttrs, self ).__init__( "Attribute Editor", parent )
        self.setObjectName( "AtribDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea )

        # Stack Widget
        self.stack = QtWidgets.QStackedWidget()

        # currently selected type
        self._current = None

        # cache of forms
        self._forms = {}
        self._forms_adv = {}

        # None selected form
        temp = QtWidgets.QLabel( "Nothing Selected" )
        temp.setAlignment( QtCore.Qt.AlignCenter )
        self._forms[ type( None ) ] = temp
        self.stack.addWidget( temp )

        # build
        self._buildUI()

    def _buildToolbar( self ):
        atrib_tools = self._mini_main.addToolBar( "AtribTools" )
        atrib_tools.setIconSize( QtCore.QSize( 16, 16 ) )
        atrib_tools.setMovable( False )

        # toggle Group for application mode
        group = QtWidgets.QButtonGroup( self )

        self.change_sel = QtWidgets.QToolButton( self )
        self.change_sel.setIcon( _getStdIcon( QtWidgets.QStyle.SP_FileDialogListView ) )
        self.change_sel.setStatusTip( "Changes Selection" )
        self.change_sel.setToolTip( "Changes Affect Selection" )
        self.change_sel.setCheckable( True )
        group.addButton( self.change_sel )

        self.change_all = QtWidgets.QToolButton( self )
        self.change_all.setIcon( _getStdIcon( QtWidgets.QStyle.SP_FileDialogDetailedView ) )
        self.change_all.setStatusTip( "Change All" )
        self.change_all.setToolTip( "Changes Affect All" )
        self.change_all.setCheckable( True )
        group.addButton( self.change_all )

        self.show_adv = QtWidgets.QToolButton( self )
        self.show_adv.setIcon( _getStdIcon( QtWidgets.QStyle.SP_FileDialogInfoView ) )
        self.show_adv.setStatusTip( "Advanced" )
        self.show_adv.setToolTip( "Show Advanced Attributes" )
        self.show_adv.setCheckable( True )

        self.reset_atr = QtWidgets.QToolButton( self )
        self.reset_atr.setIcon( _getStdIcon( QtWidgets.QStyle.SP_DialogResetButton ) )
        self.reset_atr.setStatusTip( "Reset" )
        self.reset_atr.setToolTip( "Reset to Default" )
        self.reset_atr.setCheckable( False )

        atrib_tools.addWidget( QtWidgets.QWidget() )
        atrib_tools.addWidget( self.change_sel )
        atrib_tools.addWidget( self.change_all )
        atrib_tools.addWidget( self.show_adv   )
        atrib_tools.addSeparator()
        atrib_tools.addWidget( self.reset_atr  )

        self.change_sel.setChecked( True )

    def addSelectable( self, selectable ):
        temp = self._makePanel( selectable.getAttrs() )
        self._forms[ type( selectable ) ] = temp
        self.stack.addWidget( temp )

        if( selectable.HAS_ADV ):
            temp = self._makePanel( selectable.getAttrs( True ) )
            self._forms_adv[ type( selectable ) ] = temp
            self.stack.addWidget( temp )

    def _makePanel( self, traits ):
        # make a scroll area containing the grid
        scroll = QtWidgets.QScrollArea( self )
        scroll.setWidgetResizable( True )
        area = QtWidgets.QWidget( scroll )
        scroll.setWidget( area )
        grid = QtWidgets.QGridLayout()

        # Assemble controls
        box_list = []
        for depth, data in enumerate( traits ):
            key, (default, lo, hi, name, desc, _) = data
            # Label
            lab = QtWidgets.QLabel( name )
            lab.setToolTip( key )
            grid.addWidget( lab, depth, 0 )
            # Knob
            knob = QKnob( self, hi, lo, default, desc )
            grid.addLayout( knob, depth, 1 )
            knob.valueChanged.connect( partial( self.valueChanged, key, "try" ) )
            knob.valueSet.connect( partial( self.valueSet, key, "set" ) )

            # fix [Tab] Order
            if( len( box_list ) > 0 ):
                area.setTabOrder( box_list[-1], knob.box )
            box_list.append( knob.box )

        # Loop around, if boxes available
        # if (len( box_list ) > 0):
        #     area.setTabOrder( box_list[-1], box_list[0] )

        # Complete
        area.setLayout( grid )
        return scroll

    def valueChanged( self, key, action, value ):
        # This info needs to work it's way back up to the app and MVC for the data
        print( key, action, value )
        app = self.parent()
        app.sendCNC( action, key, value )

    def valueSet( self, key, action, value ):
        print( key, action, value )
        app = self.parent()
        app.sendCNC( action, key, value )

    def selectionChanged( self, sel_list=None ):
        sel_list = sel_list or [ (None) ]  # Nothing selected
        self._current = type( sel_list[0] )
        self.updateArea()

    def updateArea( self ):
        if( self.show_adv.isChecked() ):
            if( self._current in self._forms_adv ):
                self.stack.setCurrentWidget( self._forms_adv[ self._current ] )
                return

            # if not in advanced, fall through
        if( self._current in self._forms ):
            self.stack.setCurrentWidget( self._forms[ self._current ] )
        else:
            # unidentified
            self.stack.setCurrentWidget( self._forms[ type( None ) ] )

    def _buildUI( self ):
        self._mini_main = QtWidgets.QMainWindow()
        self._mini_main.setCentralWidget( self.stack )

        self._buildToolbar()

        # set events
        self.show_adv.clicked.connect( self.updateArea )

        # Finish
        self.setWidget( self._mini_main )
        self.selectionChanged()


class QDockingLog( QtWidgets.QDockWidget ):
    
    class QPlainTextEditLogger( logging.Handler ):
        
        def __init__( self, parent ):
            super( QDockingLog.QPlainTextEditLogger, self ).__init__()
            self.qpte = QtWidgets.QPlainTextEdit( parent )
            self.qpte.setReadOnly( True )
            self.setFormatter( terse_log )

        def emit( self, record ):
            msg = self.format( record ) 
            self.qpte.appendPlainText( msg )
        
    def __init__( self, parent ):
        super( QDockingLog, self ).__init__( "Logging", parent )
        self.setObjectName( "LogDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea   |
                              QtCore.Qt.RightDockWidgetArea  |
                              QtCore.Qt.BottomDockWidgetArea |
                              QtCore.Qt.TopDockWidgetArea  )
        self.log_widget = self.QPlainTextEditLogger( self )
        self.setWidget( self.log_widget.qpte )
        logging.getLogger().addHandler( self.log_widget )


class QFlowLayout( QtWidgets.QLayout ):
    """
        Centered 'Flow' Layout based on this Qt Example:
            https://doc.qt.io/archives/qt-4.8/qt-layouts-flowlayout-example.html

    """
    def __init__( self, parent=None, margin=-1, hspacing=-1, vspacing=-1 ):
        super( QFlowLayout, self ).__init__( parent )
        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = [ ]
        self.setContentsMargins( margin, margin, margin, margin )

    def __del__( self ):
        del self._items[ : ]

    def addItem( self, item ):
        self._items.append( item )

    def horizontalSpacing( self ):
        if self._hspacing >= 0:
            return self._hspacing
        else:
            return self.smartSpacing(
                QtWidgets.QStyle.PM_LayoutHorizontalSpacing )

    def verticalSpacing( self ):
        if self._vspacing >= 0:
            return self._vspacing
        else:
            return self.smartSpacing(
                QtWidgets.QStyle.PM_LayoutVerticalSpacing )

    def count( self ):
        return len( self._items )

    def itemAt( self, index ):
        if 0 <= index < len( self._items ):
            return self._items[ index ]

    def takeAt( self, index ):
        if 0 <= index < len( self._items ):
            return self._items.pop( index )

    def expandingDirections( self ):
        return QtCore.Qt.Orientations( 0 )

    def hasHeightForWidth( self ):
        return True

    def heightForWidth( self, width ):
        return self.doLayout( QtCore.QRect( 0, 0, width, 0 ), True )

    def setGeometry( self, rect ):
        super( QFlowLayout, self ).setGeometry( rect )
        self.doLayout( rect, False )

    def sizeHint( self ):
        return self.minimumSize()

    def minimumSize( self ):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo( item.minimumSize() )
        left, top, right, bottom = self.getContentsMargins()
        size += QtCore.QSize( left + right, top + bottom )
        return size

    def doLayout( self, rect, testonly ):
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted( +left, +top, -right, -bottom )

        x = e_x = effective.x()
        y = effective.y()
        right = effective.right()

        hspace = self.horizontalSpacing()
        vspace = self.verticalSpacing()

        lineheight = 0
        widget_pos = [ [ ] ]
        curr_row = 0
        for item in self._items:
            widget = item.widget()

            if (hspace == -1):
                hspace = widget.style().layoutSpacing(
                    QtWidgets.QSizePolicy.PushButton,
                    QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal )

            if (vspace == -1):
                vspace = widget.style().layoutSpacing(
                    QtWidgets.QSizePolicy.PushButton,
                    QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical )

            width = item.sizeHint().width()
            nextX = x + width + hspace

            if (((nextX - hspace) > right) and (lineheight > 0)):
                x = e_x
                y = y + lineheight + vspace
                nextX = x + width + hspace
                lineheight = 0
                widget_pos.append( [ ] )
                curr_row += 1

            widget_pos[ curr_row ].append( (x, y, nextX) )

            x = nextX
            lineheight = max( lineheight, item.sizeHint().height() )

        if not testonly:
            # recompute each row's x to centre the row
            flat_pos = [ ]
            for row in widget_pos:
                data = row[ -1 ]
                if (len( data ) < 3):
                    continue

                extra_pad = (right - (data[ 2 ] - hspace)) // 2
                for x, y, _ in row:
                    flat_pos.append( (x + extra_pad, y) )

            # apply to widgets
            for item, (x, y) in zip( self._items, flat_pos ):
                item.setGeometry( QtCore.QRect( QtCore.QPoint( x, y ), item.sizeHint() ) )

        return y + lineheight - rect.y() + bottom

    def smartSpacing( self, pm ):
        parent = self.parent()
        if parent is None:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric( pm, None, parent )
        else:
            return parent.spacing()


class QDockingCamActivityMon( QtWidgets.QDockWidget ):

    SQUARES = [ x ** 2 for x in range( 9 ) ]

    class QCamButSettings( object ):

        def __init__( self ):
            self.BUT_SIZE = QtCore.QSize( 48, 48 )

            self.HIGH_RECT = QtCore.QRect( 1, 1, 46, 46 ) # sz -1 px
            self.BUT_RECT = QtCore.QRect( 3, 3, 41, 41 ) # sz - 3 px
            self.CHIP = QtCore.QRect( 14, 7, 18, 18 ) # 20x20 centred in BUT_RECT

            self.FONT = QtGui.QFont( "Arial", 12 )
            self.FONT.setWeight( 60 )

            self.PEN_GREY = QtGui.QPen()
            self.PEN_GREY.setColor( QtGui.QColor( 134, 132, 130 ) )
            self.PEN_GREY.setWidth( 1 )
            self.PEN_GREY.setStyle( QtCore.Qt.SolidLine )
            self.PEN_GREY.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_GREY.setJoinStyle( QtCore.Qt.RoundJoin )

            self.GRAD_GRAY = QtGui.QLinearGradient( 0, 0, 0, 38 )
            self.GRAD_GRAY.setColorAt( 0.000, QtGui.QColor( 134, 132, 130,  0 ) )
            self.GRAD_GRAY.setColorAt( 0.666, QtGui.QColor( 134, 132, 130, 32 ) )
            self.GRAD_GRAY.setColorAt( 1.000, QtGui.QColor( 134, 132, 130, 64 ) )

            self.PEN_WHITE = QtGui.QPen()
            self.PEN_WHITE.setColor( QtGui.QColor( "white" ) )
            self.PEN_WHITE.setWidthF( 1.5 )
            self.PEN_WHITE.setStyle( QtCore.Qt.SolidLine )
            self.PEN_WHITE.setCapStyle( QtCore.Qt.RoundCap )
            self.PEN_WHITE.setJoinStyle( QtCore.Qt.RoundJoin )

            self.CHIP_PATH = QtGui.QPainterPath()
            self.CHIP_PATH.addRoundedRect( self.CHIP, 2, 2 )

            self.OUT_PATH = QtGui.QPainterPath()
            self.OUT_PATH.addRoundedRect( self.BUT_RECT, 2, 2 )

            self.SEL_PATH = QtGui.QPainterPath()
            self.SEL_PATH.addRect( self.HIGH_RECT )

            self.COL_OK   = QtGui.QColor( "green" )
            self.COL_WARN = QtGui.QColor( "red" )

            self.COL_BG  = QtGui.QColor( "black" )
            self.COL_SEL = QtGui.QColor( "white" )

            self.roid_overload_limit = 5


    class QCamButton( QtWidgets.QWidget ):

        def __init__( self, parent, settings, cam_id ):
            super( QDockingCamActivityMon.QCamButton, self ).__init__( parent )

            self.setSizePolicy( QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed )

            self.cam_id = cam_id
            self.settings = settings
            self.text = str( self.cam_id )
            self.selected = False
            self.roid_count = 0

        def sizeHint( self ):
            return self.settings.BUT_SIZE

        def paintEvent( self, e ):
            painter = QtGui.QPainter( self )

            painter.setPen( self.settings.PEN_GREY )

            painter.setBrush( self.settings.GRAD_GRAY )
            painter.drawPath( self.settings.OUT_PATH )
            painter.setBrush( QtCore.Qt.NoBrush )

            if( self.roid_count > 0 ):
                if (self.roid_count >= self.settings.roid_overload_limit):
                    painter.fillPath( self.settings.CHIP_PATH, self.settings.COL_WARN )
                else:
                    painter.fillPath( self.settings.CHIP_PATH, self.settings.COL_OK )

            painter.drawPath( self.settings.CHIP_PATH )

            painter.setPen( self.settings.PEN_WHITE )
            if (self.text):
                painter.setFont( self.settings.FONT )
                painter.drawText( self.settings.BUT_RECT, QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom, self.text )

            if (self.selected):
                painter.drawPath( self.settings.SEL_PATH )


    def __init__( self, parent ):
        super( QDockingCamActivityMon, self ).__init__( "CamActivityMon", parent )
        self.setObjectName( "CamMonDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea |
                              QtCore.Qt.RightDockWidgetArea )

        self.settings = QDockingCamActivityMon.QCamButSettings()

        self.scroll_area = QtWidgets.QScrollArea( self )
        self.scroll_area.setWidgetResizable( True )
        hz = self.scroll_area.horizontalScrollBar()
        hz.setEnabled( False )
        self.scroll_area.setHorizontalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )

        self.canvas = QtWidgets.QWidget( self.scroll_area )
        self.canvas.setMinimumWidth( 150 )

        self.layout = QFlowLayout( self.canvas )

        self._populate()

        self.scroll_area.setWidget( self.canvas )
        self.setWidget( self.scroll_area )

    def addCam( self, cam_id ):
        button = QDockingCamActivityMon.QCamButton( self.canvas, self.settings, cam_id )
        self.layout.addWidget( button )
        return button

    def _populate( self ):
        for i in range( 24 ):
            button = self.addCam( i )
            if (i == 4):
                button.selected = True
            button.roid_count = i

    @staticmethod
    def genDimsSquare( num_cams ):
        """
        Determine rows / cols needed to pack num_cams into to keep square

        :param num_cams: (int) number of cameras to arrange
        :return: (int,int) Rows, Cols
        """
        x = 0
        while( QDockingCamActivityMon.SQUARES[ x ] < num_cams ):
            x += 1

        if (x > 0):
            y, r = divmod( num_cams, x )
        else:
            y, r = 0, 0

        if (r > 0):
            y += 1

        return (x, y)


class QDockingRegions( QtWidgets.QDockWidget ):

    def __init__( self, parent ):
        super( QDockingRegions, self ).__init__( "MaskRegions", parent )
        self.setObjectName( "RegionDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self._buildUI()


    def _buildUI( self ):
        self.table = QtWidgets.QTableWidget( 16, 4, self )
        self.table.setHorizontalHeaderLabels( ["X","Y","M","N"] )
        self.table.setVerticalHeaderLabels( [ "MaskZone{:0>2}".format( i+1 ) for i in range(16) ])
        self.table.setColumnWidth( 0, 40 )
        self.table.setColumnWidth( 1, 40 )
        self.table.setColumnWidth( 2, 40 )
        self.table.setColumnWidth( 3, 40 )
        self._populate()
        self.setWidget( self.table )

    def _populate( self ):
        for i in range( 16 ):
            for j in range( 4 ):
                self.table.setItem( i, j, QtWidgets.QTableWidgetItem( "0" ) )


class QDockingOutliner( QtWidgets.QDockWidget ):

    class SceneTree(  QtWidgets.QTreeWidget ):

        def __init__(self, parent ):
            super( QDockingOutliner.SceneTree, self ).__init__( parent )
            self.setSelectionBehavior( QtWidgets.QAbstractItemView.SelectRows )
            self.setSelectionMode( QtWidgets.QAbstractItemView.MultiSelection )
            self.setHeaderHidden( True )

        def selectionChanged( self, new, old ):
            # Ignore old Vs New, just directly get the selected list
            selects = self.selectionModel().selectedRows()

            app = self.parent().parent()

            app.selection_que.clear()
            if( len( selects ) > 0 ):
                for idx in selects:
                    itm = self.itemFromIndex( idx )
                    if( hasattr( itm, "_data" ) ):
                        app.selection_que.append( itm._data )
            app.updateSelection()

    def __init__( self, parent ):
        super( QDockingOutliner, self ).__init__( "Outliner", parent )
        self.setObjectName( "OutlineDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self._buildUI()

    def _populate( self ):
        example_scene = { # All a bit bogus, this needs tobe worked out from the sysman
            "Cameras" : { "Cam_01": Camera("Cam_01", 0), "Cam_02": Camera("Cam_02", 1) },
            "Scene" : { "Cube" : Mesh() }
        }
        for k, v in example_scene.items():
            first_node = QtWidgets.QTreeWidgetItem( self.tree, [k] )
            for k1, v1 in v.items():
                node = QtWidgets.QTreeWidgetItem( first_node, [k1] )
                node._data = v1

        self._expandChildren( self.tree.invisibleRootItem() )

    def _expandChildren( self, item ):
        for i in range( item.childCount() ):
            self._expandChildren( item.child( i ) )
        self.tree.expandItem( item )

    def _buildUI( self ):
        self.tree = self.SceneTree( self )
        self._populate()
        self.setWidget( self.tree )


class QMain( QtWidgets.QMainWindow ):
    
    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        # app config
        self._app.setApplicationName( "Testing Midget UI" )
        self._app.setOrganizationName( "Midget Software" )
        self._app.setOrganizationDomain( "" )
        
        # BlackStyle
        dark_fusion = QDarkPalette()
        dark_fusion.apply2Qapp( self._app )
        
        self.selection_que = []
        self.selection_observers = []
        self._actions = {}

        # Arbiter Comms channels
        # TODO: Test if Arbiter is running, spawn one if needed
        self.command = ArbiterControl()

        self._buildUI()
        self.show()
        self.logNreport( "Launched", 5000 )
        log.info( "another" )

    def sendCNC( self, verb, noun, value=None ):
        tgt_list = list( map( lambda x: x.id, self.selection_que ) )
        self.command.send( verb, noun, value, tgt_list )
        log.info( "SENT: {}, {}, {} to {}".format( verb, noun, value, tgt_list ) )
        
    def logNreport( self, msg, dwel=1200 ):
        log.info( msg )
        self.status_bar.showMessage( msg, dwel )

    def updateSelection( self ):
        # tell oservers it's changed
        for obs in self.selection_observers:
            obs.selectionChanged( self.selection_que )
            
        report = "None"
        if( len( self.selection_que ) > 0 ):
            report = "{}: {}".format( type(self.selection_que[0]), ", ".join( map( lambda x: str(x.id), self.selection_que ) ) )
        
        log.info( "Selected: {}".format( report ) )
        
    # Action CBs
    def _newFileCB( self ):
        self.textEdit.setText("")
        
    def _exitFileCB( self ):
        self.close()
        
    def _aboutHelpCB( self ):
        QtWidgets.QMessageBox.about(self, "About Midget",
            "I was born the son of a poor Filipino merchant. "
            "I remember I would sit on the stoop of my tenement brownstone "
            "on the lower East Side. I was... I was... I was... Crying!"
        )

    # UI Assembly
    def _buildStatusBar( self ):
        self.status_bar = QtWidgets.QStatusBar()
        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setRange(0, 100 )

        self.status_lbl = QtWidgets.QLabel( "" )
        
        self.status_bar.addPermanentWidget( self.status_progress, 0 )
        self.status_bar.addPermanentWidget( self.status_lbl, 0 )
        
        self.setStatusBar( self.status_bar )
        
    def _buildActions( self ):
        self._actions[ "newAction" ] = QtWidgets.QAction( QtGui.QIcon("new.png"), '&New', self )
        self._actions[ "newAction" ].setShortcut( QtGui.QKeySequence.New )
        self._actions[ "newAction" ].setStatusTip( "Create a New File" )
        self._actions[ "newAction" ].triggered.connect( self._newFileCB )

        self._actions[ "exitAction" ] = QtWidgets.QAction( QtGui.QIcon('exit.png'), 'E&xit', self )
        self._actions[ "exitAction" ].setShortcut( "Ctrl+Q" )
        self._actions[ "exitAction" ].setStatusTip( "Exit the Application" )
        self._actions[ "exitAction" ].triggered.connect( self._exitFileCB )

        self._actions[ "aboutAction" ] = QtWidgets.QAction( QtGui.QIcon('about.png'), 'A&bout', self )
        self._actions[ "aboutAction" ].setStatusTip( "Displays info about text editor" )
        self._actions[ "aboutAction" ].triggered.connect( self._aboutHelpCB )

        
    def _buildMenuBar( self ):
        # Make Menu Actions
        menu_bar = self.menuBar()
        fileMenu = menu_bar.addMenu("&File")
        fileMenu.addAction( self._actions[ "newAction" ] )
        fileMenu.addSeparator()
        fileMenu.addAction( self._actions[ "exitAction" ] )

        helpMenu = menu_bar.addMenu("&Help")
        helpMenu.addAction( self._actions[ "aboutAction" ] )
        
    def _buildToolbar( self ):
        mainToolBar = self.addToolBar( "Main" )
        mainToolBar.setMovable( False )
        mainToolBar.addAction( self._actions[ "newAction" ] )
        mainToolBar.addSeparator()

    def _buildUI( self ):
        self.setWindowTitle( "Main Window" )
        self.setGeometry( 2300, 250, 400, 300 )
        # Setup Actions
        self._buildActions()
        
        # Setup Menu Bar & Tool Bar
        self._buildMenuBar()
        self._buildToolbar()
        
        # Central Widget
        self._ctx = QGLView()
        self.setCentralWidget( self._ctx )

        # Add docables
        logDockWidget = QDockingLog( self )
        self.addDockWidget( QtCore.Qt.BottomDockWidgetArea, logDockWidget )

        outliner = QDockingOutliner( self )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, outliner )

        # setup the attribute editor = TODO: This better
        cam = Camera("anon", -1)
        mesh = Mesh()
        atribs = QDockingAttrs( self )
        self.selection_observers.append( atribs )
        atribs.addSelectable( cam )
        atribs.addSelectable( mesh )
        self.addDockWidget( QtCore.Qt.LeftDockWidgetArea, atribs )

        # Region tool
        regions = QDockingRegions( self )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, regions )

        # activity monitor
        action = QDockingCamActivityMon( self )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, action )

        # setup status bar
        self._buildStatusBar()


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
        if( fps > 120. or fps < 0.1):
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


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )


