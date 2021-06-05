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

import sys
from PySide2 import QtGui, QtCore, QtWidgets

class BitEdit( QtWidgets.QLineEdit ):
    
    def __init__( self, parent, name, bits_descriptor, display_mode="BITS" ):
        super( BitEdit, self ).__init__( parent )
        
        self._mode = display_mode
        
        # the data
        self.bits, self.mask = [], -1
        
        # bit info
        self._bits = {}
        self._bit_order = []
        
        # set RO and align
        self.setReadOnly( True )
        self.setAlignment( QtCore.Qt.AlignRight )
        
        # set Monospaced Font
        font = QtGui.QFont("")
        font.setStyleHint( QtGui.QFont.TypeWriter )
        if( self._mode == "WORD" ):
            font.setPointSize( 14 )
        else:
            font.setPointSize( 22 )
        self.setFont( font )

        # context Menu
        self._ctx_men = QtWidgets.QMenu( self, name )

        # setup the bits
        for order, bit in enumerate( bits_descriptor ):
            bit_name = bit[ "KEYNAME" ]
            self._bit_order.append( bit_name )
            self._bits[ bit_name ] = {}
            self._bits[ bit_name ].update( bit )
            
            if( "VALUE" not in self._bits[ bit_name ] ):
                self._bits[ bit_name ][ "VALUE" ] = 0

            if( "FIELD" not in self._bits[ bit_name ] ):
                self._bits[ bit_name ][ "FIELD" ] = 2**order

            bit_action = QtWidgets.QAction( bit[ "NAME" ], self._ctx_men, checkable=True )
            
            if( "DESC" in self._bits[ bit_name ] ):
                bit_action.setToolTip( self._bits[ bit_name ][ "DESC" ] )
                    
            bit_action.setChecked( bool( self._bits[ bit_name ][ "VALUE" ] == 1 ) )
                                       
            bit_action.triggered.connect( self.onHideMenu )
            
            self._bits[ bit_name ][ "ACTION" ] = bit_action
            self._ctx_men.addAction( bit_action )

        # Ensure we have space to display
        self.setMinimumWidth( self._computeWidth() )

        # setup the events
        self.setContextMenuPolicy( QtCore.Qt.CustomContextMenu )
        self.customContextMenuRequested.connect( self.onContextMenu )

        # set inital state
        self.bits, self.mask = self.compute()
        self.updateDisplay()
        
    def onContextMenu( self, point ):
        self._ctx_men.exec_( self.mapToGlobal( point ) )
        
    def onHideMenu( self ):
        self.bits, self.mask = self.compute()
        self.updateDisplay()
        
    def updateDisplay( self ):
        if( self._mode == "MASK" ):
            val = str( self.mask )

        elif( self._mode == "BITS" ):
            val = ""
            for bit in reversed( self.bits ):
                val += "1" if bit else "0"
                
        elif( self._mode == "HEX" ):
            val = "0x{:0>4X}".format( self.mask )

        elif( self._mode == "WORD" ):
            active = [ self._bits[ b ][ "DESC" ]
                       for b in self._bit_order
                       if self._bits[ b ][ "ACTION" ].isChecked() ]
            
            val = " ,".join( active )
            
        self.setText( val )
        
    def _computeWidth( self ):
        big_txt = ""
        big_num = 0
        
        for info in self._bits.values():
            big_num += info[ "FIELD" ]
            
        if( self._mode == "MASK" ):
            big_txt = str( big_num )

        elif( self._mode == "BITS" ):
            big_txt = "1" * len( self._bits )
                
        elif( self._mode == "HEX" ):
            big_txt = "0x{:0>4X}".format( big_num )

        elif( self._mode == "WORD" ):
            all = [ self._bits[ b ][ "DESC" ]
                       for b in self._bit_order ]
            
            big_txt = " ,".join( all )
            
        big_txt += "XX"
        metrics = QtGui.QFontMetrics( self.font() )

        return metrics.width( big_txt )
        
    def compute( self ):
        bits = []
        mask = 0
        # create a bitfield of the bits
        for bit in self._bit_order:
            if( self._bits[ bit ][ "ACTION" ].isChecked() ):
                bits.append( True )
                mask += self._bits[ bit ][ "FIELD" ]
            else:
                bits.append( False )

        return (bits, mask)


class Main( QtWidgets.QMainWindow ):
    
    def __init__( self, parent=None ):
        super( Main, self ).__init__( parent )
        
        the_bits = [
            { "KEYNAME" : "ones",
              "NAME"    : "Black",
              "DESC"    : "1s",
              "FIELD"   : 1, },
            { "KEYNAME" : "twos",
              "NAME"    : "Brown",
              "DESC"    : "2s",
              "FIELD"   : 2, },
            { "KEYNAME" : "fours",
              "NAME"    : "Red",
              "DESC"    : "4s",
              "FIELD"   : 4, },
            { "KEYNAME" : "eights",
              "NAME"    : "Orange",
              "DESC"    : "8s",
              "FIELD"   : 8, },
            
        ]
        the_bits = [
            { "KEYNAME" : "tx",
              "NAME"    : "Translate X",
              "DESC"    : "tx",
              "VALUE"   : 1, },
            { "KEYNAME" : "ty",
              "NAME"    : "Translate Y",
              "DESC"    : "ty",
              "VALUE"   : 1, },
            { "KEYNAME" : "tz",
              "NAME"    : "Translate Z",
              "DESC"    : "tz",
              "VALUE"   : 1, },
            { "KEYNAME" : "rx",
              "NAME"    : "Rotate X",
              "DESC"    : "rx",
              "VALUE"   : 1, },
            { "KEYNAME" : "ry",
              "NAME"    : "Rotate Y",
              "DESC"    : "ry",
              "VALUE"   : 1, },
            { "KEYNAME" : "rz",
              "NAME"    : "Rotate Z",
              "DESC"    : "rz",
              "VALUE"   : 1, },
            
            
        ]
        self.my_edit = BitEdit( self, "My Bits", the_bits, display_mode="WORD" )


if( __name__ == '__main__' ):
    app = QtWidgets.QApplication( sys.argv )
    form = Main()
    form.show()
    app.exec_()
