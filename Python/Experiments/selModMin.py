import sys
from PySide2 import QtCore, QtGui, QtWidgets

class MySelectionModel( QtCore.QItemSelectionModel ):
    # Todo: Selection with priority
    def __init__( self, data_model ):
        super( MySelectionModel, self ).__init__( data_model )
        self.primary = None
        self.selectionChanged.connect( self.onSelectionChanged )# Nasty

    def onSelectionChanged( self, selected, deselected ):
        sels = selected.indexes()
        if( len( sels ) > 0 ):
            self.primary = sels[-1]
            return

        des = deselected.indexes()
        current = self.selection().indexes()
        if( len( des ) > 0 ):
            if( self.primary in des ):
                if( len( current ) > 0 ):
                    self.primary = current[-1]
                else:
                    self.primary = None
                
    def cyclePrimary( self, direction=1 ):
        current = self.selection().indexes()
        num_current = len( current )
        if( num_current <= 1 ):
            return
        
        idx = current.index( self.primary ) + direction
        if( idx < 0 ):
            idx = num_current - 1
        elif( idx == num_current ):
            idx = 0

        self.primary = current[ idx ]
        
        
class Main( QtWidgets.QMainWindow ): # This is all Boiler plate
    def __init__( self ):
        super( Main, self ).__init__()
        self.setWindowTitle( "Testing Selections" )
        style = QtWidgets.QApplication.style()
        grid = QtWidgets.QGridLayout()
        tree = QtWidgets.QTreeWidget()
        tree.setHeaderHidden( True )
        tree.setColumnCount( 1 )
        tree.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        tree_sm = tree.selectionModel()
        spam = QtWidgets.QTreeWidgetItem( tree )
        spam.setText( 0, "Spam" )
        spam.setIcon( 0, QtGui.QIcon( style.standardIcon( style.SP_ComputerIcon ) ) )
        eggs = QtWidgets.QTreeWidgetItem( tree )
        eggs.setText( 0, "Eggs" )
        eggs.setIcon( 0, QtGui.QIcon( style.standardIcon( style.SP_DialogHelpButton ) ) )
        for i in range( 6 ):
            egg = QtWidgets.QTreeWidgetItem( eggs )
            egg.setText( 0, "Egg {}".format( i+1) )
            egg.setIcon( 0, QtGui.QIcon( style.standardIcon( style.SP_DriveCDIcon ) ) )
        tree.insertTopLevelItems( 2, [spam, eggs] )
        eggs_index = tree.indexFromItem( eggs )
        list_v1 = QtWidgets.QListView()
        list_v1.setViewMode( QtWidgets.QListView.ListMode )
        list_v1.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        list_v1_sm = list_v1.selectionModel()
        list_v2 = QtWidgets.QListView()
        list_v2.setViewMode( QtWidgets.QListView.IconMode )
        list_v2.setResizeMode( QtWidgets.QListView.Adjust )
        list_v2.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        list_v2_sm = list_v2.selectionModel()
        grid.addWidget( tree, 0, 0, 2, 1 )
        grid.addWidget( list_v1, 0, 1, 1, 1 )
        grid.addWidget( list_v2, 1, 1, 1, 1 )
        self.model = tree.model()
        list_v1.setModel( self.model )
        list_v2.setModel( self.model )
        self.sel = MySelectionModel( self.model ) # <--------- Use custom Selection Model
        tree.setSelectionModel( self.sel )
        list_v1.setSelectionModel( self.sel )
        list_v1.setRootIndex( eggs_index )
        list_v2.setSelectionModel( self.sel )
        list_v2.setRootIndex( eggs_index )
        del( list_v1_sm, list_v2_sm, tree_sm )
        ctx = QtWidgets.QWidget()
        ctx.setLayout( grid )
        self.setCentralWidget( ctx )
        self.sel.selectionChanged.connect( self.onSelectionChanged )
        self.show()

    def onSelectionChanged( self, selected, deselected ):
        print( "Added: " + "".join( [ i.data() for i in selected.indexes() ] ) )
        list = ""
        for idx in self.sel.selection().indexes():
            pri = bool( idx == self.sel.primary )
            list += "{}{}{}, ".format( ">" if pri else "", idx.data(), "<" if pri else "" )
        print( "Queue: " + list )


if( __name__ == "__main__" ):
    app = QtWidgets.QApplication()
    mainWindow = Main()
    sys.exit( app.exec_() )
