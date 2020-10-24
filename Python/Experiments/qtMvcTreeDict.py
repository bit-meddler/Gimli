"""
    qtMvcTree.py - New experiment based on Yasin Uludag's tutorials: https://www.youtube.com/watch?v=VcN94yMOkyU&t=2s
"""
from collections import OrderedDict
from itertools import islice
import logging
import os
from pprint import pprint
import sys

from PySide2 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication() # Trick to get "Standard Icons"

def getStdIcon( icon_enum ):
    return QtGui.QIcon( QtWidgets.QApplication.style().standardIcon( icon_enum ) )


class Scene( object ):

    # The scene root
    TYPE_ROOT = "ROOT"

    # Primatives
    TYPE_NODE = "NODE"
    TYPE_CAMERA = "CAMERA"
    TYPE_VIEW = "VIEW"
    TYPE_SKELETON = "SKELETON"
    TYPE_JOINT_ROOT = "ROOTJOINT"
    TYPE_JOINT = "JOINT"

    # Type Groups
    TYPE_GROUP_SYS = "GP_SYS"
    TYPE_GROUP_SYS_SYNC = "GP_SYS_SYNC"
    TYPE_GROUP_SYS_CAMS = "GP_SYS_CAMS"
    TYPE_GROUP_VIEW = "GP_VIEW"
    TYPE_GROUP_SKELETONS = "GP_SKELETON"


    def __init__( self ):
        self.root = "/"
        self.data = {
            self.root : {
                "data"     : None,
                "name"     : "root",
                "parent"   : None,
                "row"      : -1,
                "children" : 0,
                "type"     : Scene.TYPE_ROOT,
            }
        } # "/path/to/data" : dataDict
        self.tree = OrderedDict( {self.root:OrderedDict()} ) # { "":{"a":"/a","b":"/b"}, "/b":{"c":"/b/c"} }

        # Default Groups
        self.addNode( self.root, "views", type=Scene.TYPE_GROUP_VIEW )
        self.addNode( self.root, "system", type=Scene.TYPE_GROUP_SYS )
        self.addNode( "/system", "sync", type=Scene.TYPE_GROUP_SYS_SYNC )
        self.addNode( "/system", "cams", type=Scene.TYPE_GROUP_SYS_CAMS )
        self.addNode( self.root, "skels", type=Scene.TYPE_GROUP_SKELETONS )

        self.addNode( self.root, "dummy" )

    @staticmethod
    def getODbyIdx( data:OrderedDict, idx ):
        return list( data.values() )[ idx ]
        #return next( islice( data.values(), idx, idx+1 ) )

    def safeName( self, name:str, parent ) -> str:
        """ look in an 'in'able collection and make name unique """
        new_name = name
        count = 1
        while( new_name in parent ):
            new_name = "{}_{}".format( name, count )
            count += 1
        return new_name
    
    def hasPath( self, path ):
        """ Does fully qualified path 'path' exist? """
        return bool( path in self.data )

    def addNodeData( self, path, name, row, type=TYPE_NODE ):
        parent_path, _ = path.rsplit("/",1)
        if( parent_path==""):
            parent_path="/"
        self.data[ path ] = { "name":name, "parent":parent_path, "children":0, "row":row, "data":None, "type":type }

    def getPathData( self, tgt_path:str, node_mode:bool ) -> tuple:
        route = tgt_path.strip("/").split("/")
        path = "/" # allways start at root
        parent_path = "/"
        parent = self.tree
        leaf = ""
        row = -1
        for step in route:
            leaf = step
            if( path not in self.tree ):
                # Unreachable address, bail
                return (path, parent_path, parent, leaf, -1, False)
            parent = self.tree[ path ]
            parent_path = path

            if( parent is None and node_mode ): # Don't do this when adding data???
                self.tree[ path ] = OrderedDict()
                parent = self.tree[ path ]

            path = self.join(path, leaf)
            #path = parent.get( leaf, self.join(path, leaf))

        if( parent is not None and leaf in parent ):
            row = list( parent.keys() ).index( leaf )
        return (parent_path, parent, leaf, row, True)


    def join( self, *args ):
        """ TODO: must be a better way of doing join """
        if( args[0]=="/" ):
            return  "/".join( ["", *args[1:]] )
        else:
            return "/".join( args )

    def delNode( self, path ):
        parent_path, parent, name, _, reachable = self.getPathData( path, True )
        if( reachable ):
            del( parent[ name ] )
            del( self.data[ path ])
            # remarshal parent's children
            self.data[ parent_path ][ "children" ] += 1
            for i, child in enumerate( parent ):
                child_path = self.join( parent_path, child )
                data = self.data[ child_path ]
                if( data is not None ):
                    data["row"] = i
            # add to Undo Queue
            # undos.add.add( new_path )

    def addNode( self, path, name, type=TYPE_NODE ):
        new_path = self.join( path, name )
        parent_path, parent, leaf, _, reachable = self.getPathData( new_path, True )
        if( reachable ):
            # make sure name dosen't collide
            name = self.safeName( leaf, parent )
            new_path = self.join(parent_path, name)
            parent[ name ] = new_path
            self.data[ parent_path ][ "children" ] += 1
            self.tree[ new_path ] = None
            row = list( parent.keys() ).index( name )
            self.addNodeData( new_path, name, row, type=type )
            # add to Undo Queue
            # undos.del.add( new_path )
            return new_path

    def addData( self, path, name, data:dict ) -> str:
        new_path = self.join( path, name )
        parent_path, parent, leaf, _, reachable = self.getPathData( new_path, False )
        if( reachable ):
            print(parent_path, parent, reachable)
            if( self.data[ parent_path ]["data"] is None ):
                self.data[ parent_path ][ "data" ] = []
            data_keys = self.data[ parent_path ][ "data" ]
            new_name = self.safeName( name, data_keys )
            data_keys.append( new_name )
            new_path = self.join( parent_path, new_name )
            self.data[ new_path ] = data
            # add to Undo Queue
            # undos.del.add( new_path )
            return new_path

    def setValue( self, path, key, value ):
        if( path in self.data ):
            # add to Undo Queue
            # undos.set.add( (path,key,value) )
            self.data[ path ][ key ] = value
        else:
            # should we just create a node?
            pass


