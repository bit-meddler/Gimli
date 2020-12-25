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

    # Undo system
    UNDO_ACTIONS = {
        "ADD_N" : "DEL_N",
        "DEL_N" : "ADD_N",
        "ADD_D" : "DEL_D",
        "DEL_D" : "ADD_D",

        "SET_N" : "SET_O",
        "SET_O" : "SET_N",
    }
    UNDO_KVS = ( "SET_N", "SET_O", )


    def __init__( self ):
        # Scene root
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

        # Undo system
        self._undo_stack = []
        self._redo_stack = []
        self._undo = None
        self._undo_ignore = True
        self.undo_max = 42

        # Default Groups
        self.addNode( self.root, "views", type=Scene.TYPE_GROUP_VIEW )
        self.addNode( self.root, "system", type=Scene.TYPE_GROUP_SYS )
        self.addNode( "/system", "sync", type=Scene.TYPE_GROUP_SYS_SYNC )
        self.addNode( "/system", "cams", type=Scene.TYPE_GROUP_SYS_CAMS )
        self.addNode( self.root, "skels", type=Scene.TYPE_GROUP_SKELETONS )

        self._undo_ignore = False
        self.beginUndo()

    @staticmethod
    def getODbyIdx( data:OrderedDict, idx ):
        #return list( data.values() )[ idx ]
        return next( islice( data.values(), idx, idx+1 ) )

    @staticmethod
    def join( *args ) -> str:
        """ TODO: must be a better way of doing join """
        if( args[0]=="/" ):
            return  "/".join( ["", *args[1:]] )
        else:
            return "/".join( args )

    @staticmethod
    def split( path:str ) -> list:
        return path.strip("/").split("/")

    def beginUndo( self, name:str="unknown" ):
        if( self._undo is not None ):
            self._undo_stack.append( self._undo )

        self._undo_ignore = False # assume we're interested in undos if we've started an interaction
        self._undo = {"action":name} # other keys "add", "del", "set"

    def addUndo( self, action:str, path:str, action_data:dict=None ) -> bool:
        if( self._undo_ignore ):
            return False

        if( action not in Scene.UNDO_KVS ):
            # Create or delete nodes / data
            action_undos = self._undo.setdefault( action, set() )
            action_undos.add( path )
        else:
            # KV pairs for setting values
            action_undos = self._undo.setdefault( action, dict() )
            for key, value in action_data.items():
                action_undos[ path ][ key ] = value

        if( len(self._undo_stack) > self.undo_max ):
            self._undo_stack.pop( 0 ) # drop oldest undo
        return True

    def doUndo( self ):
        self._undo_ignore = True
        # invert the operations of the current undo
        # ???

        # place the undo on the end of the redo stack
        self._redo_stack.append( self._undo )

        # pop the previous undo from the undo stack and make current
        if( self._undo_stack ): # has items
            self._undo = self._undo_stack.pop()

        if (len( self._redo_stack ) > self.undo_max):
            self._redo_stack.pop( 0 )  # drop oldest redo
        self._undo_ignore = False

    def safeName( self, name:str, parent:(list, dict) ) -> str:
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

    def getPathInfo( self, tgt_path:str, node_mode:bool ) -> tuple:
        route = self.split( tgt_path )
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

    def addNode( self, path:str, name:str, type:str=TYPE_NODE ):
        """
        Add a Node to the Tree Structure
        :param path: parent's path in structure
        :param name: node name - this may be changed if there is a collision
        :param type: Scene.TYPE_ of Node, for ui
        :return: fully qualified path of Node created
        """
        new_path = self.join( path, name )
        parent_path, parent, leaf, _, reachable = self.getPathInfo( new_path, True )
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
            undoable = self.addUndo( "ADD_N", new_path )
            return new_path

    def delNode( self, path:str ):
        parent_path, parent, name, _, reachable = self.getPathInfo( path, True )
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
            undoable = self.addUndo( "DEL_N", path )

    def addNodeData( self, path:str, name:str, row:int, type:str=TYPE_NODE ):
        parent_path, _ = path.rsplit("/",1)
        if( parent_path==""):
            parent_path="/"
        self.data[ path ] = { "name":name, "parent":parent_path, "children":0, "row":row, "data":None, "type":type }

    def addData( self, path:str, name:str, data:dict ) -> str:
        new_path = self.join( path, name )
        parent_path, parent, leaf, _, reachable = self.getPathInfo( new_path, False )
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
            undoable = self.addUndo( "ADD_D", new_path )
            return new_path

    def delData( self, path:str ):
        # ... ???
        undoable = self.addUndo( "DEL_D", path )

    def setValue( self, path:str, key:str, value ):
        if( path in self.data ):
            # add to Undo Queue
            old_value = self.data[ path ][ key ]
            undoable = self.addUndo( "SET_O", path, {key:old_value} )
            self.data[ path ][ key ] = value
            undoable = self.addUndo( "SET_N", path, {key:value} )
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
            #print( "idx", node, index )
            return node

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

        if( self._scene.data[ path ]["parent"] == self._scene.root ):
            return QtCore.QModelIndex()

        parent_path = self._scene.data[ path ]["parent"]
        return self.createIndex( self._scene.data[ parent_path ]["row"], 0, parent_path )
    
    def genIndex( self, path ):
        parent = self._scene.tree[ "/" ]
        parent_idx = QtCore.QModelIndex()
        for step in path.strip("/").split("/"):
            if( step == "" ):
                break
            address = parent[step]
            parent = self._scene.tree[ address ]
            data = self._scene.data[ address ]
            parent_idx = self.index( data["row"], 0, parent_idx )
        print( parent_idx, parent_idx.internalPointer() )
        return parent_idx
    
    def index( self, row:int, col:int, parent ):
        if( not self.hasIndex( row, col, parent ) ):
            return QtCore.QModelIndex()

        parent_path = self.getNodeFromIndex( parent )
        if( self._scene.tree[ parent_path ] is not None ):
            path = self._scene.getODbyIdx( self._scene.tree[ parent_path ], row )
            idx = self.createIndex( row, col, path )
            #print( idx, idx.internalPointer() )
            return idx
        else:
            return QtCore.QModelIndex()

    # ToDo: this is going to be hard...
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
        list_v1.setRootIndex( self.model.genIndex( "/system/cams" ) )
        list_v2.setSelectionModel( sel )
        list_v2.setRootIndex( self.model.genIndex( "/" ) )
        
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