""" Widget Inspector """

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2 import QtGui
import sys

# Boilerplate from GUI -------------------------------------------------
class QPaletteOveride( QtGui.QPalette ):
    """
        Palette setup.  Can be easily updated with new themes by overloading the
        class-level "CONSTS"
    """
    TEXT      = QtGui.QColor( 255, 255, 255 )
    TEXT_INV  = QtGui.QColor( 0, 0, 0 )
    TEXT_HI   = QtGui.QColor( 255, 0, 0 )
    PRIMARY   = QtGui.QColor( 53, 53, 53 )
    SECONDARY = QtGui.QColor( 35, 35, 35 )
    TERTIARY  = QtGui.QColor( 87, 140, 178 )
    CSS_FMT   =  """QToolTip {{
                        color: {text};
                        background-color: {primary};
                        border: 1px solid {text};
                    }}
                    QToolButton:checked {{
                        background-color: {tertiary};
                        border: 1px solid;
                        border-radius: 2px;
                    }}"""

    def __init__( self, *args ):
        super( QPaletteOveride, self ).__init__( *args )

        self.setColor( QtGui.QPalette.Window,          self.PRIMARY )
        self.setColor( QtGui.QPalette.WindowText,      self.TEXT )
        self.setColor( QtGui.QPalette.Base,            self.SECONDARY )
        self.setColor( QtGui.QPalette.AlternateBase,   self.PRIMARY )
        self.setColor( QtGui.QPalette.ToolTipBase,     self.TEXT )
        self.setColor( QtGui.QPalette.ToolTipText,     self.TEXT )
        self.setColor( QtGui.QPalette.Text,            self.TEXT )
        self.setColor( QtGui.QPalette.Button,          self.PRIMARY )
        self.setColor( QtGui.QPalette.ButtonText,      self.TEXT )
        self.setColor( QtGui.QPalette.BrightText,      self.TEXT_HI )
        self.setColor( QtGui.QPalette.Link,            self.TERTIARY )
        self.setColor( QtGui.QPalette.Highlight,       self.TERTIARY )
        self.setColor( QtGui.QPalette.HighlightedText, self.TEXT_INV )

    @staticmethod
    def css_rgb( colour, a=False ):
        """Get a CSS rgb or rgba string from a QtGui.QColor."""
        return ("rgba({}, {}, {}, {})" if a else "rgb({}, {}, {})").format( *colour.getRgb() )

    @staticmethod
    def set_stylesheet( _app ):
        _app.setStyleSheet(
            QPaletteOveride.CSS_FMT.format(
                text=QPaletteOveride.css_rgb( QPaletteOveride.TEXT ),
                primary=QPaletteOveride.css_rgb( QPaletteOveride.PRIMARY ),
                secondary=QPaletteOveride.css_rgb( QPaletteOveride.SECONDARY ),
                tertiary=QPaletteOveride.css_rgb( QPaletteOveride.TERTIARY ) )
        )

    def apply2Qapp( self, _app ):
        _app.setStyle( "Fusion" )
        _app.setPalette( self )
        self.set_stylesheet( _app )


class QDarkPalette( QPaletteOveride ):
    """ Dark palette for a Qt application, meant to be used with the Fusion theme.
        from Gist: https://gist.github.com/lschmierer/443b8e21ad93e2a2d7eb
    """
    TEXT      = QtGui.QColor( 255, 255, 255 )
    TEXT_INV  = QtGui.QColor( 0, 0, 0 )
    TEXT_HI   = QtGui.QColor( 255, 0, 0 )
    PRIMARY   = QtGui.QColor( 53, 53, 53 )
    SECONDARY = QtGui.QColor( 35, 35, 35 )
    TERTIARY  = QtGui.QColor( 87, 140, 178 )

    def __init__( self, *args ):
        super( QDarkPalette, self ).__init__( *args )

class QBrownPalette( QPaletteOveride ):
    """ Beige Theme, apparently it's cool
    """
    TEXT      = QtGui.QColor( 255, 255, 255 )
    TEXT_INV  = QtGui.QColor( 0, 0, 0 )
    TEXT_HI   = QtGui.QColor( 225, 255, 35 )
    PRIMARY   = QtGui.QColor( 51, 36, 18  )
    SECONDARY = QtGui.QColor( 22, 16, 8 )
    TERTIARY  = QtGui.QColor( 187, 214, 29 )

    def __init__( self, *args ):
        super( QBrownPalette, self ).__init__( *args )

# - Real work here ----------------------------------------------------------
paletteRoles =  {
     "Window"  :          QPalette.Window ,
     "WindowText"  :      QPalette.WindowText ,
     "Base"  :            QPalette.Base ,
     "AlternateBase"  :   QPalette.AlternateBase ,
     "Text"  :            QPalette.Text ,
     "Button"  :          QPalette.Button ,
     "ButtonText"  :      QPalette.ButtonText ,
     "BrightText"  :      QPalette.BrightText ,
     "Light"  :           QPalette.Light ,
     "Midlight"  :        QPalette.Midlight ,
     "Dark"  :            QPalette.Dark ,
     "Mid"  :             QPalette.Mid ,
     "Shadow"  :          QPalette.Shadow ,
     "Highlight"  :       QPalette.Highlight ,
     "HighlightedText"  : QPalette.HighlightedText ,
     "Link"  :            QPalette.Link ,
     "LinkVisited"  :     QPalette.LinkVisited ,
}

paletteGroups = {
    "Active" :    QPalette.Active ,
    "Inactive" :   QPalette.Inactive ,
    "Disabled" :  QPalette.Disabled ,
}

class MyGui(QMainWindow):
    
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.palette = QDarkPalette()
        #self.palette = QBrownPalette()
        self.palette.apply2Qapp( app )
        
        tab_wid = QTableWidget( len( paletteRoles ), len( paletteGroups ) + 1 )
        tab_wid.setSelectionMode( QTableWidget.NoSelection )
        tab_wid.setSortingEnabled( False )

        palette = app.palette()
        col_black = QColor( "Black" )
        
        for i, (role, rid) in enumerate( paletteRoles.items() ):

            tab_wid.setItem( i, 0, QTableWidgetItem( str(role) ) )

            for j, (group, gid) in enumerate( paletteGroups.items() ):
               
                color = palette.color( gid, rid )
                pixmap = QPixmap(32, 32)
                painter = QPainter( pixmap )
                painter.fillRect( 0, 0, 31, 31, col_black )
                painter.fillRect( 1, 1, 30, 30, color )
                rgb = "{} {} {}".format( color.red(), color.green(), color.blue() )
                tab_wid.setItem( i, j + 1, QTableWidgetItem( pixmap, rgb ) )
                painter.end()
                
        self.setCentralWidget( tab_wid )
        tab_wid.resizeColumnsToContents()

        self.show()
        



app = QApplication( sys.argv )
mygui = MyGui()
sys.exit( app.exec_() )   
