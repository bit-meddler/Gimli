"""
    GUI - central UI helpers across the Project

    Also the all important SceneGraph and AbstractItemModels should be here
"""
import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from Core import Nodes

# Look and Feel Helpers
def getStdIcon( icon_enum ):
    return QtGui.QIcon( QtWidgets.QApplication.style().standardIcon( icon_enum ) )

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




# - Scene Model ----------------------------------------------------------------

class SceneModel( QtCore.QAbstractItemModel ):
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def __init__( self, root, parent=None ):
        super( SceneModel, self ).__init__( parent )
        self.root = Nodes.factory( Nodes.TYPE_ROOT, "Root" )

    def populatedGroups( self ):
        pop = 0
        for grp in self.root._children:
            if (grp.hasChildren()):
                pop += 1
        return pop

    def rowCount( self, parent ):
        node = self.getNodeIndex( parent )

        # way to hide un populated grp nodes??
        # if( node == self.root ):
        #    return self.populatedGroups()
        # But that would change the subsequent indexing!

        return node._child_count

    def columnCount( self, parent ):
        return 1

    def data( self, index, role ):
        if (not index.isValid()):
            return None

        node = index.internalPointer()
        col = index.column()

        if (role == QtCore.Qt.DisplayRole):
            return node.name

        elif (role == QtCore.Qt.DecorationRole):
            if (col == 0):
                return node.icon

        elif (role == QtCore.Qt.ToolTipRole):
            return node.fullPath()

    def headerData( self, section, orient, role ):
        if (role == QtCore.Qt.DisplayRole):
            return ""

    def flags( self, index ):
        return self.DEFAULT_FLAGS

    def parent( self, index ):
        node = index.internalPointer()

        if (node.parent == self.root):
            return QtCore.QModelIndex()

        return self.createIndex( node.parent.row(), 0, node.parent )

    def genIndex( self, node ):
        return self.createIndex( node.row(), 0, node )

    def index( self, row, col, parent ):
        if (not self.hasIndex( row, col, parent )):
            return QtCore.QModelIndex()

        parent_node = self.getNodeIndex( parent )

        child = parent_node.getChild( row )

        if (child is not None):
            return self.createIndex( row, col, child )
        else:
            return QtCore.QModelIndex()

    def getNodeIndex( self, index ):
        if (index.isValid()):
            node = index.internalPointer()
            if (node is not None):
                return node

        return self.root

    def insertRows( self, position, rows, parent=QtCore.QModelIndex(), node_type=Nodes.TYPE_NODE ):
        parent_node = self.getNodeIndex( parent )
        res = True
        self.beginInsertRows( parent, position, position + rows - 1 )
        for row in range( rows ):
            name = parent_node.safeChildName( "NewNode" )
            child = Nodes.factory( node_type, name )
            res &= parent_node.insertChild( position + row, child )
        self.endInsertRows()
        return res

    def removeRows( self, position, rows, parent=QtCore.QModelIndex() ):
        parent_node = self.getNodeIndex( parent )
        res = True
        self.beginRemoveRows( parent, position, position + rows - 1 )
        for row in range( rows ):
            res &= parent_node.removeChild( position )
        self.endRemoveRows()
        return res




# - Selectables - These need to become "UI Nodes" or something
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

    # todo load from comms, or move comms.CAMERA_TRAITS in here
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