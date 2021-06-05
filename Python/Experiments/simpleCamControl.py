# 
# Copyright (C) 2016~2021 The Gimli Project
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

import argparse
import cmd
import textwrap
import random


# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) )
CODE_PATH = os.path.join( _git_root_, "Gimli", "Python" )
sys.path.append( CODE_PATH )

from Comms import piCam
from Comms import piComunicate
from Comms import SysManager

class CamControl( cmd.Cmd ):
    _short_set_cmds = ( x for x in piCam.CAM_SET_PARAMS if not x.startswith("maskzone") )

    def __init__( self, camera_ip, local_ip=None ):
        super( CamControl, self ).__init__()
        self.camera_ip = camera_ip
        _, _, _, cam_no = camera_ip.split( "." )
        self.prompt = "Camera:{: >3}> ".format( cam_no )
        self.camera = piCam.PiCamera( camera_ip )
        self.manager = SysManager()

        # selector for imperatives
        self._HANDLER = {
            "exe": self.do_exe,
            "get": self.do_get,
            "set": self.do_set,
        }

        # Setup Communication Socket
        self.local_ip = "127.0.0.1" if local_ip is None else local_ip
        self.com_mgr = piComunicate.SimpleComms( self.manager, self.local_ip )

        # testing packet assembly
        self.det_mgr = piComunicate.AssembleDetFrame( self.com_mgr.q_dets, self.manager )

        # begin
        self.com_mgr.start()
        self.det_mgr.start()
        self.intro = "Camera Control Console, operating camera '{}' from '{:0>3}'".format( self.camera_ip, self.local_ip )

    def do_EOF( self, args ):
        return True

    def emptyline( self ):
        self._attempt_to_read()

    def _genericCompleter( self, suggests, text ):
        if( text ):
            return [ x for x in suggests if x.startswith( text ) ]
        else:
            return suggests

    def _genericOneCommand( self, args, commands, verb ):
        args = args.lower()
        if( " " in args ):
            args, _ = args.split( " ", 1 )
        if( args in commands ):
            self.com_mgr.q_cmds.put( "{}:{} {}".format( self.camera_ip, verb, args ) )
        else:
            print( "Unknown request '{}'".format( args ) )

    def do_set( self, args ):
        param, val = args.lower().split( " ", 1 )
        if( param in piCam.CAM_SET_PARAMS ):
            trait = self.camera.hw_settings[ param ]
            cast = trait.dtype( val )
            if( trait.isValid( cast ) ):
                print( "SENDING set '{}' '{}'".format( param, val ) )
                self.com_mgr.q_cmds.put( "{}:set {} {}".format( self.camera_ip, param, val ) )
                trait.value = cast
                self.camera.touched.add( param )
            else:
                print("Invalid value '{}'. this trait can be between {} and {} and is in {}".format(
                        cast, trait.min, trait.max, trait.units )
                )
        else:
            print( "Unknown request '{}'".format( args ) )

    def complete_set( self, text, line, start_index, end_index ):
            return self._genericCompleter( piCam.CAM_SET_PARAMS, text )

    def help_set( self ):
        print("Set a Camera Paramiter eg: 'set strobe 15'. param name is all lower case")
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( self._short_set_cmds ) ), width=80) )
        print("There is a special case for Mask regions. Which follow this format 'maskzone[01-16][x,y,n,m]'")
        print("eg: 'set maskzone01x 20'")
        print("You need to set all four corners for a mask zone to be active.  Maybe use the 'bulk' syntax.")

    def do_bulk( self, args ):
        """
        Clean and validate a builk command, could execute peicemeal, or send a Bulk to the com_mgr
        :param args: ';' separated commands
        :return:
        """
        commands = args.lower().split(";")
        output = "bulk "
        for cmd_string in commands:
            cmd_string = cmd_string.strip()

            if( not cmd_string ):
                continue

            if( " " in cmd_string ):
                # clean the bulk command
                imperative, data = cmd_string.split( " ", 1 )

                if( imperative == "exe" ):
                    if( data in piCam.CAM_EXE_PARAMS ):
                        output += "{} {};".format( imperative, data )
                        continue

                if( imperative == "get" ):
                    if (data in piCam.CAM_REQ_PARAMS):
                        output += "{} {};".format( imperative, data )
                        continue

                if( imperative == "set" ):
                    param, val = data.lower().split( " ", 1 )
                    if( param in piCam.CAM_SET_PARAMS ):
                        if( self.camera.validateSet( param, val ) ):
                            output += "{} {} {};".format( imperative, param, val )
                else:
                    print("Unrecognised imperative '{}'".format( imperative ))
            else:
                print("Unknown '{}'".format( cmd_string ))

        self.com_mgr.q_cmds.put( "{}:{}".format( self.camera_ip, output ) )

    def help_bulk( self ):
        print( "bulk expects a ';' separated list of commands to execute as a batch. commands should be space separated as normal" )
        print( "\teg: 'bulk set strobe 15;set fps 60; set shutter 12 ; set threshold 136;'" )
        print( "a 'get regshi' will automatically be executed after a bulk operation" )

    def do_exe( self, args ):
        self._genericOneCommand( args, piCam.CAM_EXE_PARAMS, "exe" )

    def complete_exe( self, text, line, start_index, end_index ):
        return self._genericCompleter( piCam.CAM_EXE_PARAMS, text )

    def help_exe( self ):
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( piCam.CAM_EXE_PARAMS ) ), width=80) )

    def do_get( self, args ):
        self._genericOneCommand( args, piCam.CAM_REQ_PARAMS, "get" )

    def complete_get( self, text, line, start_index, end_index ):
        return self._genericCompleter( piCam.CAM_REQ_PARAMS, text )

    def help_get( self ):
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( piCam.CAM_REQ_PARAMS ) ), width=80) )

    # presets
    def do_save( self, args ):
        print( "Saving Settings" )

    def do_load( self, args ):
        print( "Loading Settings" )

    # Shortcuts
    def do_exit( self,  args ):
        # Clean shutdown
        self.com_mgr.q_cmds.put( "{}:close close".format( self.camera_ip ) )
        self.com_mgr.join()
        exit(1)

    def do_hello( self, args ):
        self.do_get( "hello" )

    def do_start( self, args ):
        self.do_exe( "start" )

    def do_stop( self, args ):
        self.do_exe( "stop" )

    def do_spam( self, args ):
        # Spam the camera with random commands
        num = int( args.strip() )
        for i in range( num ):
            # pick a random trait
            param = random.choice( piCam.CAM_SET_PARAMS )
            trait = self.camera.hw_settings[ param ]
            val = random.randrange( trait.min, trait.max )
            self.do_set( "{} {}".format( param, val ) )
            if( (i%6) == 0 ): # occasionally do a reg get
                self.do_get( "regslo" )

    # reading?
    def postcmd( self, stop, line ):
        self._attempt_to_read()

    def postloop (self ):
        self._attempt_to_read()

    def _attempt_to_read( self ):
        if( not self.det_mgr.q_out.empty() ):
            data = self.det_mgr.q_out.get()
            print( data )

        while( not self.com_mgr.q_misc.empty() ):
            data = self.com_mgr.q_misc.get( block=False, timeout=0.001 )
            src_ip, msg = data
            if( src_ip == self.camera_ip ):
                print( msg )


if( __name__ == "__main__" ):
    ips =  piComunicate.listIPs()
    local_ip = ips[0] if len(ips)>0 else "192.168.0.20"

    DEFAULT_TARGET = "192.168.0.34"

    parser = argparse.ArgumentParser()
    parser.add_argument( "-c", action="store", dest="camera_ip", default=DEFAULT_TARGET, help="Camera to Control" )
    parser.add_argument( "-l", action="store", dest="local_ip", default=local_ip, help="Host IP (on same subnet as camera" )

    args = parser.parse_args()

    controler = CamControl( args.camera_ip, args.local_ip )
    controler.cmdloop()












