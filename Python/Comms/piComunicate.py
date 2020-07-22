""" Communication routines to send & receive to a piCCam"""
from queue import SimpleQueue, Empty
import select
import socket
import threading
import time

import numpy as np

from Comms import piCam

SOCKET_TIMEOUT = 10
RECV_BUFF_SZ   = 10240 # bigger than a Jumbo Frame

def listIPs():
    """
    Conveniance to list available IP addresses on the system, ignoring Local Link and 127.0.0.1
    :return: (list) List of detected real ip addresses
    """
    candidates = []
    for ip in socket.getaddrinfo( socket.gethostname(), None ):
        if( ip[ 0 ] == socket.AF_INET ):
            addr = ip[4][0]
            if( (not addr.startswith( "169.254.")) and (addr != "127.0.0.1") ):
                candidates.append( addr )
    return sorted( candidates )


class SimpleComs( threading.Thread ):

    def __init__( self, host_ip=None ):
        # Thread setup
        super( SimpleComs, self ).__init__()
        self.daemon = True

        # Queues to communicate in and out of the thread
        # cmds: commands into the communicator
        # dets: Centroid fragments, Light Hi priority, need to be packetized
        # imgs: Image Fragments, Heavy low priority, need to be assembled
        # misc: Other Camera Reports
        self.q_cmds = SimpleQueue()
        self.q_dets = SimpleQueue()
        self.q_imgs = SimpleQueue()
        self.q_misc = SimpleQueue()

        # Activity Flag
        self.running = threading.Event()
        self.running.set()

        # Socket Setup
        self.host_ip = "127.0.0.1" if host_ip is None else host_ip
        self.command_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.command_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        self.command_socket.bind( (self.host_ip, piCam.UDP_PORT_TX) )
        self.command_socket.settimeout( SOCKET_TIMEOUT )
        self._inputs = [ self.command_socket ]

        # Command Selector
        self._HANDLER = {
            "exe"   : self.doExe,
            "get"   : self.doGet,
            "set"   : self.doSet,
            "bulk"  : self.doBulk,
            "close" : self.close, # Maye not wise having a Kamakazi command...
        }

    def run( self ):
        # be nice to do this with ASIO...
        while( self.running.isSet() ):
            # look for commands
            if( not self.q_cmds.empty()):
                try:
                    cmd_string = self.q_cmds.get( False )
                    target, commands = cmd_string.split( ":", 1 )
                    imperative, data = commands.split( " ", 1 )
                    self._HANDLER[ imperative ]( target, data )

                except Empty as e:
                    # no commands
                    pass
                except KeyError:
                    # unrecognised command, ignore
                    pass

            # Read Data from socket
            readable, _, _ = select.select( self._inputs, [], [], 0 ) # 0 timeout = poll
            for sock in readable:
                # TODO: should write a 'chunk' reader
                data, (src_ip, src_port) = sock.recvfrom( RECV_BUFF_SZ )
                # for now, just a digest
                self.handlePacket( src_ip, data )

        # running flag has been cleared
        self.command_socket.close()

    def handlePacket( self, src_ip, data ):
        dtype, time_stamp, num_dts, dgm_no, dgm_cnt, msg = piCam.decodePacket( data )

        if( dtype > piCam.PACKET_TYPES["imagedata"] ):
            # "misc" Data
            self.q_misc.put( (src_ip, (msg,)) )
        elif( dtype == piCam.PACKET_TYPES["centroids"] ):
            # Centroid Fragment
            self.q_dets.put( (src_ip, (time_stamp, num_dts, dgm_no, dgm_cnt, msg)) )
        elif( dtype == piCam.PACKET_TYPES["imagedata"] ):
            self.q_imgs.put( (src_ip, (time_stamp, num_dts, dgm_no, dgm_cnt, msg)) )

        #print( time.time(), piCam.PACKET_TYPES_REV[ dtype ], num_dts, dgm_no, dgm_cnt, msg[:8] )

    def doExe( self, target, command ):
        """
        Execute a Start or Stop
        :param target: (string) IP Address of camera being controlled
        :param command: (string) The request
        :return: None
        """
        msg, _ = piCam.composeCommand( command, None )
        self.command_socket.sendto( msg, ( target, piCam.UDP_PORT_RX ) )
        return False

    def doGet( self, target, request ):
        """
        Request something, this might need to make a "ticket" to register that a given camera is expecting a response

        :param target: (string) IP Address of camera being controlled
        :param request: (string) The request
        :return: None
        """
        msg, _ = piCam.composeCommand( request, None )
        self.command_socket.sendto( msg, ( target, piCam.UDP_PORT_RX ) )
        return False

    def doSet( self, target, args ):
        """
        Set a Setting - assumes the value has been pre-validated.  The Camea state will be invalid, and we might need
        to get a refresh of the regs, in_regshi says which req to send

        :param target: (string) IP Address of camera being controlled
        :param args: (string) The Paramiter and value, space separated.
        :return: None
        """
        param, val = args.lower().split( " ", 1 )
        trait = piCam.CAMERA_CAPABILITIES[ param ]
        cast = trait.dtype( val )
        msg, in_regshi = piCam.composeCommand( param, cast )

        self.command_socket.sendto( msg, ( target, piCam.UDP_PORT_RX ) )
        return in_regshi


    def doBulk( self, target, tasks ):
        """ Do a bulk operation, assume the commands are pre-validated

        :param target: (string) IP Address of camera being controlled
        :param tasks: (string) A Bulk execution string
        :return: None
        """
        hiregs = False
        commands = tasks.split(";")

        for cmd_string in commands:
            if( not cmd_string ):
                continue
            imperative, data = cmd_string.split( " ", 1 )
            in_regshi = self._HANDLER[ imperative ]( target, data )
            hiregs |= in_regshi
        self.q_misc.put( (target, ("Refresh {}".format( "regshi" if hiregs else "regslo" ))) )

    def close( self, target, arg ):
        """
        The close command is '<anything>:close close'
        Set the Flag to end this process and do a graceful shutdown on the socket

        :return: None
        """
        if( arg == "close" ):
            self.command_socket.sendto( b"bye", (target, piCam.UDP_PORT_RX) )
            self.running.clear()

