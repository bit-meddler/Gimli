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


# UI Placement Helper
def getPrefDims( q_app ):
    """ Get preferred screen dimensions and preferred display screen.
        1  screen: Centre
        2+ screens:
            pick biggest
                or if both the same size, use system defined primary

        Returns:
            screen info (tuple):
                big_scr: (QScreen) The biggest or primary screen

                tgt_rect: (QRect) Centered rect in the big_scr
    """
    # Find Physicaly biggest Screen
    big_scr = q_app.primaryScreen()
    big_dim = q_app.primaryScreen().physicalSize().width()
    screens = q_app.screens()
    for screen in screens:
        width = screen.physicalSize().width()
        if (width > big_dim):
            big_scr = screen
            big_dim = width

    # set window to fit nicely inside it
    desk_w = big_scr.availableGeometry().width()
    desk_h = big_scr.availableGeometry().height()
    width = desk_w * 0.75
    height = desk_h * 0.75

    # place in the screen's available canvas
    x = ((desk_w - width) / 2) + big_scr.availableGeometry().left()
    y = ((desk_h - height) / 2) + big_scr.availableGeometry().top()

    tgt_rect = QtCore.QRect( x, y, width, height )

    return (big_scr, tgt_rect)


# - Scene Model --------------------------------------------------------------------------------------------------------

ROLE_INTERNAL_ID = QtCore.Qt.UserRole + 0
ROLE_NUMROIDS    = QtCore.Qt.UserRole + 1
ROLE_TYPEINFO    = QtCore.Qt.UserRole + 2

class SceneModel( QtCore.QAbstractItemModel ):

    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def __init__( self, root=None, parent=None ):
        super( SceneModel, self ).__init__( parent )
        self.root = root or Nodes.factory( Nodes.TYPE_ROOT, "Root" )
        self.root_idx = self.createIndex( self.root.row(), 0, self.root )
        self.expected_nodes = set( Nodes.TYPE_ROOT )
        self.groups = {} # lut of TYPE:GroupNode

        # Incoming mocap frame (dets, strides, labels)
        # Thread lock?
        self.frame_count = 0
        self.dets_time = 0
        self.dets_strides = []
        self.dets_dets = []
        self.dets_count = []

    def registerNode( self, node_type ):
        # add to expected set
        self.expected_nodes.add( node_type )

        # work out dep chain
        dep_chain = []
        node = node_type
        while node in Nodes.NODE_DEPENDANCIES:
            dep_chain.append( Nodes.NODE_DEPENDANCIES[ node ] )
            node = Nodes.NODE_DEPENDANCIES[ node ]

        # then backwards to build hierarchy if it doesn't exist
        last_parent = self.root
        while( len( dep_chain ) > 0 ):
            node_t = dep_chain.pop()
            if( node_t not in self.groups ):
                last_parent = Nodes.factory( node_t, None, parent=last_parent )
                self.groups[ node_t ] = last_parent

    def addNodeTo( self, new_node, parent_node ):
        parent_idx = self.genIndex( parent_node )
        position = parent_node.childCount()
        name = parent_node.safeChildName( new_node.name )
        new_node.name = name

        self.beginInsertRows( parent_idx, position, position )
        parent_node.insertChild( position, new_node )
        self.endInsertRows()

    def addNode( self, new_node ):
        node_gp = Nodes.NODE_DEPENDANCIES.get( new_node.type_info, Nodes.TYPE_ROOT )
        parent_node = self.groups.get( node_gp, self.root )
        self.addNodeTo( new_node, parent_node )

    def dump( self ):
        print( self.root._log() )
        print( self.groups )

    def populatedGroups( self ):
        pop = 0
        for grp in self.root._children:
            if (grp.hasChildren()):
                pop += 1
        return pop

    def emitUpdate( self ):
        first = self.createIndex( 0, 0, self.root )
        last  = self.createIndex( self.root._child_count, 0, self.root )
        self.dataChanged.emit( first, last, [ ] )

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
                return None #node.icon

        elif( role == ROLE_INTERNAL_ID ):
            return node.data.get( "ID", 0 )

        elif( role == ROLE_NUMROIDS ):
            cam_id = node.data.get( "ID", 0 )
            return self.dets_count[ cam_id ]

        elif( role == ROLE_TYPEINFO ):
            return node.type_info

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

        elif( node.parent == None ): # None parent == root
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



