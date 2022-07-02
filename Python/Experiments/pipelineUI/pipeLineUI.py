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

import sys, os 

from collections import OrderedDict
from functools import partial
from glob import glob

from PySide2 import QtWidgets, QtCore

from traits import OpFactory, Pipeline, lexicalBool


class QEditTick( QtWidgets.QCheckBox ):

    """ A CheckBox that acts like a LineEdit
    
    Signals:
        editingFinished(): Fired when the check has been toggled
    """
    
    editingFinished = QtCore.Signal()

    def __init__( self, parent ):
        super( QEditTick, self ).__init__( parent )
        self.stateChanged.connect( self._announce )

    def _announce( self ):
        # Plumbing to emit the "editingFinished" event
        self.editingFinished.emit()

    def text( self ):
        # overload inherit from QAbstractButton, respond like a LineEdit
        return True if bool( self.isChecked() ) else False

    def setText( self, value ):
        # overload inherit from QAbstractButton, respond like a LineEdit
        self.blockSignals( True ) # this is called programatically, so block
        self.setChecked( lexicalBool( value ) )
        self.blockSignals( False )


class QEditComb( QtWidgets.QComboBox ):

    """ A ComboBox that acts like a LineEdit
    
    Signals:
        editingFinished(): Fired when a selection has been made
    """
    
    editingFinished = QtCore.Signal()

    def __init__( self, parent, items ):
        super( QEditComb, self ).__init__( parent )
        self._item_list = items
        self.setEditable( False )
        self.addItems( self._item_list )
        self.activated.connect( self._announce )

    def _announce( self ):
        # Plumbing to emit the "editingFinished" event
        self.editingFinished.emit()

    def text( self ):
        # overload inherit from QAbstractButton, respond like a LineEdit
        return self.currentText()

    def setText( self, value ):
        # overload inherit from QAbstractButton, respond like a LineEdit
        if( value not in self._item_list ):
            return

        self.setCurrentText( value )


TraitUIFactory = {
    "INT"   : QtWidgets.QLineEdit,
    "FLOAT" : QtWidgets.QLineEdit,
    "STR"   : QtWidgets.QLineEdit,
    "BOOL"  : QEditTick,
    "DESC"  : QEditComb,
}


class PipelineExecuter( QtCore.QObject ):

    emitStatus = QtCore.Signal( int, str )
    finished   = QtCore.Signal()

    def __init__( self, the_pipeline, start_idx ):
        """ A QObject that can be moved to a QThread to run a pipline

        Args:
            the_pipeline (Pipeline): Pipeline object to execute
            start_idx (int): Operation 'step' to start running
        """
        super( PipelineExecuter, self ).__init__()
        self._pipe = the_pipeline
        self._idx = start_idx

    def do( self ):
        self._pipe.status_reporter = self.reportStatus
        self._pipe.runFrom( self._idx ) # The Blocking call
        self._pipe.status_reporter = None
        # Pipeline complete
        self.finished.emit()

    def reportStatus( self, idx, report ):
        self.emitStatus.emit( idx, report )    


class QOperationChooser( QtWidgets.QDialog ):

    def __init__( self, parent, op_data ):
        """ Dialog to help choose an operation

            retrive the selected operation by accessing 'X.selected'
        
        Args:
            parent (QtWidget): Owning Qt Application
            op_data (dict): Operation data like {"op name":"op description"}
        """
        super( QOperationChooser, self ).__init__( parent )
        self.selected = None
        self._op_data = op_data
        self._buildUI()

    def _changed( self, operation_name ):
        """ Update the hint text, and capture the current selection
        
        Args:
            operation_name (str): name of the Selected Operation from the combobox
        """
        self._hint.setPlainText( self._op_data[ operation_name ] )
        self.selected = operation_name

    def _buildUI( self ):
        """
            Build the Operation Chooser UI
        """
        self.setWindowTitle( "Choose an Operation to Add" )

        layout = QtWidgets.QVBoxLayout()

        # Label
        l = QtWidgets.QLabel( "Select an operation to Add to the Pipeline" )
        layout.addWidget( l )

        # Operations Combo box
        self._comb = QtWidgets.QComboBox()
        self._comb.addItems( list( self._op_data.keys() ) )
        self._comb.setEditable( False )
        layout.addWidget( self._comb )

        # description text
        self._hint = QtWidgets.QTextEdit()
        self._hint.setFontPointSize( 12.0 )
        self._hint.resize( 120, 120 )
        layout.addWidget( self._hint )

        # Buttons
        but_layout = QtWidgets.QHBoxLayout()
        but_choose = QtWidgets.QPushButton( "Add selected Operation" )
        but_layout.addWidget( but_choose )
        but_cancel = QtWidgets.QPushButton( "Cancel" )
        but_layout.addWidget( but_cancel )
        layout.addLayout( but_layout )

        # Hookup events
        self._comb.currentTextChanged.connect( self._changed )
        but_choose.clicked.connect( self.accept )
        but_cancel.clicked.connect( self.reject )

        # force event
        self._comb.setCurrentIndex( 1 )
        self._comb.setCurrentIndex( 0 )

        # Done
        self.setLayout( layout )


