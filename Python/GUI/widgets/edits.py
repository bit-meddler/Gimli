""" Edit Box controls for ui
    Going to rehash the Properties editor: https://github.com/bit-meddler/shogunScripts/blob/master/dayMakerV2/QProperties.py

"""
import logging
from PySide2 import QtGui, QtCore, QtWidgets
import re


class DragBoxInt( QtWidgets.QSpinBox ):

    def __init__( self,  parent, min, max, default, desc ):
        super( DragBoxInt, self ).__init__( parent )

        self.default = default
        self.min = min
        self.max = max
        self.setToolTip( desc )

        # ToDo: Do these need to be computed from min/max range?
        self.step_lo = 1
        self.step_mid = 5
        self.step_hi = 10
        self.step_scale = 16.

        # take any updates to the range
        self.setRange( self.min, self.max )

        # Spinner Mousing
        self._mousing = False
        self._start_pos = None
        self._start_val = None

        # initialize to Default
        self.setValue( self.default )

        # Wheel focus & return to next element
        self.setFocusPolicy( QtCore.Qt.StrongFocus )

        # Only fire change when enter pressed (so it won't spam when typing
        self.setKeyboardTracking( False )
        self.installEventFilter( self )

    def wheelEvent( self, event ):
        if (self.hasFocus()):
            # dial up or down the value
            delta = 1 if event.angleDelta().y() > 0 else -1
            val = int( self.text() )
            val += delta
            prev_state = self.blockSignals( True )
            self.setValue( val )
            self.blockSignals( prev_state )
            self.editingFinished.emit()
            event.accept()
        else:
            event.ignore()

    def focusInEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.WheelFocus )
        super( DragBoxInt, self ).focusInEvent( event )

    def focusOutEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.StrongFocus )
        super( DragBoxInt, self ).focusOutEvent( event )

    def mousePressEvent( self, event ):
        super( DragBoxInt, self ).mousePressEvent( event )
        if (event.button() & QtCore.Qt.MiddleButton):
            self._mousing = True
            self._start_pos = event.pos()
            self.setCursor( QtCore.Qt.SizeVerCursor )
            self._start_val = self.value()

    def mouseMoveEvent( self, event ):
        if not self._mousing:
            return

        mods = event.modifiers()

        delta = self.step_mid
        if( mods & QtCore.Qt.ShiftModifier ):
            delta = self.step_lo

        elif( mods & QtCore.Qt.AltModifier ):
            delta = self.step_hi

        # TODO: Do this nicely
        change = (event.pos().y() - self._start_pos.y())
        val = self._start_val + int( -1. * (change / self.step_scale) * delta )
        self.setValue( val )

    def mouseReleaseEvent( self, event ):
        super( DragBoxInt, self ).mouseReleaseEvent( event )
        self._mousing = False
        self.unsetCursor()
        self.editingFinished.emit()

    def mouseDoubleClickEvent( self, event ):
        """ restore default on [Ctrl] Double click """
        # todo: we never reach here!
        if( event.modifiers() & QtCore.Qt.ControlModifier ):
            # Return to default, and do a "Set" like signal
            prev_state = self.blockSignals( True )
            self.setValue( self.default )
            self.blockSignals( prev_state )
            self.editingFinished.emit()

    def eventFilter( self, widget, event ):
        # Advance focus on "Enter" key press
        if( event.type() == QtCore.QEvent.KeyPress ):
            key = event.key()
            if( key == QtCore.Qt.Key_Return ):
                prev_state = self.blockSignals( True )
                self.focusNextChild()
                self.blockSignals( prev_state )
                self.editingFinished.emit()
                return True

        return False


