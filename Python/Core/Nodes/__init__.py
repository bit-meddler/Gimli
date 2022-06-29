# 
# Copyright (C) 2016~2022 The Gimli Project
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

""" Nodes representing entities in the scene.  Implementation details in the nodes themselves.
"""

# -------------------- Main Type Registry ---------------------------------------------------------------------------- #
# If you're making a new node, make sure it doesn't collide with any of these
TYPE_NODE = "NODE"
TYPE_ROOT = "ROOT"
TYPE_CAMERA = "CAMERA"
TYPE_CAMERA_MC_PI = "PI_CAMERA"
TYPE_SYNC_PI = "PI_SYNC"
TYPE_VIEW = "VIEW"
TYPE_TESTING = "TESTING"
#TYPE_TARGET = "TARGET"

TYPE_GROUP = "GP"
TYPE_GROUP_SYSTEM = "GP_SYSTEM"
TYPE_GROUP_MOCAP = "GP_MOCAP"
TYPE_GROUP_VIEW = "GP_VIEW"
TYPE_GROUP_TARGETS = "GP_TARGETS"


# ------------------------- The main Node base class ----------------------------------------------------------------- #
class Node( object ):
    """ Abstract base class for Nodes. """

    TYPE_INFO = TYPE_NODE
    DEFAULT_NAME = "Node"

    def __init__( self, name, parent=None ):
        """
        Instantiate a Node.
        Args:
            name: (str) The Nodes name
            parent: (Nodelike) The Node's parent.
        """
        self.name = name
        self._children = []
        self._child_count = 0
        self.parent = parent

        if( parent is not None ):
            parent.addChild( self )
            
        self.data = {}

        self.type_info = self.TYPE_INFO
            
    def addChild( self, child ):
        """
        Add a child node under this node.
        Args:
            child: (Nodelike) The child.
        """
        self._children.append( child )
        self._child_count += 1

    def insertChild( self, position, child ):
        """
        Insert the given Node to a specific index in the child list.
        Args:
            position: (int) Target position for the Node.
            child: (noedlike) the Node.

        Returns:
            success: (bool) If it was possible to insert the node.
        """
        if( (position < 0) or (position > self._child_count) ):
            return False # Bad target index

        self._children.insert( position, child )
        child.parent = self
        self._child_count += 1
        return True
    
    def removeChild( self, position ):
        """
        Remove child at position, and return it (if possible to remove)
        Args:
            position: (int) index of Node to remove

        Returns:
            result: (tuple)
                success: (bool) Has it been possible to remove the node.
                node: (nodelike) The removed node, if successful.
        """
        if( (position < 0) or (position > len( self._children )) ):
            return (False, None) # Bad target index

        child = self._children.pop( position )
        self._child_count -= 1
        child.parent = None
        return (True, child)

    def safeChildName( self, name ):
        """
        Test and generate a name that doesn't collide with existing children.
        Args:
            name: (str) Candidate node name.

        Returns:
            new_name: (bool) The safe name for a child node.
        """
        child_names = [ c.name for c in self._children ]
        new_name = name
        count = 1
        while( new_name in child_names ):
            new_name = "{}_{}".format( name, count )
            count += 1
        return new_name
    
    def delChild( self, child ):
        """
        Remove the supplied node from the list of children.
        Args:
            child: (nodelike) The node to remove
        """
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
        """
        For Qt Tree widgets, the "row" is the depth of this node in it's parent's child list.
        Returns:
            index: (int) This Node's index.
        """
        if( self.parent is not None ):
            return self.parent._children.index( self )
        else:
            return 0

    def fullPath( self ):
        """
        Generate a textual 'path' to this node.
        Returns:
            path: (str) the path.
        """
        if( self.parent is not None ):
            return self.parent.fullPath() + "/" + self.name
        else:
            return "/" + self.name
        
    def _log( self, tab=-1 ):
        """ DEBUG
        Recurse Children and build a 'tree' with indents showing depth of children.
        Args:
            tab: (int) indent depth.

        Returns:
            output: (str) The complete tree
        """
        output = ""
        tab += 1
        output += "{: <{indent}}{} <{}>\n".format( "", self.displayName(), self.type_info, indent=tab*2 )
        for child in self._children:
            output += child._log( tab )
        tab -= 1
        return output

    def displayName( self ):
        """
        Not a 'Getter' - allows subclassing nodes to display extra information, such as a count of children.
        Returns:
            displayname: (str) What to display for this node's name.
        """
        return self.name

    def toJSON( self ):
        """
        Implementing Nodes will have a private method to handle their JSON representation.
        Returns:
            json: (str) JSON of the node's data.
        """
        return ""

    def fromJSON( self, json_data ):
        """
        Implementing Nodes will have a private method to handle their JSON representation.
        Args:
            json_data: (str) JSON of a node's data
        """
        pass


