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

"""
widgets - simple widgets live here, more complex things get their own file.

For self configuring components (edits, knobs, dials) the actual functional bit
must be named "box", for [Tab] skip ordering at a higher level.

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from GUI.nodeTraits import *
from GUI.widgets.knobs import KnobInt, KnobFloat
from GUI.widgets.edits import EditInt, EditFloat, EditCombo, EditBool, EditStr


TRAIT_UI_LUT = {
    TRAIT_TYPE_INT   : {
        TRAIT_STYLE_EDIT : EditInt,
        TRAIT_STYLE_KNOB : KnobInt,
    },
    TRAIT_TYPE_FLOAT : {
        TRAIT_STYLE_EDIT : EditFloat,
        TRAIT_STYLE_KNOB : KnobFloat,
    },
    TRAIT_TYPE_LIST : {
        TRAIT_STYLE_EDIT : EditCombo,
    },
    TRAIT_TYPE_BOOL : {
        TRAIT_STYLE_EDIT : EditBool,
    },
    TRAIT_TYPE_STR : {
        TRAIT_STYLE_EDIT : EditStr,
    },
}

CONTINUOUS_TRATES = ( TRAIT_TYPE_INT, TRAIT_TYPE_FLOAT, )
DISCRETE_TRAITS   = ( TRAIT_TYPE_LIST, )
SINGULAR_TRAITS   = ( TRAIT_TYPE_BOOL, TRAIT_TYPE_STR, )


def uiTraitFactory( owner, trait ):
    type_styles = TRAIT_UI_LUT[ trait.TYPE_INFO ]
    # if a style is missing, fall back
    style = trait.style
    while( style not in type_styles ):
        style -= 1
    ControlClass = type_styles[ style ]

    # correctly instantiate
    control = None
    if( trait.TYPE_INFO in CONTINUOUS_TRATES ):
        control = ControlClass( owner, trait.min, trait.max, trait.default, trait.desc )

    elif( trait.TYPE_INFO in DISCRETE_TRAITS ):
        control = ControlClass( owner, trait.options, trait.default, trait.desc )

    elif( trait.TYPE_INFO in SINGULAR_TRAITS ):
        control = ControlClass( owner, trait.default, trait.desc )

    return control


# ----------------------------------------------------------------------------------------------------------------------
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