class DragBoxFloat( QtWidgets.QDoubleSpinBox ):

    def __init__( self,  parent, min, max, default, desc ):
        super( DragBoxFloat, self ).__init__( parent )

        self.default = default
        self.min = min
        self.max = max
        self.setToolTip( desc )

        # ToDo: Do these need to be computed from min/max range?
        self.step_lo = 1
        self.step_mid = 5
        self.step_hi = 10
        self.step_scale = 16.

        # take any updates to the range
        self.setRange( self.min, self.max )

        # Spinner Mousing
        self._mousing = False
        self._start_pos = None
        self._start_val = None

        # initialize to Default
        self.setValue( self.default )

        # Wheel focus & return to next element
        self.setFocusPolicy( QtCore.Qt.StrongFocus )

        # Only fire change when enter pressed (so it won't spam when typing
        self.setKeyboardTracking( False )
        self.installEventFilter( self )

    def wheelEvent( self, event ):
        if (self.hasFocus()):
            # dial up or down the value
            delta = 1 if event.angleDelta().y() > 0 else -1
            val = float( self.text() )
            val += delta
            prev_state = self.blockSignals( True )
            self.setValue( val )
            self.blockSignals( prev_state )
            self.editingFinished.emit()
            event.accept()
        else:
            event.ignore()

    def focusInEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.WheelFocus )
        super( DragBoxFloat, self ).focusInEvent( event )

    def focusOutEvent( self, event ):
        event.accept()
        self.setFocusPolicy( QtCore.Qt.StrongFocus )
        super( DragBoxFloat, self ).focusOutEvent( event )

    def mousePressEvent( self, event ):
        super( DragBoxFloat, self ).mousePressEvent( event )
        if (event.button() & QtCore.Qt.MiddleButton):
            self._mousing = True
            self._start_pos = event.pos()
            self.setCursor( QtCore.Qt.SizeVerCursor )
            self._start_val = self.value()

    def mouseMoveEvent( self, event ):
        if not self._mousing:
            return

        mods = event.modifiers()

        delta = self.step_mid
        if (mods & QtCore.Qt.ShiftModifier):
            delta = self.step_lo

        elif (mods & QtCore.Qt.AltModifier):
            delta = self.step_hi

        # TODO: Do this nicely
        change = (event.pos().y() - self._start_pos.y())
        val = self._start_val + float( -1. * (change / self.step_scale) * delta )
        self.setValue( val )

    def mouseReleaseEvent( self, event ):
        super( DragBoxFloat, self ).mouseReleaseEvent( event )
        self._mousing = False
        self.unsetCursor()
        self.editingFinished.emit()

    def eventFilter( self, widget, event ):
        # Advance focus on "Enter" key press
        if (event.type() == QtCore.QEvent.KeyPress):
            key = event.key()
            if (key == QtCore.Qt.Key_Return):
                prev_state = self.blockSignals( True )
                self.focusNextChild()
                self.blockSignals( prev_state )
                self.editingFinished.emit()
                return True

        return False

    def mouseDoubleClickEvent( self, event ):
        """ restore default on [Ctrl] Double click """
        # todo: we never reach here!
        if (event.modifiers() & QtCore.Qt.ControlModifier):
            # Return to default, and do a "Set" like signal
            prev_state = self.blockSignals( True )
            self.setValue( self.default )
            self.blockSignals( prev_state )
            self.editingFinished.emit()

class SMathValidator( QtGui.QValidator ):
    """
        Accept Scientific notation in the lineEdit.
        Also interprets basic expressions ( +=, -=, /=, *=) followed by a value
        which may also be in scientific notation
    """

    def __init__( self ):
        super( SMathValidator, self ).__init__()
        self._floatOK = re.compile( r"(([+\-*\\]\=)?([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)" )

    def _test( self, text ):
        matched = self._floatOK.search( text )
        if matched:  # Guard for Non-Matching
            return (matched.groups()[ 0 ] == text)
        else:
            return False

    def validate( self, text, pos ):
        if (self._test( text )):
            return self.State.Acceptable

        elif ((text == "") or (text[ pos - 1 ] in 'e.-+/*=')):
            return self.State.Intermediate

        return self.State.Invalid

    def valueFromText( self, text, previous=0. ):
        matched = self._floatOK.search( text )
        match, expression, mantissa, _, exponent = matched.groups()
        value = previous
        if( expression is not None ):
            mantissa = 1 if mantissa == None else mantissa
            exponent = "" if exponent == None else exponent
            change = float( mantissa + exponent )  # rebuild sci notation

            if (expression == "+="):
                value += change

            elif (expression == "-="):
                value -= change

            elif (expression == "*="):
                value *= change

            elif (expression == "/="):
                value /= change

        else:
            value = float( match )

        return value

    def fixup( self, text ):
        matched = self._floatOK.search( text )
        if matched:  # Guard for Non-Matching
            return matched.groups()[ 0 ]
        else:
            return ""


class EditInt( QtWidgets.QHBoxLayout ):

    valueChanged = QtCore.Signal( int ) # Spam while sliding
    valueSet     = QtCore.Signal( int ) # Mouse release, or box entry is "SET"

    def __init__( self, parent, min, max, default, desc ):
        super( EditInt, self ).__init__( parent )

        self.box = DragBoxInt( parent, min, max, default, desc )
        self.addWidget( self.box, 1 )

        self.box.valueChanged.connect( self._try )
        self.box.editingFinished.connect( self._set )

    def _try( self, *_args ):
        self.valueChanged.emit( self.box.value() )

    def _set( self ):
        self.valueSet.emit( self.box.value() )


class EditFloat( QtWidgets.QHBoxLayout ):

    valueChanged = QtCore.Signal( float ) # Spam while sliding
    valueSet     = QtCore.Signal( float ) # Mouse release, or box entry is "SET"

    def __init__( self, parent, min, max, default, desc ):
        super( EditFloat, self ).__init__( parent )

        self.box = DragBoxFloat( parent, min, max, default, desc )
        self.addWidget( self.box, 1 )

        self.box.valueChanged.connect( self._try )
        self.box.editingFinished.connect( self._set )

    def _try( self, *_args ):
        self.valueChanged.emit( self.box.value() )

    def _set( self ):
        self.valueSet.emit( self.box.value() )
