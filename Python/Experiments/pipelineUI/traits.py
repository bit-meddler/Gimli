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

import json
import os
from time import sleep
import uuid


def lexicalBool( in_string ):
    """ 'cast' the common truth meaning of various tokens to a bool
        
    """
    s = in_string.lower()

    if( s in ("true", "yes", "1", "y") ):
        return True

    if( s in ("false", "no", "0", "n") ):
        return False

    return bool( s )


class Trait( object ):
    """
        Lightweight Reconfigurable Trait prototype
    """
    
    TYPE = "NONE"
    castor = None

    def __init__( self, name, default, lo, hi, value, desc, advanced=False ):
        self.name = name
        self.default = default
        self.lo = lo
        self.hi = hi
        self.value = value
        self.desc = desc
        self.advanced = advanced

    def validate( self, candidate ):
        pass
    
    def toString( self ):
        return str( self.value )
    
    def fromString( self, in_string ):
        return self.castor( in_string )


class TraitInt( Trait ):
    
    TYPE = "INT"
    castor = int
    
    def validate( self, candidate ):
        if( type( candidate ) != self.castor ):
            return False

        if( self.lo == self.hi ):
            return True

        if( self.lo <= candidate and candidate <= self.hi ):
            return True

        return False


class TraitFloat( Trait ):

    TYPE = "FLOAT"
    castor = float
    
    def validate( self, candidate ):
        if( type( candidate ) != self.castor ):
            return False

        if( self.lo == self.hi ):
            return True

        if( self.lo <= candidate and candidate <= self.hi ):
            return True

        return False


class TraitBool( Trait ):

    TYPE = "BOOL"
    castor = bool

    def validate( self, candidate ):
        return bool( type( candidate ) == self.castor )

    def fromString( self, in_val ):
        if( type(in_val)==bool ):
            return in_val

        elif( type(in_val)==str ):
            return lexicalBool( in_val )

        else:
            print("Unexpected Bool input type")


class TraitStr( Trait ):

    TYPE = "STR"
    castor = str

    def validate( self, candidate ):
        return bool( type( candidate ) == self.castor )


class TraitDiscrete( TraitStr ):
    
    TYPE = "DESC"

    def __init__( self, name, default, options, value, desc, advanced=False ):
        super( TraitDiscrete, self).__init__(name, default, None, None, value, desc, advanced )
        self.options = options

    def validate( self, candidate ):
        if( type( candidate ) != self.castor ):
            return False

        return bool( candidate in self.options )


class AbstractOperation( object ):

    OPERATION_NAME = "Dummy"
    OPERATION_DESC = """"""
    STATUSES    = ( None, "Preparing", "Running", "Complete", "Failed" )

    def __init__( self ):
        self.user_tag = self.OPERATION_NAME
        self.active = True
        self.trait_order = []
        self.traits = {}
        self.is_changed = False
        self.status = None
        self._report = ""

    #-- Abstract Operation Interface --------------------------------------------#
    def prepare( self ):
        sleep( 1 )

    def execute( self ):
        sleep( 1 )
        if( "fail" in self.user_tag ):
            self.status = "Failed"
            return

        sleep( 2 )
        self.status = "Complete"

    def report( self ):
        return self._report

    #-- Traits ---------------------------------------------------------------#
    def setTrait( self, attr, value ):
        if( not attr in self.trait_order ):
            return

        old = self.traits[ attr ].value
        if( old != value ):
            self.traits[ attr ].value = value
            setattr( self, attr, value )
            self.is_changed = True

    def resetDefaults( self ):
        for attr in self.trait_order:
            self.setTrait( attr, self.traits[ attr ].default )

    #-- Serialization --------------------------------------------------------#
    def paramsToJDict( self ):
        d = {}
        for attr in self.trait_order:
            test = getattr( self, attr, None )
            if( test is not None ):
                d[ attr ] = self.traits[ attr ].toString()
        return d

    def paramsFromJDict( self, d, tag=None ):
        self.resetDefaults()
        for attr in self.trait_order:
            if( attr in d ):
                val = self.traits[ attr ].fromString( d[ attr ] )
                self.setTrait( attr, val )

        if( tag is not None ):
            self.user_tag = tag

        # just loaed to clear 'dirty' flag
        self.is_changed = False

    def makeOpDict( self ):
        d = {}
        d["OPERATION"] = self.OPERATION_NAME
        d["USERTAG"] = self.user_tag
        d["ACTIVE"] = self.active
        d["PARAMS"] = self.paramsToJDict()
        return d

    def fromOpDict( self, d ):
        self.user_tag = d["USERTAG"]
        self.active = d["ACTIVE"]
        self.paramsFromJDict( d["PARAMS"] )


