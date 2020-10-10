"""
docking Outliner

"""

import logging
from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL

from GUI import getStdIcon, Camera, Mesh

class QDockingOutliner( QtWidgets.QDockWidget ):

    class SceneTree(  QtWidgets.QTreeWidget ):

        def __init__(self, parent ):
            super( QDockingOutliner.SceneTree, self ).__init__( parent )
            self.setSelectionBehavior( QtWidgets.QAbstractItemView.SelectRows )
            self.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection  )
            self.setHeaderHidden( True )

        def selectionChanged( self, *args, **kwargs ):
            # Ignore old Vs New, just directly get the selected list
            selects = self.selectionModel().selectedRows()

            app = self.parent().parent()

            app.selection_que.clear()
            if( len( selects ) > 0 ):
                for idx in selects:
                    itm = self.itemFromIndex( idx )
                    if( hasattr( itm, "_data" ) ):
                        app.selection_que.append( itm._data )
            app.updateSelection()
            return super( QDockingOutliner.SceneTree, self ).selectionChanged( *args, **kwargs )

    def __init__( self, parent ):
        super( QDockingOutliner, self ).__init__( "Outliner", parent )
        self.setObjectName( "OutlineDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        self._buildUI()

    def _populate( self ):
        example_scene = { # All a bit bogus, this needs tobe worked out from the sysman
            "Cameras" : { "Cam_01": Camera("Cam_01", 0), "Cam_02": Camera("Cam_02", 1) },
            "Scene" : { "Cube" : Mesh() }
        }
        for k, v in example_scene.items():
            first_node = QtWidgets.QTreeWidgetItem( self.tree, [k] )
            for k1, v1 in v.items():
                node = QtWidgets.QTreeWidgetItem( first_node, [k1] )
                node._data = v1

        self._expandChildren( self.tree.invisibleRootItem() )

    def _expandChildren( self, item ):
        for i in range( item.childCount() ):
            self._expandChildren( item.child( i ) )
        self.tree.expandItem( item )

    def _buildUI( self ):
        self.tree = self.SceneTree( self )
        self._populate()
        self.setWidget( self.tree )