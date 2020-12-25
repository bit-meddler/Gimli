"""
    qtMvc.py - an experiment to try out data models, items and views in Qt
    Hopefuly this will let us navigate around the scenegraph and share "selection"
    interactions between widgets observing the same data.
"""
import logging
import os
import sys

from PySide2 import QtCore, QtGui, QtWidgets


class TestModel( QtGui.QStandardItemModel ):

    def __init__( self ):
        super( TestModel, self ).__init__()

    def data( self, index, role ):
        """ Just playing with DecorationRole / drawing for now"""
        item = self.itemFromIndex( index )

        if( role == QtCore.Qt.DisplayRole ):
            return item.text()

        if( role == QtCore.Qt.DecorationRole ):
           if( item.text().startswith("Child") ):
               return QtGui.QColor( 255, 0, 0 )
           else:
               return QtGui.QColor( 0, 255, 0 )


class QMain( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        self.roots = []
        self._buildUI()
        self.show()

    def _setupModel( self ):
        # most basic ever
        self.model = TestModel()

        r1 = QtGui.QStandardItem( "1st Root" )
        r2 = QtGui.QStandardItem( "2nd Root" )
        c1 = QtGui.QStandardItem( "Child 1" )
        c2 = QtGui.QStandardItem( "Child 2" )

        self.roots.append( r1 )
        self.roots.append( r2 )

        self.model.appendRow( r1 )
        self.model.appendRow( r2 )
        r1.appendRow( c1 )
        r1.appendRow( c2 )

    def _buildUI( self ):
        self.setWindowTitle( "Testing MVC" )

        self._setupModel()

        grid = QtWidgets.QGridLayout()

        tree_v = QtWidgets.QTreeView()
        tree_v.setHeaderHidden( True )
        list_v = QtWidgets.QListView()

        grid.addWidget( tree_v, 0, 0, 1 ,1 )
        grid.addWidget( list_v, 0, 1, 1 ,1 )

        tree_v.setModel( self.model )
        list_v.setModel( self.model )

        sel = tree_v.selectionModel()
        list_v.setSelectionModel( sel )

        list_v.setRootIndex( self.model.indexFromItem( self.roots[0] ) )

        self._ctx = QtWidgets.QWidget()
        self._ctx.setLayout( grid )
        self.setCentralWidget( self._ctx )

if __name__ == "__main__":
    app = QtWidgets.QApplication()
    mainWindow = QMain( app )
    sys.exit( app.exec_() )