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


class SimpleComms( threading.Thread ):

    def __init__( self, host_ip=None ):
        # Thread setup
        super( SimpleComms, self ).__init__()
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
        try:
            self.command_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1 )
        except AttributeError:# not on Windows :(
            pass
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
                # TODO: Can this be better?
                data, (src_ip, src_port) = sock.recvfrom( RECV_BUFF_SZ )
                self.handlePacket( src_ip, data )

        # running flag has been cleared
        self.command_socket.close()

    def handlePacket( self, src_ip, data ):
        dtype, time_stamp, num_dts, dgm_no, dgm_cnt, msg = piCam.decodePacket( data )

        if( dtype > piCam.PACKET_TYPES["imagedata"] ):
            # "misc" Data: Regs, Text, Version Info
            self.q_misc.put( (src_ip, (dtype, time_stamp, msg,)) )
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


class AssembleDetFrame( threading.Thread ):
    """
        This will assemble fragmented Centroid packets (Centroids from a Camera) and compose a "big Frame" of data and indexs
        this is a bit like an OpenGL VBO and it's Index buffer, eg data[idx1:idx2] is the the first cameras centroids
        data[0:idx1] is a reserved area for Metadata, such as Timecode values.

    """
    UNKNOWN_REMAINS = 100
    DEFAULT_CHECK_FREQ = 10 # 720 # 60fps * 12
    FAILURE_TO_COMMUNICATE = UNKNOWN_REMAINS * (DEFAULT_CHECK_FREQ-1)
    FRAC_8BIT = 1./256
    FRAC_4BIT = 1./16

    def __init__( self, q_dets, manager ):
        # Thread setup
        super( AssembleDetFrame, self ).__init__()
        self.daemon = True

        # Thread Control
        self.running = threading.Event()
        self.running.set()

        # IO queues
        self.q_dets = q_dets
        self.q_orph = SimpleQueue()
        self.q_out  = SimpleQueue()

        # Framing data
        self.current_time = 0

        # sysManager
        self.manager = manager
        self.last_hash = -1 #?

        # assembly
        self.frame_assemble = [] # assemble fragmented packets here
        self.packets_remain = np.array( [], dtype=np.int8  ) # count of num of packets remaining
        self.assembled_idxs = np.array( [], dtype=np.int32 ) # index for assemble that has been filled up to

        # camera health
        self.ship_sucess = np.array( [], dtype=np.int32 )
        self.bad_cameras = np.array( [], dtype=np.int32 )
        self.frames_sent = 0
        self.check_freqs = self.DEFAULT_CHECK_FREQ

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

        cam_id, new = self.manager.getCamId( src_ip, time_stamp )

        if( new ):
            # Make space for the new camera in the Assembly, and initialize
            self.frame_assemble.append( np.array([], dtype=np.uint8) )
            self.packets_remain = np.append( self.packets_remain, self.UNKNOWN_REMAINS )
            self.assembled_idxs = np.append( self.assembled_idxs, 0 )
            self.ship_sucess = np.append( self.ship_sucess, 0 )

        # Are we forced to Ship?
        if( time_stamp > self.current_time ):
            print( "Compelled Ship" )
            self.ship()
            self.current_time = time_stamp
        elif( time_stamp < self.current_time ):
            # this is an orphan!
            self.q_orph.put( (src_ip, packet) )
            return
        
        # First Packet from this camera in this frame?
        if( self.packets_remain[ cam_id ] == self.UNKNOWN_REMAINS ):
            self.packets_remain[ cam_id ] = dgm_cnt
            self.frame_assemble[ cam_id ] = np.zeros( (num_dts*8), dtype=np.uint8 )

        # add this packet's detections to the assembly buffer
        start_idx = self.assembled_idxs[ cam_id ]
        end_idx = start_idx + data_len
        self.frame_assemble[ cam_id ][ start_idx:end_idx ] = np.frombuffer( dets, dtype=np.uint8 )
        self.assembled_idxs[ cam_id ] = end_idx
        self.packets_remain[ cam_id ] -= 1

        # Test for opportunistic ship (all packets assembled)
        if( np.all( self.packets_remain < 1 ) ):
            print( "Opportunistic Ship" )
            self.ship()

    def ship( self ):
        # Pack
        out = np.array([], dtype=np.uint8) # fill with meta data??? timestamp, sysHash
        idxs = []
        for i in range( self.manager.num_cams ):
            idxs.append( len( out ) )
            out = np.append( out, self.frame_assemble[i][0:self.assembled_idxs[i]] ) # as many as we got
        idxs.append( len( out ) )

        # empty frame
        if( len( out ) == 0):
            self.clearBuffers()
            return

        idxs = np.array( idxs, dtype=np.int )
        idxs = np.right_shift( idxs, 3 ) # div 8

        raw = out.reshape( (idxs[ -1 ], 8) )

        # Decode
        out = np.zeros( (raw.shape[0],3), dtype=np.float32 )

        # ToDo: Can this be done better? Manual decode of int16 :(

        out[:,0]  = raw[:,1].astype( np.float32 ) * 256
        out[:,0] += raw[:,0].astype( np.float32 )

        out[:,1]  = raw[:,4].astype( np.float32 ) * 256
        out[:,1] += raw[:,3].astype( np.float32 )

        out[:,2]  = raw[:,6].astype( np.float32 )

        # Fractions
        out[:,0] += raw[:,2].astype( np.float32 ) * self.FRAC_8BIT
        out[:,1] += raw[:,5].astype( np.float32 ) * self.FRAC_8BIT

        # tricky offset Radius fractions
        tmp = np.right_shift( raw[:,7], 4 )
        out[:,2] += tmp.astype( np.float32 ) * self.FRAC_4BIT

        # Ship
        self.q_out.put( (idxs, out) )
        self.frames_sent += 1

        # do Health Check
        if( (self.frames_sent % self.check_freqs) == 0):
            # have any cameras stopped communicating?
            bad_cam_ids = np.argwhere( self.ship_sucess > self.FAILURE_TO_COMMUNICATE ).flatten()
            for cam in bad_cam_ids:
                self.manager.flagBadId( cam )
            self.bad_cameras = bad_cam_ids

            # ToDo: Can I rehabilitate cameras that are no-longer bad?

            # reset counter
            self.ship_sucess = np.full( (self.manager.num_cams,), 0 )

        self.ship_sucess += self.packets_remain
        # Done
        self.clearBuffers()

    def clearBuffers( self ):
        self.frame_assemble = [ np.array([], dtype=np.uint8) for _ in range( self.manager.num_cams ) ]
        self.packets_remain = np.full( (self.manager.num_cams,), self.UNKNOWN_REMAINS, dtype=np.int8 )
        self.packets_remain[ self.bad_cameras ] = 0 # don't let bad cameras stop you from shipping
        self.assembled_idxs = np.full( (self.manager.num_cams,), 0, dtype=np.int32 )