class OpRender( AbstractOperation ):

    OPERATION_NAME = "Render"
    OPERATION_DESC = """Make a Video of the current scene from the currently active camera."""

    def __init__( self ):
        super( OpRender, self ).__init__()
        # Set up Traits
        self.traits = {
            "fps"        : TraitFloat( "fps", 30.0, 30.0, 120.0, 30.0, "Export Framerate" ),
            "doRender"   : TraitBool( "High Quality", True, None, None, False, "Render a Playblast" ),
            "doTimecode" : TraitBool( "Embed Timecode", True, None, None, True, "Embed Timecode" ),
            "appendage"  : TraitStr( "Suffix", "_export", None, None, "_spam", "Export Appendage" ),
            "encoding"   : TraitDiscrete( "Video Codec", "h264", ["h264","mjpg","prores"], "h264", "Encoding type" )
        }
        self.trait_order = ( "fps", "doRender", "doTimecode", "appendage", "encoding" )
        # initalize
        self.resetDefaults()


class OpBake( AbstractOperation ):

    OPERATION_NAME = "Bake"
    OPERATION_DESC = """Bake the Current Solve to a skeleton for export"""

    def __init__( self ):
        super( OpBake, self ).__init__()
        # Set up Traits
        self.traits = {
            "scale"   : TraitFloat( "Global Scale Override", 1.0, 0.01, 10.0, 1.02, "Character Scale" ),
            "doClean"  : TraitBool( "Clean Scene", True, None, None, False, "Delete all but the skeletons" ),
            "mapping" : TraitStr( "Character Mapping", "", None, None, "", "Character Mapping - this is a comma separate list of subject:character" ),
        }
        self.trait_order = ( "scale", "doClean", "mapping")
        # initalize
        self.resetDefaults()


class OpReconstruct( AbstractOperation ):

    OPERATION_NAME = "Reconstruct"
    OPERATION_DESC = """Reconstruct 3D Data by intersecting Centroid Rays."""

    def __init__( self ):
        super( OpReconstruct, self ).__init__()
        # Set up Traits
        self.traits = {
            "noise"      : TraitFloat( "Noise", 1.0, 0.01, 10.0, 1.02, "Camera Noise Factor" ),
            "cams_start" : TraitInt( "Start Cameras", 3, 2, 255, 3, "Minimum Cameras to start Reconstruction" ),
            "cams_track" : TraitInt( "Track Cameras", 2, 2, 255, 3, "Minimum Cameras to continue Reconstruction" ),
            "roid_min"   : TraitFloat( "Centroid min Radius", 1.5, 0.5, 1000, 1.5, "Minimum Centroid radius to contribute" ),
            "roid_max"   : TraitFloat( "Centroid max Radius", 20, 0.5, 1000, 20, "Maximum Centroid radius to contribute" ),
            # advanced settings
            "vel2d"      : TraitFloat( "2d Velocity", 16.0, 5.01, 64.0, 16.0, "2d pixel velocity clamp (px/frm)", True ),
            "vel3d"      : TraitFloat( "3d Velocity", 180.0, 50, 500.0, 180.0, "3d marker velocity clamp (mm/s)", True ),
        }
        self.trait_order = ( "noise", "cams_start", "cams_track", "roid_min", "roid_max", "vel2d", "vel3d" )
        # initalize
        self.resetDefaults()


class OpBoot( AbstractOperation ):

    OPERATION_NAME = "Boot"
    OPERATION_DESC = """Attempt to Boot the labelling of the subject(s) on a given frame."""

    def __init__( self ):
        super( OpBoot, self ).__init__()
        # Set up Traits
        self.traits = {
            "first_frame"  : TraitInt( "Boot Frame", 0, 0, 1_000_000, 0, "Frame to run Booting operation on" ),
            "doSubjects"   : TraitDiscrete( "Subjects to Boot", "all", ["all","listed"], "all", "Boot all subjects or just those listed"),
            "subject_list" : TraitStr( "List of Subjects", "", None, None, "", "Only boot the subjects listed here, only effective is 'Subjects to Boot' is 'all'." ),
            "doRobust"     : TraitBool( "Robust Booting", True, None, None, False, "Only label fully present subjects" ),
            "presenceTrsh" : TraitFloat( "Presence Threshold", 45.0, 10.0, 100.0, 55.0, "Percentage of Markers ID'd to begin tracking", True ),
            
        }
        self.trait_order = ( "doSubjects", "subject_list", "doRobust", "presenceTrsh" )
        # initalize
        self.resetDefaults()