# class SimpleComms


class AssembleFrame( threading.Thread ):
    """
        This will assemble fragmented Centroid packets (Centroids from a Camera) and compose a "big Frame" of data and indexs
        this is a bit like an OpenGL VBO and it's Index buffer, eg data[idx1:idx+1] is the the first cameras centroids
        data[0:idx1] is a reserved area for Metadata, such as Timecode values.

    """
    UNKNOWN_REMAINS = -1
    DTYPE_CENTROID_PACKED = np.dtype( "u2, B, u2, B, B, B" )
    FRAC_8BIT = 1./256
    FRAC_4BIT = 1./16

    def __init__( self, q_dets ):
        # Thread setup
        super( AssembleFrame, self ).__init__()
        self.daemon = True

        # Thread Control
        self.running = threading.Event()
        self.running.set()

        # IO queues
        self.q_dets = q_dets
        self.q_out  = SimpleQueue()

        # Framing data
        self.current_time = [0,0,0,0]

        # Camera list
        self.known_cameras = []
        self.camera_table  = {}
        self.num_cameras   = 0

        # assembly
        self.frame_assemble = [] # assemble fragmented packets here
        self.packets_remain = [] # count of num of packets remaining
        self.assembled_idx  = [] # index for assemble that has been filled up to

    def run( self ):
        # Core Thread
        while( self.running.isSet() ):
            # look for packets
            if( not self.q_dets.empty()):
                try:
                    src_ip, packet = self.q_dets.get()
                    self.processPacket( src_ip, packet )

                except Empty as e:
                    # no commands
                    pass

    def processPacket( self, src_ip, packet ):
        time_stamp, num_dts, dgm_no, dgm_cnt, dets = packet
        data_len = len( dets )

        try:
            # When this will work 99.9999999998% of the time, is except faster than "if X in known" every. single. time.
            cam_id = self.camera_table[ src_ip ]
        except KeyError:
            # New Camera Discovered add to cam list
            cam_id = self.num_cameras # 0 index :)
            self.num_cameras += 1
            self.known_cameras.append( src_ip )
            self.camera_table[ src_ip ] = cam_id

            # Make space for the new camera in the Assembly, and initialize
            self.packets_remain.append( self.UNKNOWN_REMAINS )
            self.frame_assemble[ cam_id ] = []
            self.assembled_idx.append( 0 )

            # Should announce the change in state somehow..

        # Are we forced to Ship?
        if( time_stamp[3] != self.current_time[3] ):
            self.ship()
            self.current_time = time_stamp

        if( self.packets_remain[ cam_id ] == self.UNKNOWN_REMAINS ):
            # first packet from this cam has come through
            self.packets_remain[ cam_id ] = dgm_cnt

            # make space for the centroids
            self.frame_assemble[ cam_id ] = np.zeros( (num_dts*8), dtype=np.uint8 )

        # add this packet's detections to the assembly buffer
        start_idx = self.assembled_idx[ cam_id ]
        end_idx = data_len
        self.frame_assemble[ cam_id ][ start_idx:end_idx ] = dets
        self.assembled_idx[ cam_id ] = end_idx
        self.packets_remain[ cam_id ] -= 1

        # Test for opportunistic ship (all packets assembled)
        if( np.all( self.packets_remain==0 ) ):
            # Ship it!
            self.ship()

    def ship( self ):
        # Pack
        out = [0,0,0,0,0,0] # fill with meta data??? tiemstamp
        idxs = []
        for i in range( self.num_cameras ):
            idxs.extend( [len(out)] )
            out.extend( self.frame_assemble[i][0:self.assembled_idx[i]] ) # as many as we got
        idxs.extend( [ len( out ) ] )

        # Decode
        X = np.array( out, dtype=self.DTYPE_CENTROID_PACKED )
        out = np.zeros( (X.shape[0],3), dtype=np.float32 )

        # Whole parts
        out[::0] = X[::0].astype( np.float32 )
        out[::1] = X[::2].astype( np.float32 )
        out[::2] = X[::4].astype( np.float32 )

        # Fractions
        out[ ::0 ] += X[ ::1 ].astype( np.float32 ) * self.FRAC_8BIT
        out[ ::1 ] += X[ ::3 ].astype( np.float32 ) * self.FRAC_8BIT

        # tricky offset Radius fractions
        tmp = np.right_shift( X[::5], 4 )
        out[ ::2 ] += tmp.astype( np.float32 ) * self.FRAC_4BIT

        # Ship
        self.q_out.put( idxs, out )
        self.clearBuffers()

    def clearBuffers( self ):
        self.frame_assemble = [ None for _ in range( self.num_cameras ) ]
        self.packets_remain = np.full( (self.num_cameras,), self.UNKNOWN_REMAINS )
        self.assembled_idx  = np.full( (self.num_cameras,), 0 )