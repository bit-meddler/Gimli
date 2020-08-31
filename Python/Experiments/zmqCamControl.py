import argparse
import cmd
import textwrap
import random
import zmq


# Workaround not being in PATH
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

from Comms import piCam
from Comms import piComunicate
from Comms import SysManager

PORT_COMAND = 5555
PORT_STATE = 5556
TOPIC_STATE = "STATE"

CLIENT_TIMEOUT = 150
SERVER_TIMEOUT =  20


class CamControl( cmd.Cmd ):
    _short_set_cmds = ( x for x in piCam.CAM_SET_PARAMS if not x.startswith("maskzone") )

    def changedCam( self ):
        self.target_list_bytes = [ bytes( x, "utf-8" ) for x in self.target_list ]
        self.prompt = "Controling {}> ".format( ",".join( self.target_list ) )
        
    def __init__( self, local_ip=None ):
        super( CamControl, self ).__init__()
        self.local_ip = local_ip
        self.target_list = ["0"]
        self.changedCam()

        # for validation and traits
        self.camera = piCam.PiCamera( "" )
        
        # selector for imperatives
        self._HANDLER = {
            "exe": self.do_exe,
            "get": self.do_get,
            "set": self.do_set,
        }

        # Setup Communication Socket
        self._zctx = zmq.Context()
        self.comand = self._zctx.socket( zmq.REQ )
        self.comand.connect( "tcp://localhost:{}".format( PORT_COMAND ) )

        self.state_recv = self._zctx.socket( zmq.SUB )
        self.state_recv.subscribe( TOPIC_STATE )
        self.state_recv.connect( "tcp://localhost:{}".format( PORT_STATE ) )

        self.poller = zmq.Poller()
        self.poller.register( self.state_recv, zmq.POLLIN )
        
        # begin
        self.intro = "Camera Control Console, operating from '{:0>3}'".format( self.local_ip )

    def do_EOF( self, args ):
        return True

    def emptyline( self ):
        self._attempt_to_read()

    def _genericCompleter( self, suggests, text ):
        if( text ):
            return [ x for x in suggests if x.startswith( text ) ]
        else:
            return suggests

    def _emit( self, verb, noun, value=None ):
        
        # compose command
        self.comand.send( bytes( verb, "utf-8" ), zmq.SNDMORE )
        self.comand.send( bytes( noun, "utf-8" ), zmq.SNDMORE )
        if( value is not None ):
            self.comand.send( bytes( str( value ), "utf-8" ), zmq.SNDMORE )
        for target in self.target_list:
            self.comand.send( bytes( target, "utf-8" ), zmq.SNDMORE )
        self.comand.send( b"K?" )

        # get ack
        resp = self.comand.recv()
        print( "got '{}'".format( resp ) )
        
    def _genericOneCommand( self, args, commands, verb ):
        args = args.lower()
        if( " " in args ):
            args, _ = args.split( " ", 1 )
        if( args in commands ):
            self._emit( verb, args )
        else:
            print( "Unknown request '{}'".format( args ) )

    def do_set( self, args ):
        param, val = args.lower().split( " ", 1 )
        if( param in piCam.CAM_SET_PARAMS ):
            trait = self.camera.hw_settings[ param ]
            cast = trait.dtype( val )
            if( trait.isValid( cast ) ):
                print( "SENDING set '{}' '{}'".format( param, val ) )
                self._emit( "set", param, value=val )
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

        #self.com_mgr.q_cmds.put( "{}:{}".format( self.camera_ip, output ) )

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
        self._emit( "close", "close" )
        self.comand.close()
        self._zctx.term()
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

    def do_cams( self, args ):
        # set target list
        args = args.strip()
        cams = args.split(",")
        self.target_list = list( map( lambda x: x.strip(), cams ) )
        self.changedCam()

    # reading?
    def postcmd( self, stop, line ):
        self._attempt_to_read()

    def postloop (self ):
        self._attempt_to_read()

    def _attempt_to_read( self ):
        coms = dict( self.poller.poll( CLIENT_TIMEOUT ) )
        if( coms.get( self.state_recv ) == zmq.POLLIN ):
            data = self.state_recv.recv_multipart()
            print( data )


if( __name__ == "__main__" ):
    ips =  piComunicate.listIPs()
    local_ip = ips[0] if len(ips)>0 else "192.168.0.20"

    DEFAULT_TARGET = "192.168.0.34"

    parser = argparse.ArgumentParser()
    parser.add_argument( "-l", action="store", dest="local_ip", default=local_ip, help="Host IP (on same subnet as camera" )

    args = parser.parse_args()

    controler = CamControl( args.local_ip )
    controler.cmdloop()












