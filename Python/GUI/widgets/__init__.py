"""
widgets - simple widgets live here, more complex things get their own file

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL


class QKnob( QtWidgets.QHBoxLayout ):
    """
    'QKnob' is a slider with a linked LineEdit for adjusting numeric values.

    It has two signals, 'valueChanged' and 'valueSet', to allow settings to be
    Previewed before being set - will keep the UNDO stack clean
    todo: a float version
    todo: more complex actions when lineEdit is click-dragged in
    """

    valueChanged = QtCore.Signal( int ) # Spam while sliding
    valueSet     = QtCore.Signal( int ) # Mouse release, or box entry is "SET"

    class KSlider( QtWidgets.QSlider ):
        """
        Special 'Knob Slider' that allows wheel scrolling when mouseover.
        Also [Ctrl]+Double click to restore default.
        """

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
        """
        Special 'Knob Editor' that plays nice with mouse wheel events.
        """
        # todo: [Shift] [Alt] [Ctrl] Modifiers and MMB Click drag
        # todo: [Ctrl] LMB reset to default
        # todo: +=/-= semantics
        # Maybe write an improved lineedit with these functions??
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
        """
        An integer 'Knob'.  this is both a text box and a slider.

        Args:
            parent: (QtWidget) Widget this is attached to
            hi: (int) max value
            lo: (int) min value
            default: (int) default value.
            desc: (str) Tooltip description
        """
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
            return # How did we get here?

        self.dialing = True
        self.box.setText( str( value ) )
        self.valueChanged.emit( value )
        self.dialing = False

    def _sliderSet( self ):
        if( self.dialing ):
            return  # How did we get here?

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
            return  # How did we get here?

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


class QFlowLayout( QtWidgets.QLayout ):
    """
        Centered 'Flow' Layout based on this Qt Example:
            https://doc.qt.io/archives/qt-4.8/qt-layouts-flowlayout-example.html

        NOTE: This may be superseded by an implementation of 'TiledListView'

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