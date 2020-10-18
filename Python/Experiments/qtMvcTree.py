"""
    qtMvcTree.py - New experiment based on Yasin Uludag's tutorials: https://www.youtube.com/watch?v=VcN94yMOkyU&t=2s
"""
import logging
import os
import sys

from PySide2 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication() # Trick to get "Standard Icons"

def getStdIcon( icon_enum ):
    return QtGui.QIcon( QtWidgets.QApplication.style().standardIcon( icon_enum ) )

class Node( object ):

    TYPE_NODE = "NODE"
    TYPE_ROOT = "ROOT"
    TYPE_CAMERA = "CAMERA"
    TYPE_VIEW = "VIEW"
    TYPE_SKELETON = "SKELETON"
    TYPE_GROUP_CAMERA = "GP_CAMERA"
    TYPE_GROUP_VIEW = "GP_VIEW"
    TYPE_GROUP_SKELETONS = "GP_SKELETON"

    DEFAULT_ICON = None
    
    def __init__( self, name, parent=None ):
        self.name = name
        self._children = []
        self._child_count = 0
        self.parent = parent

        if( parent is not None ):
            parent.addChild( self )
            
        self.icon = self.DEFAULT_ICON
        
    def typeInfo( self ):
        return Node.TYPE_NODE
            
    def addChild( self, child ):
        self._children.append( child )
        self._child_count += 1

    def insertChild( self, position, child ):
        if( (position < 0) or (position > len( self._children )) ):
            return False # Bad target index

        self._children.insert( position, child )
        child.parent = self
        self._child_count += 1
        return True
    
    def removeChild( self, position ):
        if( (position < 0) or (position > len( self._children )) ):
            return False # Bad target index

        child = self._children.pop( position )
        self._child_count -= 1
        child.parent = None
        return True

    def safeChildName( self, name ):
        child_names = [ c.name for c in self._children ]
        new_name = name
        count = 1
        while( new_name in child_names ):
            new_name = "{}_{}".format( name, count )
            count += 1
        return new_name
    
    def delChild( self, child ):
        if( child in self._children ):
            self._children.remove( child )
            self._child_count -= 1
            
    def getChild( self, idx ):
        return self._children[ idx ]
    
    def childCount( self ):
        return self._child_count

    def hasChildren( self ):
        return (self._child_count > 0)

    def row( self ):
        # Index relative to parent
        if( self.parent is not None ):
            return self.parent._children.index( self )
        else:
            return 0

    def fullPath( self ):
        if( self.parent is not None ):
            return self.parent.fullPath() + "/" + self.name
        else:
            return "/" + self.name
	    
    def _log( self, tab=-1 ):
        output = ""
        tab += 1
        output += ("  " * tab) + self.name + "\n"
        for child in self._children:
            output += child._log( tab )
        tab -= 1
        return output


