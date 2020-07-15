import argparse
import cmd
import textwrap
import socket

# Workaround not being in PATH
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from Comms import piCam
from Comms import piComunicate

class CamControl( cmd.Cmd ):
    _short_set_cmds = ( x for x in piCam.KNOWN_SET_PARAMS if not x.startswith("maskzone") )

    def __init__( self, camera_ip, local_ip=None ):
        super( CamControl, self ).__init__()
        self.camera_ip = camera_ip
        _, _, _, cam_no = camera_ip.split( "." )
        self.prompt = "Camera:{: <3}> ".format( cam_no )
        self.camera = piCam.PiCamera( camera_ip )

        # selector for imperatives
        self._HANDLER = {
            "exe": self.do_exe,
            "get": self.do_get,
            "set": self.do_set,
        }

        # Setup Communication Socket
        self.local_ip = "127.0.0.1" if local_ip is None else local_ip
        timeout = 12
        self.command_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.command_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        self.command_socket.bind( (self.local_ip, piCam.UDP_PORT_RX) )
        self.command_socket.settimeout( timeout )
        self.intro = "Camera Control Console, operating camera '{}' from '{:0>3}'".format( self.camera_ip, self.local_ip )

    def test_send( self, cmd_string ):
        self.command_socket.sendto( cmd_string, (self.camera_ip, piCam.UDP_PORT_TX) )

    def do_EOF( self, args ):
        return True

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
            print( "{} '{}'".format( verb, args ) )
            msg, _ = piCam.composeCommand( args, None )
            print( "Payload '{}'".format( msg.hex() ) )
            self.test_send( msg )
        else:
            print( "Unknown request '{}'".format( args ) )

    def do_set( self, args ):
        param, vals = args.lower().split( " ", 1 )
        if( param in piCam.KNOWN_SET_PARAMS ):
            trait = self.camera.hw_settings[ param ]
            cast = trait.dtype( vals )
            if( trait.isValid( cast ) ):
                print( "Setting '{}' to '{}'".format( param, cast ) )
                msg, in_regs_hi = piCam.composeCommand( param, cast )
                print( "Payload '{}'".format( msg.hex() ) )
                self.test_send( msg )
                trait.value = cast
                self.camera.touched.add( param )
            else:
                print("Invalid value '{}'. this trait can be between {} and {} and is in {}".format(
                        cast, trait.min, trait.max, trait.units )
                )
        else:
            print( "Unknown request '{}'".format( args ) )

    def complete_set( self, text, line, start_index, end_index ):
            return _genericCompleter( piCam.KNOWN_SET_PARAMS, text )

    def help_set( self ):
        print("Set a Camera Paramiter eg: 'set strobe 15'. param name is all lower case")
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( self._short_set_cmds ) ), width=80) )
        print("There is a special case for Mask regions. Which follow this format 'maskzone[01-16][x,y,n,m]'")
        print("eg: 'set maskzone01x 20'")
        print("You need to set all four corners for a mask zone to be active.  Maybe use the 'bulk' syntax.")

    def do_bulk( self, args ):
        commands = args.split(";")
        for cmd_string in commands:
            cmd_string = cmd_string.strip()

            if( not cmd_string ):
                continue

            if( " " in cmd_string ):
                imperative, data = cmd_string.split( " ", 1 )

                if( imperative in self._HANDLER ):
                    self._HANDLER[ imperative ]( data )
                else:
                    print("Unrecognised imperative '{}'".format( imperative ))
            else:
                print("Unknown '{}'".format( cmd_string ))
        self.do_get( "regshi" )

    def help_bulk( self ):
        print( "bulk expects a ';' separated list of commands to execute as a batch. commands should be space separated as normal" )
        print( "\teg: 'bulk set strobe 15;set fps 60; set shutter 12 ; set threshold 136;'" )
        print( "a 'get regshi' will automatically be executed after a bulk operation" )

    def do_exe( self, args ):
        self._genericOneCommand( args, piCam.KNOWN_EXE_PARAMS, "exe" )

    def complete_exe( self, text, line, start_index, end_index ):
        return self. _genericCompleter( piCam.KNOWN_EXE_PARAMS, text )

    def help_exe( self ):
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( piCam.KNOWN_EXE_PARAMS ) ), width=80) )

    def do_get( self, args ):
        self._genericOneCommand( args, piCam.KNOWN_REQ_PARAMS, "req" )

    def complete_get( self, text, line, start_index, end_index ):
        return self._genericCompleter( piCam.KNOWN_REQ_PARAMS, text )

    def help_get( self ):
        print(textwrap.fill( "Available paramiters: '{}'".format( "', '".join( piCam.KNOWN_REQ_PARAMS ) ), width=80) )

    # presets
    def do_save( self, args ):
        print( "Saving Settings" )

    def do_load( self, args ):
        print( "Loading Settings" )

    # Shortcuts
    def do_exit( self,  args ):
        # Clean shutdown
        self.command_socket.close()
        exit(1)

    def do_hello( self, args ):
        self.do_get( "hello" )

    def do_start( self, args ):
        self.do_exe( "start" )

    def do_stop( self, args ):
        self.do_exe( "stop" )


if( __name__ == "__main__" ):
    ips =  piComunicate.listIPs()
    local_ip = ips[0] if len(ips)>0 else "192.168.0.20"

    DEFAULT_TARGET = "127.0.0.1"#"192.168.0.32"

    parser = argparse.ArgumentParser()
    parser.add_argument( "-c", action="store", dest="camera_ip", default=DEFAULT_TARGET, help="Camera to Control" )
    parser.add_argument( "-l", action="store", dest="local_ip", default=DEFAULT_TARGET, help="Host IP (on same subnet as camera" )

    args = parser.parse_args()

    controler = CamControl( args.camera_ip, args.local_ip )
    controler.cmdloop()