class OpTrack( AbstractOperation ):

    OPERATION_NAME = "Track"
    OPERATION_DESC = """Track any booted subject forward in the scene, from a given first frame for a given duration, 'Frames to Track' is smart and will go backwards if 'Track Forward' is off, and clamp to the extents of the file."""

    def __init__( self ):
        super( OpTrack, self ).__init__()
        # Set up Traits
        self.traits = {
            "predictionClamp" : TraitFloat( "Prediction Factor", 1.0, 0.01, 10.0, 1.02, "Kinematic prediction clamp factor" ),
            "doForward"       : TraitBool( "Track Forward", True, None, None, False, "Track forwards" ),
            "doReboot"        : TraitBool( "Auto Boot", True, None, None, False, "Attempt to reboot if a subject's track is lost" ),
            "first_frame"     : TraitInt( "First Frame", 0, 0, 1_000_000, 0, "Frame to start tracking on, -1 means the last frame" ),
            "track_frames"    : TraitInt( "Frames to Track", -1, -1, 1_000_000, -1, "Number of frames to track, -1 means all" ),

        }
        self.trait_order = ( "predictionClamp", "doForward", "doReboot", "first_frame", "track_frames" )
        # initalize
        self.resetDefaults()


class OpSolve( AbstractOperation ):

    OPERATION_NAME = "Solve"
    OPERATION_DESC = """Refinet the solution of a tracked file, with additional Kinematic filtering."""

    def __init__( self ):
        super( OpSolve, self ).__init__()
        # Set up Traits
        self.traits = {
            "doSubjects"   : TraitDiscrete( "Subjects to Solve", "all", ["all","listed"], "all", "Solve all subjects or just those listed"),
            "subject_list" : TraitStr( "List of Subjects", "", None, None, "", "Only Solve the subjects listed here, only effective is 'Subjects to Solve' is 'all'." ),
            "doImplyMkrs"  : TraitBool( "Create Implyed Markers", True, None, None, False, "Create Implyed Markers when there are no ray contributions." ),
            "doKineSmooth" : TraitBool( "Kinematic Smoothing", True, None, None, False, "Apply Kinematic Smoothing to the solution" ),
            "kineFactor"   : TraitFloat( "Kinematic Smoothing Factor", 1.0, 0.01, 10.0, 1.02, "Kinematic prediction clamp factor", True ),
        }
        self.trait_order = ("doSubjects", "subject_list", "doImplyMkrs", "doKineSmooth", "kineFactor" )
        # initalize
        self.resetDefaults()



OpFactory = {
    "Reconstruct" : OpReconstruct,
    "Boot"        : OpBoot,
    "Track"       : OpTrack,
    "Solve"       : OpSolve,
    "Bake"        : OpBake,
    "Render"      : OpRender,
}

