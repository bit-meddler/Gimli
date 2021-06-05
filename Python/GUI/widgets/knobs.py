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

""" Knob controls for ui """
import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL


class KSlider( QtWidgets.QSlider ):
    """
    Special 'Knob Slider' that allows wheel scrolling when mouseover.
    Also [Ctrl]+Double click to restore default.
    """

    def __init__( self, parent=None ):
        super( KSlider, self ).__init__( parent )
        self.setFocusPolicy( QtCore.Qt.ClickFocus )  # can't be tabbed to
        self.setOrientation( QtCore.Qt.Horizontal )
        self.setTickPosition( QtWidgets.QSlider.NoTicks )
        self.default = 0

    def wheelEvent( self, event ):
        if (self.hasFocus()):
            super( KSlider, self ).wheelEvent( event )
        else:
            event.ignore()

    def focusInEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.WheelFocus )
        super( KSlider, self ).focusInEvent( event )

    def focusOutEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.ClickFocus )
        super( KSlider, self ).focusOutEvent( event )

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
        super( KEdit, self ).__init__( text, parent )
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
        super( KEdit, self ).focusInEvent( event )

    def focusOutEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.StrongFocus )
        super( KEdit, self ).focusOutEvent( event )

    def _returnPressed( self ):
        prev_state = self.blockSignals( True )
        self.focusNextChild()
        self.blockSignals( prev_state )

    def mouseDoubleClickEvent( self, event ):
        if( event.modifiers() & QtCore.Qt.ControlModifier ):
            # Return to default, and do a "Set" like signal
            prev_state = self.blockSignals( True )
            self.setText( str( self.default ) )
            self.blockSignals( prev_state )
            self.editingFinished.emit()


class KnobInt( QtWidgets.QHBoxLayout ):
    """
    A 'Knob' is a slider with a linked LineEdit for adjusting numeric values.

    It has two signals, 'valueChanged' and 'valueSet', to allow settings to be
    Previewed before being set - will keep the UNDO stack clean
    todo: more complex actions when lineEdit is click-dragged in
    """

    valueChanged = QtCore.Signal( int ) # Spam while sliding
    valueSet     = QtCore.Signal( int ) # Mouse release, or box entry is "SET"

    _CASTOR = int

    def __init__( self, parent, min, max, default, desc ):
        """
        An integer 'Knob'.  this is both a text box and a slider.

        Args:
            parent: (QtWidget) Widget this is attached to
            min: (int) min value
            max: (int) max value
            default: (int) default value.
            desc: (str) Tooltip description
        """
        super( KnobInt, self ).__init__( parent )
        self.box = KEdit( "", parent )
        self.box.default = default
        self.slider = KSlider( parent )
        self.slider.default = default
        self.slider.setToolTip( desc )
        self.slider.setMinimum( min )
        self.slider.setMaximum( max )

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
        val = self._CASTOR( self.box.text() )
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


class KnobFloat( KnobInt ):
    """
    Float Knob - Uhg QSlider is discrete only, I thought I could get away with something crafty
    """

    valueChanged = QtCore.Signal( float )  # Spam while sliding
    valueSet = QtCore.Signal( float )  # Mouse release, or box entry is "SET"

    _CASTOR = float