# --------------- Some Boiler plate nodes and groups ----------------------------------------------------------------- #
class RootNode( Node ):
    """
    The Root node, there should only ever be one of these, and it is parent of the whole tree structure
    """
    TYPE_INFO = TYPE_ROOT
    DEFAULT_NAME = "Root"

    def fullPath( self ):
        return ""

class GroupNode( Node ):
    """
    A Group Node is a display controlling node, not actually evaluated or doing anything.
    """
    TYPE_INFO = TYPE_GROUP
    DEFAULT_NAME = "Group"

    def displayName( self ):
        """
        Overloading generic displayName, this implementation shows how many children a group has.
        Returns:
            displayname: (Str) custom display name.
        """
        return "{} [{}]".format( self.name, self._child_count )

class GroupSystem( GroupNode ):
    TYPE_INFO = TYPE_GROUP_SYSTEM
    DEFAULT_NAME = "System"

class GroupViews( GroupNode ):
    TYPE_INFO = TYPE_GROUP_VIEW
    DEFAULT_NAME = "Views"

class GroupMoCapCams( GroupNode ):
    TYPE_INFO = TYPE_GROUP_MOCAP
    DEFAULT_NAME = "Cameras"

class GroupTargets( GroupNode ):
    TYPE_INFO = TYPE_GROUP_TARGETS
    DEFAULT_NAME = "Targets"

class Testing( Node ):
    TYPE_INFO = TYPE_TESTING
    DEFAULT_NAME = "Trait Testing"

########################################################################################################################
# The Stuff to change when we add new nodes is here
########################################################################################################################
# As we add "Functional" Nodes, we'll need to import them and load the LUT up with the implementations.
from . import camera, mcCamera, view


NODE_LUT = {
    camera.Camera.TYPE_INFO    : camera.Camera,
    mcCamera.MoCapPi.TYPE_INFO : mcCamera.MoCapPi,

    view.View.TYPE_INFO        : view.View,

    RootNode.TYPE_INFO         : RootNode,
    GroupSystem.TYPE_INFO      : GroupSystem,
    GroupViews.TYPE_INFO       : GroupViews,
    GroupMoCapCams.TYPE_INFO   : GroupMoCapCams,
    GroupTargets.TYPE_INFO     : GroupTargets,

    Testing.TYPE_INFO          : Testing,
}

NODE_DEPENDANCIES = {
    TYPE_CAMERA_MC_PI: TYPE_GROUP_MOCAP,
    TYPE_GROUP_MOCAP : TYPE_GROUP_SYSTEM,

    TYPE_SYNC_PI     : TYPE_GROUP_SYSTEM,

    TYPE_VIEW        : TYPE_GROUP_VIEW,
}

def factory( node_type, name=None, parent=None ):
    """
    Given a node_type (that is registered here, and implemented) generate a default node.
    Args:
        node_type: (str) new Node Type.
        name: (str) The new Node's name.
        parent: (nodelike) The new Node's parent.

    Returns:
        node: (nodelike) The new Node.
    """
    name = name or NODE_LUT[ node_type ].DEFAULT_NAME
    return NODE_LUT[ node_type ]( name, parent )


# Also Register the type of new nodes here so other components can use them
__all__ = [

    "TYPE_NODE",
    "TYPE_ROOT",

    "TYPE_CAMERA",
    "TYPE_CAMERA_MC_PI",
    "TYPE_SYNC_PI",
    "TYPE_VIEW",
#    "TYPE_TARGET",

    "TYPE_GROUP_SYSTEM",
    "TYPE_GROUP_CAMERA",
    "TYPE_GROUP_VIEW",
    "TYPE_GROUP_TARGETS",

    "TYPE_TESTING",

    "DEFAULT_NAMES",
    
    "Node",
    
    "factory"
]