class QPipeLinePanel( QtWidgets.QWidget ):

    TOOLNAME  = "Pipeline Editor"

    HEADINGS  = ( "Active", "Status", "Name" )
    ENABLED   = 0
    STATUS    = 1
    OPERATION = 2

    ROLE_OPERATION = QtCore.Qt.UserRole + 1
    ROLE_OPERATION_NAME = QtCore.Qt.UserRole + 2

    def __init__( self, parent=None, pipe_to_load=None, default_path="" ):
        super( QPipeLinePanel, self ).__init__()

        # Pipeline Object
        self.pipeline = Pipeline()

        # populate available pipes
        self._pipelines_path = default_path
        self._avail_pipes = OrderedDict()
        self._populatePipeList()

        # Find available operations
        self._avail_ops = list( OpFactory.keys() )

        # make look up of operation descriptions
        self._op_data = { k:i.OPERATION_DESC for k,i in OpFactory.items() }

        # Setup stacked UI
        self._current = None
        self._forms = {}      # {<Op Type>:'it's interface form'}
        self._form_ctrls = {} # {<Op Type>:{attr:control,...}}

        # Stack Widget
        self.stack = QtWidgets.QStackedWidget()

        # 'None selected' form
        temp = QtWidgets.QLabel( "Nothing Selected" )
        temp.setAlignment( QtCore.Qt.AlignCenter )
        self._forms[ type( None ) ] = temp
        self.stack.addWidget( temp )
            
        # Build UI
        self._QActs = {}
        self._buildUI()

        # for testing, force load a pipeline file
        if( pipe_to_load is not None ):
            self._combo_pipes.setCurrentText( pipe_to_load )
            # force load if currentText was already 'pipe_to_load' (which won't fire an event)
            self._onSwitchPipe( pipe_to_load )

        # Finalize
        self.show()

    @staticmethod
    def _boolToCheck( boolean ):
        """
            translates a boolean to a Qt Const (int?)

        Args:
            boolean (bool): a truth value
        
        Returns:
            QtCore.Qt.(un)checked: the truth value as the Qt Const that defines a checkboxe's checked-ness
        """
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    #-- Pipeline Editor ----------------------------------------------------------------------------------------------#
    def loadPipeline( self, file_fq ):
        """ Load a pipeline jpf from the given file path
        
        Args:
            file_fq (str): fully qualified path to the pipeline jpf file
        """
        if( os.path.exists( file_fq ) ):
            self.pipeline.loadFile( file_fq )
            self.refreshPipelineTable()
            print( "loaded '{}'".format( file_fq ) )

        else:
            print( "'{}' does not exist".format( file_fq ) )

    def refreshPipelineTable( self ):
        """
            Rebuild the pipeline table with the program from the pipeline object
        """
        self.pipe.blockSignals( True )
        self.pipe.clearContents()
        self.pipe.setRowCount( 0 )
        self.pipe.setRowCount( len( self.pipeline ) )
        for i, operation in enumerate( self.pipeline.pipeline ):
            # Make items
            chk_itm = QtWidgets.QTableWidgetItem( "" )
            chk_itm.setCheckState( self._boolToCheck( operation.active ) )
            
            stat_itm = QtWidgets.QTableWidgetItem( "" )

            act_itm = QtWidgets.QTableWidgetItem( operation.user_tag )
            act_itm.setToolTip( operation.OPERATION_NAME )
            act_itm.setData( self.ROLE_OPERATION, operation )
            act_itm.setData( self.ROLE_OPERATION_NAME, operation.OPERATION_NAME )

            # Place in table
            self.pipe.setItem( i, self.ENABLED, chk_itm  )
            self.pipe.setItem( i, self.STATUS,  stat_itm )
            self.pipe.setItem( i, self.OPERATION,  act_itm  )

            # ensure there is UI for the operatoin
            if( type( operation ) not in self._forms ):
                self._addOperationProps( operation )

        self.pipe.blockSignals( False )

    def resetPipeStatus( self ):
        """
            reset all Operation's 'status' field with a blank (no information)
        """
        for i in range( self.pipe.rowCount() ):
            stat_itm = QtWidgets.QTableWidgetItem( "" )
            self.pipe.setItem( i, self.STATUS,  stat_itm )

    def setPipeStatus( self, row, status ):
        """
        Anotate the pipeline Operation at 'row' with the given 'status'
        
        Args:
            row (int): pipeline row
            status (str): row's new status
        """
        itm = self.pipe.item( row, self.STATUS )
        # todo: in the future this could be a pretty graphic
        itm.setText( status )
        #self.pipe.update()

    def _populatePipeList( self ):
        """
            Scan the current pipeline folder for Json Pipeline Files (.JPF).
        """
        search = os.path.join( self._pipelines_path, "*" + self.pipeline.EXTENSION )
        pipes = glob( search )
        self._avail_pipes.clear()
        for pipe in pipes:
            filename = os.path.basename( pipe )
            name, _ = filename.rsplit( ".", 1 )
            self._avail_pipes[ name ] = pipe

    def _updatePipeCombo( self ):
        """
            update the combobox with available pipelines
        """
        self._combo_pipes.clear()
        self._combo_pipes.addItems( list( self._avail_pipes.keys() ) )

    def _onPipelineSelectionChanged( self, selected, deselected_ ):
        """
            Handler for when an Operation is selected in the pipline table, updates the properties panel.
        
        Args:
            selected (Selection): newly selected row
            deselected_ (Selection): the deselected row (unused)
        """
        sel_row = None
        for idx in selected.indexes():
            sel_row = idx.row()
            break # should only ever be one row selected
        
        if( sel_row is None ):
            self._current = None
            return

        # get the Operation
        act_itm = self.pipe.item( sel_row, self.OPERATION )
        operation = act_itm.data( self.ROLE_OPERATION )
        self._current = operation

        # Update properties panel
        # add Opperations in the new pipeline to the Panel

        self.toggleProps()

        self.updateProps()

    def getSelectedRow( self ):
        """
            Get current selected row, or None if nothing selected
        
        Returns:
            int or None: selected row index of the pipeline, or None if nothing selected.
        """
        indexes = self.pipe.selectionModel().selectedRows()
        for idx in indexes:
            return idx.row()

        return None

    # Context menu for the Pipeline #
    def _do_popup( self, point ):
        """
            Show pipeline editor context menu
        """
        self._popup.exec_( self.pipe.mapToGlobal( point ) )

    #-- Properties Panel for the selected operation ------------------------------------------------------------------#
    def _addOperationProps( self, operation ):
        """
        Make a property panel for the given operation and add to the stack
        
        Args:
            operation (AbsractOperation): the operation
        """
        form = self._makePanel4Op( operation )
        self._forms[ type( operation ) ] = form
        self.stack.addWidget( form )

    def _uiTraitFactory( self, trait ):
        """
        Return a Widget suitable for adjusting the supplied triat
        
        Args:
            trait (Trait): The data trait we need UI for
        
        Returns:
            TYPE: Description
        """
        control = TraitUIFactory.get( trait.TYPE, None )

        if( trait.TYPE == "DESC" ):
            # add the list
            return control( self, trait.options )    

        return control( self )
    
    def _makePanel4Op( self, op_instance ):
        """
            Build the properties panel for the supplied operation.
        
        Args:
            op_instance (AbsractOperation): the Operation we're making UI for
        
        Returns:
            scroll (QScrollArea): the scrollArea containing the UI
        """
        # make a scroll area containing the grid
        scroll = QtWidgets.QScrollArea( self )
        scroll.setWidgetResizable( True )
        area = QtWidgets.QWidget( scroll )
        scroll.setWidget( area )
        grid = QtWidgets.QGridLayout()

        
        ctrl_lut = {}
        # Assemble controls
        depth = 0
        for attr in op_instance.trait_order:
            trait = op_instance.traits[ attr ]

            # Get the appropriate Knob, Dial, or Edit
            control = self._uiTraitFactory( trait )
            if( control is None ):
                print( "No Control for '{}' ".format( trait.name ) )
                continue

            # Add Label
            lab = QtWidgets.QLabel( trait.name )
            if( trait.advanced ):
                # TODO: Show Gide Advanced options toggle.
                font = lab.font()
                font.setItalic( True )
                lab.setFont( font )
                
            lab.setToolTip( trait.desc )
            grid.addWidget( lab, depth, 0 )

            # Add widget
            grid.addWidget( control, depth, 1 )

            # Setup value changing callbacks
            control.editingFinished.connect( partial( self._onPropChange, attr ) )

            # register
            ctrl_lut[ attr ] = control

            # next row
            depth += 1

        # Complete UI
        grid.setRowStretch( depth, 1 )
        area.setLayout( grid )

        # Register Controls
        self._form_ctrls[ type( op_instance ) ] = ctrl_lut

        return scroll
    
    def _onPropChange( self, attr ):
        """
        Set the current Operation's attr to the value of the attr's control in the properties panel.
        
        Args:
            attr (str): the Operation's attribute name

        """
        op = self._current
        if( op is None ):
            return

        control = self._form_ctrls[ type( self._current ) ][ attr ]
        trait = self._current.traits.get( attr, None )
        if( control is None or trait is None ):
            print( "got None" )
            return

        val = trait.fromString( control.text() )
        # Could validate here...
        self._current.setTrait( attr, val )

    def toggleProps( self ):
        """
            Switches the stacked widget to the panel for the selected Operation.
        """
        op_type = type( self._current )
        if( op_type in self._forms ):
            self.stack.setCurrentWidget( self._forms[ op_type ] )
            # Load the widgets with the op's props current values
            # TODO!
            
        else:
            # unidentified / None selected
            self.stack.setCurrentWidget( self._forms[ type( None ) ] )

    def updateProps( self ):
        """
            Update the current props form with the current op's trait values
        """
        ctrl_lut = self._form_ctrls[ type( self._current ) ]
        for attr in self._current.trait_order:
            control = ctrl_lut.get( attr, None )
            if( control is None ):
                print( "Error unfound control" )
                return

            control.setText( self._current.traits[ attr ].toString() )

    def threadRunFrom( self, idx ):
        """ 
        
        Args:
            idx (int): 'Step' of the pipeline to start running at
        """
        # Lock UI?
        self.pipe_op_runner = PipelineExecuter (self.pipeline, idx )
        self.pipe_op_runner.emitStatus.connect( self.setPipeStatus )

        self.thread = QtCore.QThread()
        self.thread.started.connect( self.pipe_op_runner.do )
        self.pipe_op_runner.finished.connect( self.thread.quit )
        self.pipe_op_runner.moveToThread( self.thread )

        self.thread.start()
        # Unlock UI

    #-- Qt Actions ---------------------------------------------------------------------------------------------------#
    def _configureActions( self ):
        """
            Set up the Qt Actions and attach to the toolbar or popup palete as needed
        """
        # the actions
        tool_actions = ( "New", "Open...", "Save", "Save As...", "Run Pipeline", "Add Op", "Move Op Up", "Move Op Dn", 
                         "Remove Op", "Run From Here", "Reset to Defaults", )
        for act in tool_actions:
            self._QActs[ act ] = QtWidgets.QAction( act, self )

        # Setup Toolbar
        self.tool_bar = QtWidgets.QToolBar( "Test", self )

        self.tool_bar.addAction( self._QActs[ "New" ] )
        self.tool_bar.addAction( self._QActs[ "Open..." ] )
        self.tool_bar.addSeparator()
        self.tool_bar.addAction( self._QActs[ "Save" ] )
        self.tool_bar.addAction( self._QActs[ "Save As..." ] )
        self.tool_bar.addSeparator()
        self.tool_bar.addAction( self._QActs[ "Run Pipeline" ] )
        self.tool_bar.addSeparator()
        self.tool_bar.addAction( self._QActs[ "Add Op" ] )
        self.tool_bar.addAction( self._QActs[ "Move Op Up" ] )
        self.tool_bar.addAction( self._QActs[ "Move Op Dn" ] )

        # Setup Pipeline Popup
        self._popup = QtWidgets.QMenu( self )

        self._popup.addAction( self._QActs[ "Run Pipeline" ] )
        self._popup.addAction( self._QActs[ "Run From Here" ] )
        self._popup.addSeparator()
        self._popup.addAction( self._QActs[ "Add Op" ] )
        self._popup.addAction( self._QActs[ "Remove Op" ] )
        self._popup.addSeparator()
        self._popup.addAction( self._QActs[ "Move Op Up" ] )
        self._popup.addAction( self._QActs[ "Move Op Dn" ] )
        self._popup.addSeparator()
        self._popup.addAction( self._QActs[ "Reset to Defaults" ] )

        # Connect the Actions to callbacks
        self._QActs[ "New" ].triggered.connect( self._cb_newPipe )
        self._QActs[ "Open..." ].triggered.connect( self._cb_openPipe )

        self._QActs[ "Save" ].triggered.connect( self._cb_savePipe )
        self._QActs[ "Save As..." ].triggered.connect( self._cb_saveAsPipe )

        self._QActs[ "Run Pipeline" ].triggered.connect( self._cb_runPipe )
        self._QActs[ "Run From Here" ].triggered.connect( self._cb_runFromPipe )

        self._QActs[ "Add Op" ].triggered.connect( self._cb_addOp )
        self._QActs[ "Remove Op" ].triggered.connect( self._cb_remOp )

        self._QActs[ "Move Op Up" ].triggered.connect( self._cb_opUp )
        self._QActs[ "Move Op Dn" ].triggered.connect( self._cb_opDn )

        self._QActs[ "Reset to Defaults" ].triggered.connect( self._cb_opReset )

    def _promptSaveCurrent( self ):
        """Prompt suggesting the user saves the pipeline 
        
        Returns:
            bool: True is good to continue, or False if op Canceled
        """
        ret = QtWidgets.QMessageBox.warning( self, "Save Current?", "Current Pipeline has unsaved changes,\ndo you want to save?",
                                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                                QtWidgets.QMessageBox.Save )

        if( ret == QtWidgets.QMessageBox.StandardButton.Save ):
            self._cb_savePipe()

        elif( ret == QtWidgets.QMessageBox.StandardButton.Cancel ):
            print( "Cancel New" )
            return False

        return True

    #-- Action Callbacks ---------------------------------------------------------------------------------------------#
    def _cb_newPipe( self ):
        """
            Action Callback: Create a new Pipeline in a named file
        """
        # Prompt Save existing?
        if( self.pipeline.isChanged() ):
            cont = self._promptSaveCurrent()
            if( not cont ):
                return

        unique = False
        while( not unique ):
            # Prompt New Pipeline name
            text, res = QtWidgets.QInputDialog().getText( self, "New Pipeline", "Name:", QtWidgets.QLineEdit.Normal, "myPipeline" )

            if( not res ): # Canceled
                return

            # check for unqiueness 
            if( text not in self._avail_pipes ):
                unique = True

            else:
                ret = QtWidgets.QMessageBox.warning( self, "Not Unique",
                                "Pipeline '{}' already exists.\nPlease give the pipeline a unique name.".format( text ),
                                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok )

        # Clear existing
        print( text )
        self.pipeline = Pipeline( name=text )
        self.pipeline.loaded_from = os.path.join( self._pipelines_path, text+self.pipeline.EXTENSION )
        self.refreshPipelineTable()

        # touch a jpf
        self._cb_savePipe()

        # Add to Drop
        self._populatePipeList()
        self._updatePipeCombo()

    def _cb_openPipe( self ):
        """
            Action Callback: Open a pipeline file (from new directory)
        """
        if( self.pipeline.isChanged() ):
            ok2continue = self._promptSaveCurrent()
            if( not ok2continue ):
                return

        # Prompt Open
        file_fq, _ = QtWidgets.QFileDialog.getOpenFileName( self, "Open Pipeline", self._pipelines_path,
                                                            "JSON Pipeline File (*{}})".format( self.pipeline.EXTENSION ) )
        print( "Opening >{}<".format( file_fq ) )

        # Load
        if( file_fq ):
            self.loadPipeline( file_fq )

    def _cb_savePipe( self ):
        """
            Action Callback:  Silently save current pipeline
        """
        self.pipeline.saveFile( self.pipeline.loaded_from )
        print( "Saved '{}'".format( self.pipeline.loaded_from ) )
        self.pipeline.justSaved()

    def _cb_saveAsPipe( self ):
        """
            Action Callback: Save the current pipeline to a new file.  this updates the combobox of pipelines """
        # prompt savename
        file_fq, _ = QtWidgets.QFileDialog.getSaveFileName( self, "Save Pipeline", self._pipelines_path,
                                                            "JSON Pipeline File (*{}})".format( self.pipeline.EXTENSION ) )

        if( file_fq ):
            # Save silent
            self.pipeline.saveFile( file_fq )
            self.pipeline.loaded_from = file_fq

            # reset 'needs2save'
            self.pipeline.justSaved()

            # popPipes
            self._populatePipeList()
            self._updatePipeCombo()

    def _cb_runPipe( self ):
        """
            Action Callback: Run the whole Pipeline from the start
        """
        self.threadRunFrom( 0 )

    def _cb_runFromPipe( self ):
        """
            Action Callback: Run the pipeline from currently selected Operation
        """
        self.threadRunFrom( self.getSelectedRow() )

    def _cb_addOp( self ):
        """
            Action Callback: Add a new Operation to the pipeline, after the currently selected row """
        row = self.getSelectedRow()
        if( row is None ): # starting an empty pipeline?
            row = 0
        else:
            row += 1

        # Propmt for operation to add
        chooser = QOperationChooser( self, self._op_data )

        if( chooser.exec_() == QtWidgets.QDialog.Accepted ):
            op_name = chooser.selected

            # make a new operation
            operation = OpFactory[ op_name ]()

            # add it's properties panel to the stack
            if( type( operation ) not in self._forms ):
                self._addOperationProps( operation )

            # Insert in pipeline
            self.pipeline.insertOperation( operation, row )
            self.refreshPipelineTable()
            if( row >= self.pipe.rowCount() ):
                row -= 1
            self.pipe.selectRow( row )

        del( chooser )

    def _cb_remOp( self ):
        """
            Action Callback: Remove Operation from pipeline
        """
        row = self.getSelectedRow()
        # remove idx from pipeline
        _ = self.pipeline.removeOperation( idx=row )
        self.refreshPipelineTable()
        self.pipe.selectRow( row )

    def _cb_opUp( self ):
        """
            Action Callback: Move Operation up the pipeline order
        """
        row = self.pipeline.nudge( self._current, True )
        # rebuild table
        self.refreshPipelineTable()
        self.pipe.selectRow( row )
        
    def _cb_opDn( self ):
        """
            Action Callback: Move Operation down the pipeline order
        """
        row = self.pipeline.nudge( self._current, False )
        # rebuild table
        self.refreshPipelineTable()
        self.pipe.selectRow( row )

    def _cb_opReset( self ):
        """
            Action Callback: Reset the ipeline
        """
        op = self._current
        if( op is None ):
            return

        op.resetDefaults()

    #== Other CBs ----------------------------------------------------------------------------------------------------#
    def _onItmChange( self, item ):
        """ React to changes to Pipeline items getting changed
        
        Args:
            item (QTableWidgetItem): the data item getting changed
        """
        row, col = item.row(), item.column()
        operation = self.pipeline.pipeline[ row ]

        if( col == self.ENABLED ):
            # toggle activation of the selected operation
            operation.active = bool( item.checkState() == QtCore.Qt.CheckState.Checked )

        elif( col == self.OPERATION ):
            # rename the operation
            operation.user_tag = str( item.text() )

    def _onSwitchPipe( self, pipe_name ):
        """ React to the combobox changing and load the selected pipeline
        
        Args:
            pipe_name (str): name of the pipeline
        """
        if( self.pipeline.isChanged() ):
            ok2continue = self._promptSaveCurrent()
            if( not ok2continue ):
                return

        file_fq = os.path.join( self._pipelines_path, str( pipe_name ) + self.pipeline.EXTENSION )
        self.loadPipeline( file_fq )

    #-- The Main UI Build --------------------------------------------------------------------------------------------#
    def _buildUI( self ):
        """
            Build the pipeline editor UI
        """
        box = QtWidgets.QVBoxLayout( self )
        
        # actions and toolbar
        self._configureActions()

        box.addWidget( self.tool_bar )

        # Pipeline Selector
        hbox = QtWidgets.QHBoxLayout()
        
        l = QtWidgets.QLabel( "Current Pipeline:" )
        hbox.addWidget( l )

        self._combo_pipes = QtWidgets.QComboBox( self )
        hbox.addWidget( self._combo_pipes )
        self._updatePipeCombo()
        box.addLayout( hbox )
        
        # 'Add op' Button
        b = QtWidgets.QToolButton()
        b.setDefaultAction( self._QActs[ "Add Op" ] )
        b.setText( "Add Operation" )
        b.setSizePolicy( QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum )
        box.addWidget( b )

        # The Pipline menu
        self.pipe = QtWidgets.QTableWidget( self )
        #self.pipe.setItemDelegate( QPipeLinePanel.CenteredDelegate() )

        # Headings
        self.pipe.setColumnCount( len( self.HEADINGS ) )
        self.pipe.setHorizontalHeaderLabels( self.HEADINGS )
        header = self.pipe.horizontalHeader()
        header.setSectionResizeMode( 0, QtWidgets.QHeaderView.ResizeToContents )
        header.setSectionResizeMode( 1, QtWidgets.QHeaderView.ResizeToContents )
        header.setSectionResizeMode( 2, QtWidgets.QHeaderView.Stretch )
        
        # Dissable Dropping
        self.pipe.setDragEnabled( False )
        self.pipe.setAcceptDrops( False )
        self.pipe.viewport().setAcceptDrops( False )
        self.pipe.setDragDropOverwriteMode( False )
        self.pipe.setDropIndicatorShown( False )

        # set Dropping Mode
        self.pipe.setSelectionMode( QtWidgets.QAbstractItemView.SingleSelection ) 
        self.pipe.setSelectionBehavior( QtWidgets.QAbstractItemView.SelectRows )

        pipe_scroll = QtWidgets.QScrollArea( self )
        pipe_scroll.setWidgetResizable( True )
        pipe_scroll.setWidget( self.pipe )

        splitter = QtWidgets.QSplitter( QtCore.Qt.Vertical )
        splitter.addWidget( pipe_scroll )
        splitter.addWidget( self.stack )
                
        box.addWidget( splitter )
        
        # Reset Params
        b = QtWidgets.QToolButton()
        b.setDefaultAction( self._QActs[ "Reset to Defaults" ] )
        b.setText( "Reset" )
        b.setSizePolicy( QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum )
        box.addWidget( b )

        # Setup callbacks ###############################################################
        # Enable popup menu for the table
        self.pipe.setContextMenuPolicy( QtCore.Qt.CustomContextMenu )
        self.pipe.customContextMenuRequested.connect( self._do_popup )

        # Operation Selction
        selection_model = self.pipe.selectionModel()
        selection_model.selectionChanged.connect( self._onPipelineSelectionChanged  )

        # try to find when checkboxes are changed
        self.pipe.itemChanged.connect( self._onItmChange )

        # Attach a callback to the combobox change event
        self._combo_pipes.currentTextChanged.connect( self._onSwitchPipe )

        # Complete
        self.setWindowTitle( self.TOOLNAME )
        

if __name__ == '__main__':
    app = QtWidgets.QApplication( sys.argv )
    app.setStyle( "Fusion" )

    ex = QPipeLinePanel( app, "testPipeline" )
    sys.exit( app.exec_() )