class SceneModel( QtCore.QAbstractItemModel ):
    
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    ICON_LUT = {
        # The scene root
        Scene.TYPE_ROOT             : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),

        # Primatives
        Scene.TYPE_NODE             : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),
        Scene.TYPE_CAMERA           : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),
        Scene.TYPE_VIEW             : getStdIcon( QtWidgets.QStyle.SP_TitleBarContextHelpButton ),
        Scene.TYPE_SKELETON         : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),
        Scene.TYPE_JOINT_ROOT       : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),
        Scene.TYPE_JOINT            : getStdIcon( QtWidgets.QStyle.SP_DriveFDIcon ),

        # Type Groups
        Scene.TYPE_GROUP_SYS        : getStdIcon( QtWidgets.QStyle.SP_DialogOpenButton ),
        Scene.TYPE_GROUP_SYS_SYNC   : getStdIcon( QtWidgets.QStyle.SP_DialogOpenButton ),
        Scene.TYPE_GROUP_SYS_CAMS   : getStdIcon( QtWidgets.QStyle.SP_DriveNetIcon ),
        Scene.TYPE_GROUP_VIEW       : getStdIcon( QtWidgets.QStyle.SP_DirIcon ),
        Scene.TYPE_GROUP_SKELETONS  : getStdIcon( QtWidgets.QStyle.SP_FileIcon ),
    }

    def __init__( self, root, parent=None ):
        super( SceneModel, self ).__init__( parent )
        self._scene = Scene()
        for i in range(10):
            self._scene.addNode( "/system/cams", "cam_{}".format(i) )

    def getNodeFromIndex( self, index ):
        node = index.internalPointer()
        if( node is not None ):
            #print( "idx", node )
            return node
        else:
            print("Invalid")
            print( index )
        return self._scene.root

    def rowCount( self, parent ):
        path = self.getNodeFromIndex( parent )
        if( self._scene.tree[ path ] is None ):
            return 0
        return self._scene.data[ path ][ "children" ]
    
    def columnCount( self, parent ):
        return 1
    
    def data( self, index, role ):
        if( not index.isValid() ):
            print( "invalid data" )
            return None
        
        path = index.internalPointer()
        col = index.column()

        if( role == QtCore.Qt.DisplayRole ):
            return self._scene.data[ path ][ "name" ]
        
        elif( role == QtCore.Qt.DecorationRole ):
            if( col == 0 ):
                return SceneModel.ICON_LUT[ self._scene.data[ path ][ "type" ] ]
            
        elif( role == QtCore.Qt.ToolTipRole ):
            return path
		    
    def headerData( self, section, orient, role ):
        if( role == QtCore.Qt.DisplayRole ):
            return ""
    
    def flags( self, index ):
        return self.DEFAULT_FLAGS

    def parent( self, index ):
        path = index.internalPointer()
        node = self._scene.data[ path ]
        parent = self._scene.data[ node["parent"] ]

        print( "p", path, node, parent )
        if( node["parent"] == self._scene.root ):
            return QtCore.QModelIndex()
        return self.createIndex( parent["row"], 0 , node["parent"] )
    
    def genIndex( self, path ):
        node = self._scene.data[ path ]
        return self.createIndex( node["row"], 0 , path )
    
    def index( self, row, col, parent ):
        parent_path = self.getNodeFromIndex( parent )
        if( self._scene.tree[ parent_path ] is not None ):
            if( row >= self._scene.data[ parent_path ][ "children" ] ):
                print( "Wrong parent inspected" )
                print( row, col, parent_path )

            try:
                path = self._scene.getODbyIdx( self._scene.tree[ parent_path ], row )
                print( "Idx", path, row )
            except (StopIteration, IndexError):
                print( "Error with:", row, col, parent_path )
                pprint( self._scene.tree )
                pprint( self._scene.data )
                exit(0)

            return self.createIndex( row, col, path )
        else:
            return QtCore.QModelIndex()
    
    def insertRows( self, position, rows, parent=QtCore.QModelIndex() ):
        pass
    
    def removeRows( self, position, rows, parent=QtCore.QModelIndex() ):
        pass

        
class QMain( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        self.roots = []
        self._buildUI()
        self.show()

    def _setupModel( self ):
        self.model = SceneModel( None, self )
        
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

    if( True ):
        scene = Scene()

        scene.addNode( "/skels", "Andy", None )

        scene.addNode( "/system/cams", "cam", None )
        scene.addNode( "/system/cams", "cam", None )
        #print( scene.getPathData( "/system/cams/cam_2", False ))
        scene.addNode( "/system/cams", "cam/", None )

        #print( scene.getPathData( "/system/cams/cam_2", False ))

        scene.addData( "/system/cams/cam_2", "attrs", {"strobe":25,"fps":60} )

        from pprint import pprint
        #pprint( scene.tree )
        pprint( scene.data )