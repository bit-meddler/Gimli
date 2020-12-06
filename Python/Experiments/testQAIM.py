import sys

from PySide2 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication() # stupid icon thing

from qaimNodes import SceneModel
#from qaimDict import SceneModel


class QMain( QtWidgets.QMainWindow ):

    def __init__( self, parent ):
        super( QMain, self ).__init__()
        self._app = parent
        self.roots = [ ]
        self._setupModel()
        self._buildUI()
        self.show()

    def _setupModel( self ):
        self.model = SceneModel( None, self )

    def _selectionReport( self, index ):
        indexes = self.sel.selection().indexes()
        print( ", ".join( [ i.data() for i in indexes ] ) )
        node = indexes[-1].internalPointer()
        print( indexes[-1].data( role=QtCore.Qt.DecorationRole ) )
        print( node )

    def onSelectionChanged( self, selected, deselected ):
        # walk selcted and find cameras
        indexes = self.sel.selection().indexes()
        print( ", ".join( [ i.data() for i in indexes ] ) )
        

    def _buildUI( self ):
        self.setWindowTitle( "Testing MVC" )

        print( "*" * 8 )
        grid = QtWidgets.QGridLayout()

        tree_v = QtWidgets.QTreeView()
        tree_v.setHeaderHidden( True )
        tree_v.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        
        list_v1 = QtWidgets.QListView()
        list_v1.setViewMode( QtWidgets.QListView.ListMode )
        list_v1.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        list_v1_sm = list_v1.selectionModel()
        
        list_v2 = QtWidgets.QListView()
        list_v2.setViewMode( QtWidgets.QListView.IconMode )
        list_v2.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        list_v2_sm = list_v2.selectionModel()
        
        grid.addWidget( tree_v, 0, 0, 2, 1 )
        grid.addWidget( list_v1, 0, 1, 1, 1 )
        grid.addWidget( list_v2, 1, 1, 1, 1 )

        tree_v.setModel( self.model )
        list_v1.setModel( self.model )
        list_v2.setModel( self.model )

        self.sel = QtCore.QItemSelectionModel( self.model )

        tree_v.setSelectionModel( self.sel )

        #self.sel.selectionChanged.connect( self._selectionReport )
        self.sel.selectionChanged.connect( self.onSelectionChanged )
        
        list_v1.setSelectionModel( self.sel )
        list_v1.setRootIndex( self.model.ROOT_CAMS )
        list_v2.setSelectionModel( self.sel )
        list_v2.setRootIndex( self.model.ROOT_CAMS )

        del( list_v1_sm, list_v2_sm )

        self._ctx = QtWidgets.QWidget()
        self._ctx.setLayout( grid )
        self.setCentralWidget( self._ctx )

if __name__ == "__main__":
    if (True):
        mainWindow = QMain( app )
        sys.exit( app.exec_() )