# class AssembleDetFrame


class SysManager( object ):
    """
    Class to manage system topology, hold camera table. manage camera_ids
    """
    def __init__( self ):
        self._reset()

    def _reset( self ):
        self.cam_dict = {}
        self.rev_dict = {}
        self.num_cams = 0
        self.sys_hash = 0
        self.old_hash = {}
        self.bad_cams = []
        self.last_dgm = {}

    def getCamId( self, cam_ip, timestamp ):
        """
        Get a camera's ID.  if it's a new camera, update the table and announce a state change.
        Also note the last contact time for the camera, could help with diagnostics.
        This gets run a lot!

        :param cam_ip: Camera ip
        :return: id, state_changed
        """
        state_changed = False
        try:
            cam_id = self.cam_dict[ cam_ip ]
        except KeyError:
            # New Camera Discovered, add to cam list
            cam_id = self.num_cams # 0 index :)
            self.num_cams += 1
            self.cam_dict[ cam_ip ] = cam_id
            self.rev_dict[ cam_id ] = cam_ip
            self._updateHash()
            state_changed = True

        self.last_dgm[ cam_id ] = timestamp
        return (cam_id, state_changed)

    def _updateHash( self ):
        self.sys_hash += 1
        self.old_hash[ self.sys_hash ] = self.getCamList()

    def flagBadId( self, cam_id ):
        if( not cam_id in self.bad_cams ):
            self.bad_cams.append( cam_id )
        # leave it to the UI?

    def load( self, camip_list ):
        # setup ids from the given list, fully resets state
        self._reset()
        self.cam_dict = { ip: n for n, ip in enumerate( camip_list ) }
        self.rev_dict = { val:key for key, val in self.cam_dict.items() }
        self.num_cams = len( self.cam_dict )

    def remarshelCameras( self ):
        """
        Sort the cameras to be ordered by ip.  This will invalidate and frame assembly going on and corrupt your
        calibration. use the supplied "rename map" to fix you calibration.
        :return: (dict) rename_map - lut of old to new camera IDs
        """
        #? Lock ?
        new_dict = { ip:n for n,ip in enumerate( sorted( self.cam_dict.keys() ) ) }
        rename_map = { val:new_dict[key] for key, val in self.cam_dict.items() }
        self.cam_dict.clear()
        self.cam_dict = new_dict
        self.rev_dict = { val:key for key, val in self.cam_dict.items() }
        self._updateHash()

        return rename_map

    def getCamList( self ):
        return ( c for c in sorted( self.cam_dict.items(), key=lambda x: x[1] ) )