class RootNode( Node ):
    
    def __init__( self, name, parent=None ):
        super( RootNode, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_ROOT

    def fullPath( self ):
        return ""

        
class CameraNode( Node ):

    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon )
    
    def __init__( self, name, parent=None ):
        super( CameraNode, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_CAMERA


class ViewNode( Node ):

    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_DriveNetIcon )
    
    def __init__( self, name, parent=None ):
        super( ViewNode, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_VIEW


class SkelNode( Node ):

    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_FileIcon )
    
    def __init__( self, name, parent=None ):
        super( SkelNode, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_SKELETON


class CameraGroup( Node ):
    
    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_DialogOpenButton )
    
    def __init__( self, name, parent=None ):
        super( CameraGroup, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_GROUP_CAMERA


class ViewGroup( Node ):

    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_DirIcon )
    
    def __init__( self, name, parent=None ):
        super( ViewGroup, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_GROUP_VIEW


class SkelGroup( Node ):

    DEFAULT_ICON = getStdIcon( QtWidgets.QStyle.SP_TitleBarContextHelpButton )
    
    def __init__( self, name, parent=None ):
        super( SkelGroup, self ).__init__( name, parent )
        
    def typeInfo( self ):
        return Node.TYPE_GROUP_SKELETON


class SceneModel( QtCore.QAbstractItemModel ):
    
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
    
    def __init__( self, root, parent=None ):
        super( SceneModel, self ).__init__( parent )
        self.root = root or RootNode( "root" )

        # 'Node' Groups
        self.grp_skel = SkelGroup( "Skeletons", self.root )
        self.grp_cams = CameraGroup( "Cameras", self.root )
        self.grp_view = ViewGroup( "Views",     self.root )

    def populatedGroups( self ):
        pop = 0
        for grp in self.root._children:
            if( grp.hasChildren() ):
                pop += 1
        return pop
    
    def rowCount( self, parent ):
        node = self.getNodeIndex( parent )
            
        # way to hide un populated grp nodes??
        #if( node == self.root ):
        #    return self.populatedGroups()

        return node._child_count
    
    def columnCount( self, parent ):
        return 1
    
    def data( self, index, role ):
        if( not index.isValid() ):
            return None
        
        node = index.internalPointer()
        col = index.column()
        
        if( role == QtCore.Qt.DisplayRole ):
            return node.name
        
        elif( role == QtCore.Qt.DecorationRole ):
            if( col == 0 ):
                return node.icon
            
        elif( role == QtCore.Qt.ToolTipRole ):
            return node.fullPath()
		    
    def headerData( self, section, orient, role ):
        if( role == QtCore.Qt.DisplayRole ):
            return ""
    
    def flags( self, index ):
        return self.DEFAULT_FLAGS

    def parent( self, index ):
        node = index.internalPointer()

        if( node.parent == self.root ):
            return QtCore.QModelIndex()

        return self.createIndex( node.parent.row(), 0 , node.parent )
    
    def genIndex( self, node ):
        return self.createIndex( node.row(), 0 , node )
    
    def index( self, row, col, parent ):
        parent_node = self.getNodeIndex( parent )
        
        child = parent_node.getChild( row )

        if( child is not None ):
            return self.createIndex( row, col, child )
        else:
            return QtCore.QModelIndex()
        
    def getNodeIndex( self, index ):
        if( index.isValid() ):
            node = index.internalPointer()
            if( node is not None ):
                return node

        return self.root
    
    def insertRows( self, position, rows, parent=QtCore.QModelIndex() ):
        parent_node = self.getNodeIndex( parent )
        res = True
        self.beginInsertRows( parent, position, position + rows - 1 )
        for row in range( rows ):
            name = parent_node.safeChildName( "NewNode" )
            child = Node( name )
            res &= parent_node.insertChild( position+row, child )
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

        
class QMain( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        self.roots = []
        self._buildUI()
        self.show()

    def _setupModel( self ):
        self.model = SceneModel( None, self )
        # Some Cameras
        for i in range( 10 ):
            _ = CameraNode( "Camera_{:0>2}".format( i+1 ), self.model.grp_cams )
        # Some 3d Views
        _ = ViewNode( "persp", self.model.grp_view )
        _ = ViewNode( "ortho_left", self.model.grp_view )
        _ = ViewNode( "ortho_top", self.model.grp_view )
        _ = ViewNode( "ortho_front", self.model.grp_view )

        # trying to insert rows
        idx = self.model.genIndex( self.model.grp_skel )
        print( idx )
        self.model.insertRows( 0, 5, idx )
        
    def _buildUI( self ):
        self.setWindowTitle( "Testing MVC" )

        self._setupModel()
        print("*"*8)
        grid = QtWidgets.QGridLayout()

        tree_v = QtWidgets.QTreeView()
        tree_v.setHeaderHidden( True )
        list_v1 = QtWidgets.QListView()
        list_v1.setViewMode( QtWidgets.QListView.ListMode )
        list_v2 = QtWidgets.QListView()
        list_v2.setViewMode( QtWidgets.QListView.IconMode )

        grid.addWidget( tree_v,  0, 0, 2 ,1 )
        grid.addWidget( list_v1, 0, 1, 1 ,1 )
        grid.addWidget( list_v2, 1, 1, 1 ,1 )

        tree_v.setModel( self.model )
        list_v1.setModel( self.model )
        list_v2.setModel( self.model )

        sel = tree_v.selectionModel()
        
        list_v1.setSelectionModel( sel )
        list_v1.setRootIndex( self.model.index( 1, 0, QtCore.QModelIndex() ) )
        list_v2.setSelectionModel( sel )
        list_v2.setRootIndex( self.model.index( 1, 0, QtCore.QModelIndex() ) )
        
        self._ctx = QtWidgets.QWidget()
        self._ctx.setLayout( grid )
        self.setCentralWidget( self._ctx )


class SimpleSkel( object ):
    
    """ Robbed from "MotionFiles" in the skunkWorks """
    
    def __init__( self ):
        # Joint Data
        self.joint_names   = [] # [s]   List of Joint names, as encountered
        self.joint_count   = 0  # i     num joints encountered
        self.joint_topo    = {} # s:[s] Dict of parent:[ children... ]
        self.joint_root    = "" # s     name of root joint
        
    def _traverse( self, root ):
        """
            DFS of the skeleton's topology to return a 'computation order' list.
            root can be a leaf if we are coimputing only a subset of the skel
        """
        path = []
        q = [ root ]
        while( len( q ) > 0 ):
            leaf = q.pop( 0 )
            if leaf not in path:
                path.append( leaf )
                q = self.joint_topo[ leaf ] + q
        return path

        
def mkSkel():
    htr_spec = """Hips	GLOBAL
Spine	Hips
Spine1	Spine
Spine2	Spine1
Spine3	Spine2
Neck	Spine3
Head	Neck
HeadEnd	Head
RightShoulder	Spine3
RightArm	RightShoulder
RightForeArm	RightArm
RightForeArmRoll	RightForeArm
RightHand	RightForeArmRoll
RightHandEnd	RightHand
R_FingersEnd	RightHandEnd
RightHandThumb1	RightHand
RightHandThumb2	RightHandThumb1
LeftShoulder	Spine3
LeftArm	LeftShoulder
LeftForeArm	LeftArm
LeftForeArmRoll	LeftForeArm
LeftHand	LeftForeArmRoll
LeftHandEnd	LeftHand
L_FingersEnd	LeftHandEnd
LeftHandThumb1	LeftHand
LeftHandThumb2	LeftHandThumb1
RightUpLeg	Hips
RightLeg	RightUpLeg
RightFoot	RightLeg
RightToeBase	RightFoot
RightToeBaseEnd	RightToeBase
LeftUpLeg	Hips
LeftLeg	LeftUpLeg
LeftFoot	LeftLeg
LeftToeBase	LeftFoot
LeftToeBaseEnd	LeftToeBase"""

    skel = SimpleSkel()

    skel.joint_topo[ "GLOBAL" ] = []
    rev_LUT = {}

    lines = htr_spec.splitlines()
    for line in lines:
        child, parent = line.split()
        
        if parent in skel.joint_topo:
            skel.joint_topo[ parent ].append( child )
        else:
            skel.joint_topo[ parent ] = [ child ]
            
        if child not in skel.joint_topo:
            skel.joint_topo[ child ] = []
            
        rev_LUT[ child ] = parent
                
    root = skel.joint_topo[ "GLOBAL" ][0] # assume one root!
    del( skel.joint_topo[ "GLOBAL" ] )
    skel.joint_root = root
    skel.joint_names = skel._traverse( root )
    skel.joint_count = len( skel.joint_names )

    return skel


if __name__ == "__main__":
    if( True ):
        mainWindow = QMain( app )
        sys.exit( app.exec_() )


    if( False ):
        # skeleton data
        skel = mkSkel()
        print( skel.joint_names )