class Pipeline( object ):

    EXTENSION = ".jpf"

    def __init__( self, name=None ):
        self.pipe_name = name or "Default"
        self.loaded_from = ""
        self.pipeline = []
        self.status_reporter = None

    #-- Pipeline Execution ---------------------------------------------------#
    def runFrom( self, idx=0 ):
        # Prep list of ops to act on
        active_ops = []
        for i, operation in enumerate( self.pipeline ):
            if( operation.active ):
                # set to pending
                self.reportStatus( i, "Pending" )
                active_ops.append( [i, operation] )

            else:
                # clear and skip
                self.reportStatus( i, "" )
                active_ops.append( [i, None] )

        # Use a slice to skip to "run from" step
        for i, operation in active_ops[idx:]:
            # skip inactive ops
            if( operation is None ):
                continue

            # Otherwise, run the operation
            self.reportStatus( i, "Preparing" )
            operation.prepare()

            self.reportStatus( i, "Running" )
            operation.execute()

            if( operation.status == "Complete" ):
                self.reportStatus( i, "Complete" )

            else:
                result = operation.report()
                self.reportStatus( i, "Failed" )                

        # Pipeline complete

    def reportStatus( self, idx, status ):
        if( self.status_reporter is not None ):
            self.status_reporter( idx, status )

        else:
            print( idx, status )

    #-- Operation Managment --------------------------------------------------#
    def insertOperation( self, operation, idx=None ):
        if( idx is None ):
            self.pipeline.append( operation )
        else:
            self.pipeline.insert( idx, operation )

    def removeOperation( self, operation=None, idx=None ):
        """
        Remove an operation either by index or by refference
        Args:
            operation (None, optional): Operation to remove
            row (None, optional): index of operaation  to remove
        """
        if( idx is None ):
            if( operation is None ):
                print("ERROR - need somethign to remove!")
                return
            idx = self.pipeline.index( operation )

        kill = self.pipeline.pop( idx )
        del( kill )

        return idx

    def index( self, operation ):
        return self.pipeline.index( operation )

    def nudge( self, operation, direction ):
        """
        Nudge the given operation left (up), or right (down) the order of the pipeline.
        Args:
            operation (AbstractOperation): Operation to move - should exist in the pipeline
            direction (bool): Direction, True==Up, False==Down
        
        Returns:
            int: New index of the given op, or it's current index if not moved
        """
        start_idx = self.index( operation )
        tgt_idx = start_idx + (-1 if direction else 1)
        if( tgt_idx < 0 ):
            # can't go further up
            return start_idx

        if( tgt_idx >= self.__len__() ):
            # Can't go further down
            return start_idx

        tmp = self.pipeline.pop( start_idx )
        self.pipeline.insert( tgt_idx, tmp )

        return tgt_idx

    #-- Serialization --------------------------------------------------------#
    def isChanged( self ):
        # have we changed from last save?
        for operation in self.pipeline:
            if( operation.is_changed ):
                return True

        return False

    def justSaved( self ):
        # Reset the 'dirty' flag on the operations as we have just saved.
        for operation in self.pipeline:
            operation.is_changed = False

    def toJson( self ):
        pd = {
            "NAME" : self.pipe_name,
            "ORDER":[],
            "OPERATIONS":{},
        }
        for operation in self.pipeline:
            uid = str( uuid.uuid4() )
            pd["ORDER"].append( uid )
            pd["OPERATIONS"][uid] = operation.makeOpDict()

        return json.dumps( pd, indent=4, sort_keys=False )

    def fromJsonDict( self, d ):
        self.pipeline.clear()
        for key in d["ORDER"]:
            op_dat = d[ "OPERATIONS" ][ key ]
            operation = OpFactory[ op_dat[ "OPERATION" ] ]()
            operation.fromOpDict( op_dat )
            self.pipeline.append( operation )

        self.pipe_name = d.get( "NAME", "None" )

    def saveFile( self, file_fq ):
        with open( file_fq, "w" ) as fh:
            fh.write( self.toJson() )

    def loadFile( self, file_fq ):
        self.loaded_from = file_fq

        # open the JSON
        json_dict = {}
        with open( file_fq, "r" ) as fh:
            json_dict = json.load( fh )

        # Determine pipeline name
        name = json_dict.get( "NAME", None )
        if( name is None ):
            # take from filename
            file_name = os.path.basename( file_fq )
            name, _ = file_name.rsplit( ".", 1 )
            json_dict["NAME"] = name

        # load
        self.fromJsonDict( json_dict )

    # Some suger
    def __len__( self ):
        return len( self.pipeline )


# Test some of these functions
if( __name__ == "__main__" ):
    # Trait Casting
    traits = [
        TraitFloat( "float", 1.0, 0.01, 10.0, 1.02, "" ),
        TraitInt( "int", 1, 1, 100, 42, "" ),
        TraitBool( "binary", True, None, None, False, "" ),
        TraitStr( "string", "", None, None, "A:B, C:D, E:F", "" ),
    ]

    for t in traits:
        stringed = t.toString()
        unstringed = t.fromString( stringed )
        print( "Trait:{} Str:'{}' Cast:'{}' as '{}'".format( t.name, stringed, unstringed, type( unstringed ) ) )

    # Serializing Operation Params
    act = OpBake()
    d = act.paramsToJDict()
    print( d )
    d["scale"]="1.2"
    act.paramsFromJDict( d )
    print( type(act.doBake), act.doBake, type(act.scale), act.scale )

    # making a pipeline file
    pipeline = [ OpBake(), OpBake(), OpRender() ]
    pipeline[0].setTrait( "mapping", "First"  )
    pipeline[1].setTrait( "mapping", "Second" )
    pipeline[1].setTrait( "scale", 69 )

    plf = {
        "ORDER":[],
        "OPERATIONS":{},
    }
    for op in pipeline:
        uid = str( uuid.uuid4() )
        plf["ORDER"].append( uid )
        plf["OPERATIONS"][uid] = op.makeOpDict()

    print( plf )

    # exporting a pipline
    with open( "testPipeline.jpf", "w" ) as fh:
        fh.write( json.dumps( plf, indent=4, sort_keys=False ) )

    # read it back
    test = {}
    with open( "testPipeline.jpf", "r" ) as fh:
        test = json.load( fh )

    print( test )

    pipe = Pipeline()
    pipe.fromJsonDict( test )
    print( pipe.pipeline )

    print( pipe.toJson() )