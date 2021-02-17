"""
The Docking attribute editor.

At UI creation time, it is expected that any nodes we will have in the scene will be registered.  When registered their
Attribuite edit pane will be created.  Selection and Scene Model are shared with the application and currently the
"Lead" Node in the selection (usually last) is the node whose editor will be displayed.

ToDo: so much...

"""

import logging

from functools import partial

from PySide2 import QtCore, QtGui, QtWidgets, QtOpenGL
from GUI.widgets import QKnob
from GUI import getStdIcon, ROLE_TYPEINFO
from GUI.UINodes import uiNodeFactory

class QDockingAttrs( QtWidgets.QDockWidget ):

    def __init__(self, parent):
        super( QDockingAttrs, self ).__init__( "Attribute Editor", parent )
        self.setObjectName( "AtribDockWidget" )
        self.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea )

        # Stack Widget
        self.stack = QtWidgets.QStackedWidget()

        # currently selected type
        self._current = None

        # selection Model and data Model
        self._select = None
        self._model  = None

        # cache of forms
        self._forms = {}
        self._forms_adv = {}

        # None selected form
        temp = QtWidgets.QLabel( "Nothing Selected" )
        temp.setAlignment( QtCore.Qt.AlignCenter )
        self._forms[ type( None ) ] = temp
        self.stack.addWidget( temp )

        # build
        self._buildUI()

        self.setMinimumHeight( 250 )

    def _buildToolbar( self ):
        atrib_tools = self._mini_main.addToolBar( "AtribTools" )
        atrib_tools.setIconSize( QtCore.QSize( 16, 16 ) )
        atrib_tools.setMovable( False )

        # toggle Group for application mode
        group = QtWidgets.QButtonGroup( self )

        self.change_sel = QtWidgets.QToolButton( self )
        self.change_sel.setIcon( getStdIcon( QtWidgets.QStyle.SP_FileDialogListView ) )
        self.change_sel.setStatusTip( "Changes Selection" )
        self.change_sel.setToolTip( "Changes Affect Selection" )
        self.change_sel.setCheckable( True )
        group.addButton( self.change_sel )

        self.change_all = QtWidgets.QToolButton( self )
        self.change_all.setIcon( getStdIcon( QtWidgets.QStyle.SP_FileDialogDetailedView ) )
        self.change_all.setStatusTip( "Change All" )
        self.change_all.setToolTip( "Changes Affect All" )
        self.change_all.setCheckable( True )
        group.addButton( self.change_all )

        self.show_adv = QtWidgets.QToolButton( self )
        self.show_adv.setIcon( getStdIcon( QtWidgets.QStyle.SP_FileDialogInfoView ) )
        self.show_adv.setStatusTip( "Advanced" )
        self.show_adv.setToolTip( "Show Advanced Attributes" )
        self.show_adv.setCheckable( True )

        self.reset_atr = QtWidgets.QToolButton( self )
        self.reset_atr.setIcon( getStdIcon( QtWidgets.QStyle.SP_DialogResetButton ) )
        self.reset_atr.setStatusTip( "Reset" )
        self.reset_atr.setToolTip( "Reset to Default" )
        self.reset_atr.setCheckable( False )

        atrib_tools.addWidget( QtWidgets.QWidget() )
        atrib_tools.addWidget( self.change_sel )
        atrib_tools.addWidget( self.change_all )
        atrib_tools.addWidget( self.show_adv   )
        atrib_tools.addSeparator()
        atrib_tools.addWidget( self.reset_atr  )

        self.change_sel.setChecked( True )

    def registerNodeType( self, node_type ):
        """
        Currently we just build node specific UIs here, we could also switch in other functionality perhaps?
        Args:
            node_type: (str) Type Info for the Node we are registering
        """
        ui_data = uiNodeFactory( node_type )
        temp = self._makePanel( ui_data, False )
        self._forms[ node_type ] = temp
        self.stack.addWidget( temp )

        if( ui_data.has_advanced ):
            temp = self._makePanel( ui_data, True )
            self._forms_adv[ node_type ] = temp
            self.stack.addWidget( temp )

        print( self._forms.keys() )
        print( self._forms_adv.keys() )

    def _makePanel( self, ui_node, do_advanced ):
        """
        Build the Attribute editor for the supplied node.
        Args:
            ui_node: (nodelike) The node to build UI for
            do_advanced: (bool) should we do the advanced options?

        Returns:
            scroll: (QScrollArea)
        """
        # make a scroll area containing the grid
        scroll = QtWidgets.QScrollArea( self )
        scroll.setWidgetResizable( True )
        area = QtWidgets.QWidget( scroll )
        scroll.setWidget( area )
        grid = QtWidgets.QGridLayout()

        # Assemble controls
        box_list = []
        depth = 0
        for key in ui_node.trait_order:
            t = ui_node.traits[ key ]

            if( t.isAdvanced() and not do_advanced ):
                #print( "skipping", key )
                continue

            # Label
            lab = QtWidgets.QLabel( t.name )
            lab.setToolTip( key )
            grid.addWidget( lab, depth, 0 )

            # Knob
            knob = QKnob( self, t.max, t.min, t.default, t.desc )
            grid.addLayout( knob, depth, 1 )
            knob.valueChanged.connect( partial( self.valueChanged, key, "try" ) )
            knob.valueSet.connect( partial( self.valueSet, key, "set" ) )

            # fix [Tab] Order
            if( len( box_list ) > 0 ):
                area.setTabOrder( box_list[-1], knob.box )
            box_list.append( knob.box )

            depth += 1
        # Loop around, if boxes available
        # if (len( box_list ) > 0):
        #     area.setTabOrder( box_list[-1], box_list[0] )

        # Complete
        area.setLayout( grid )
        return scroll

    def valueChanged( self, key, action, value ):
        """
        Slot called when one of the field editors make a change.
        Args:
            key: (str) The attribute key that's been changed.
            action: (str) SET or TRY, only SET actions go onto the Undo stack.
            value: (any) Value changed.

        Returns:

        """
        # This info needs to work it's way back up to the app and MVC for the data
        print( key, action, value )
        app = self.parent()
        app.sendCNC( action, key, value )

    def valueSet( self, key, action, value ):
        """ as above """
        print( key, action, value )
        app = self.parent()
        app.sendCNC( action, key, value )

    def setModels( self, item_model, selection_model ):
        """ Attach the data and selection models """
        self._model = item_model
        #self._model.dataChanged.connect( self.onDataChange )
        self._select = selection_model

    def onDataChange( self, change_idx ):
        """ Slot called by selection model when data changes."""
        pass

    def onSelectionChanged( self, _selected, _deselected ):
        """
        Slot called when selection changes.  Keeps the displayed editor in agreement with the lean selection item.
        Args:
            _selected: unused
            _deselected: unused
        """
        if( self._select is None ):
            return
        # Currently assuming the last node is the lead node...
        selection = self._select.selection().indexes()
        if( len( selection ) > 0 ):
            self._current = selection[-1].data( role=ROLE_TYPEINFO )
        else:
            self._current = None

        self.updateArea()

    def updateArea( self ):
        """
        Switches the display to the selected node.
        """
        if( self.show_adv.isChecked() ):
            if( self._current in self._forms_adv ):
                self.stack.setCurrentWidget( self._forms_adv[ self._current ] )
                return

            # if not in advanced, fall through
        if( self._current in self._forms ):
            self.stack.setCurrentWidget( self._forms[ self._current ] )
        else:
            # unidentified
            self.stack.setCurrentWidget( self._forms[ type( None ) ] )

    def _buildUI( self ):
        """ assemble UI, trigger a dummy change to show the "None" editor. """
        self._mini_main = QtWidgets.QMainWindow()
        self._mini_main.setCentralWidget( self.stack )

        self._buildToolbar()

        # set events
        self.show_adv.clicked.connect( self.updateArea )

        # Finish
        self.setWidget( self._mini_main )
        self.onSelectionChanged( None, None )
