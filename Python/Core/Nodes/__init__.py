""" Nodes representing entities in the scene.  Implementation details in the nodes themselves.
"""

# -------------------- Main Type Registry ------------------------------------ #
TYPE_NODE = "NODE"
TYPE_ROOT = "ROOT"
TYPE_CAMERA = "CAMERA"
TYPE_CAMERA_MC_PI = "PI_CAMERA"
TYPE_SYNC_PI = "PI_SYNC"
TYPE_VIEW = "VIEW"
TYPE_TARGET = "TARGET"

TYPE_GROUP = "GP"
TYPE_GROUP_SYSTEM = "GP_SYSTEM"
TYPE_GROUP_MOCAP = "GP_MOCAP"
TYPE_GROUP_VIEW = "GP_VIEW"
TYPE_GROUP_TARGETS = "GP_TARGETS"


DEFAULT_NAMES = {
    TYPE_NODE : "Node",
    TYPE_ROOT : "Root",
    TYPE_CAMERA : "Camera",
    TYPE_CAMERA_MC_PI : "Camera",
    TYPE_SYNC_PI : "Sync Unit",
    TYPE_VIEW : "View",
    TYPE_TARGET : "Target",

    TYPE_GROUP : "Group",
    TYPE_GROUP_SYSTEM : "System",
    TYPE_GROUP_MOCAP : "Cameras",
    TYPE_GROUP_VIEW : "Views",
    TYPE_GROUP_TARGETS : "Targets",
}
# ------------------------- The main Node base class ----------------------------- #
class Node( object ):
    """ Abstract base class for Nodes. """

    TYPE_INFO = TYPE_NODE

    def __init__( self, name, parent=None ):
        self.name = name
        self._children = []
        self._child_count = 0
        self.parent = parent

        if( parent is not None ):
            parent.addChild( self )
            
        self.data = {}

        self.type_info = self.TYPE_INFO
            
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
        """ Remove child at position, and return it (if possible to remove) """
        if( (position < 0) or (position > len( self._children )) ):
            return (False, None) # Bad target index

        child = self._children.pop( position )
        self._child_count -= 1
        child.parent = None
        return (True, child)

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
        output += "{: <{indent}}{} <{}>\n".format( "", self.displayName(), self.type_info, indent=tab*2 )
        for child in self._children:
            output += child._log( tab )
        tab -= 1
        return output

    def displayName( self ):
        """ Not a 'Getter' - allows group nodes to display a count of children etc """
        return self.name

    def toJSON( self ):
        # serialize the data dict to JSON
        return ""

    def fromJSON( self, json_data ):
        pass


# --------------- Some Boiler plate nodes and groups ----------------------------- #
class RootNode( Node ):
    TYPE_INFO = TYPE_ROOT

    def fullPath( self ):
        return ""

class GroupNode( Node ):
    TYPE_INFO = TYPE_GROUP

    def displayName( self ):
        return "{} [{}]".format( self.name, self._child_count )

class GroupSystem( GroupNode ):
    TYPE_INFO = TYPE_GROUP_SYSTEM

class GroupViews( GroupNode ):
    TYPE_INFO = TYPE_GROUP_VIEW

class GroupMoCapCams( GroupNode ):
    TYPE_INFO = TYPE_GROUP_MOCAP

class GroupTargets( GroupNode ):
    TYPE_INFO = TYPE_GROUP_TARGETS



from . import camera, mcCamera

NODE_LUT = {
    camera.Camera.TYPE_INFO    : camera.Camera,
    mcCamera.MoCapPi.TYPE_INFO : mcCamera.MoCapPi,

    RootNode.TYPE_INFO         : RootNode,
    GroupSystem.TYPE_INFO      : GroupSystem,
    GroupViews.TYPE_INFO       : GroupViews,
    GroupMoCapCams.TYPE_INFO   : GroupMoCapCams,
    GroupTargets.TYPE_INFO     : GroupTargets,
}

def factory( node_type, name=None, parent=None ):
    name = name or DEFAULT_NAMES[ node_type ]
    return NODE_LUT[ node_type ]( name, parent )

    
__all__ = [

    "TYPE_NODE",
    "TYPE_ROOT",

    "TYPE_CAMERA",
    "TYPE_CAMERA_MC_PI",
    "TYPE_SYNC_PI",
    "TYPE_VIEW",
    "TYPE_TARGET",

    "TYPE_GROUP_SYSTEM",
    "TYPE_GROUP_CAMERA",
    "TYPE_GROUP_VIEW",
    "TYPE_GROUP_TARGETS",

    "DEFAULT_NAMES",
    
    "Node",
    
    "factory"
]
