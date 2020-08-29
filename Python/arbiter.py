""" arbiter.py - "We sense a soul in search of answers"

    The Arbiter is the "core" loop. it will manage multiple ZMQ services:

    CameraCnC  : DB Multi Client access to camera settings
    SysState   : DB Camera List changes, Camea settings

    SysAnnounce: PS Flag the state has changed, Subs Req what they're interested in
    Centroids  : PS Stream of Centroids from the MoCap System
    Images     : PS Images from the MoCap Cameras
    Orphans    : PS Any Centroids arriving after their Packet Ships
    Timecode   : PS Just HH:MM:SS:FF:ss U1:U2:U3:U4:U5:U6:U7:U8 for anyone that's interested
    TakeCnC    : RR Transport control, a Client sets the Take name, starts recording etc
    Transport  : PS Current & upcoming Take Name, Rec Status, target folder & name

    And receive Data from the Cameras, and _do the right thing_ with it!

    Problem is I don't know where to start...
"""

# Workaround not being in PATH
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import numpy as np
np.set_printoptions( precision=3, suppress=True )

import threading
import zmq

import Comms
from Comms.piComunicate import AssembleDetFrame, SimpleComms


class Arbiter( object ):

    def __init__( self, local_ip=None ):
        # System State
        self.system = Comms.SysManager()

        # Setup System Communications
        self.local_ip = local_ip or "127.0.0.1"
        self.com_mgr = SimpleComms( self.system, self.local_ip )

        # Packet Handlers
        self.det_mgr = AssembleDetFrame( self.com_mgr.q_dets, self.system )
        #self.img_mgr = AssembleImages( self.com_mgr.q_imgs, self.system )

        # Client Comunications (ZMQ)
        self._zctx = zmq.Context()

        self.cnc_in = self._zctx.socket( zmq.ROUTER )
        self.cnc_in.bind( "tcp://*:{}".format( Comms.ABT_PORT_SYSCNC ) )

        self.state_pub = self._zctx.socket( zmq.PUB )
        self.state_pub.bind( "tcp://*:{}".format( Comms.ABT_PORT_SYSSTATE ) )

        self.data_pub = self._zctx.socket( zmq.PUB )
        self.data_pub.bind( "tcp://*:{}".format( Comms.ABT_PORT_DATA ) )

        self.poller = zmq.Poller()
        self.poller.register( self.cnc_in, zmq.POLLIN )

        # Enable Running
        self.running = threading.Event()
        self.running.set()

        # Load last system state?

    def handleCNC( self, dgm ):
        # currently just cameras
        verb = dgm[ 2 ]
        noun = dgm[ 3 ]

        tgt_idx = 5 if (verb == b"set") else 4
        tgt_out = len( dgm ) - 1
        tgts = dgm[ tgt_idx: tgt_out ]

        for tgt in tgts:
            ip = self.system.getCamIP( int( str( tgt ) ) )
            if( ip is None ):
                print("Unknown Cam id")
                continue
            if( verb == b"set" ):
                self.com_mgr.q_cmds.put( "{}:set {} {}".format( ip, noun, dgm[ 4 ] ) )
            else: #get exe
                self.com_mgr.q_cmds.put( "{}:{} {}".format( ip, verb, noun ) )

    def execute( self ):
        # Start Services
        self.det_mgr.start()
        self.com_mgr.start()

        # Say hello to the cameras
        #self.com_mgr.q_cmds.put("192.168.0.32:get hello")

        while( self.running.isSet() ):
            # look for commands from clients
            coms = dict( self.poller.poll( 0 ) )
            if (coms.get( self.cnc_in ) == zmq.POLLIN):
                dgm = self.cnc_in.recv_multipart()
                # Just ack it for now, maybe we could test the validity of the request?
                self.cnc_in.send_multipart( [ dgm[ 0 ], b'', b'K' ] )
                self.handleCNC( dgm )

            # Check for Dets or Images to send out
            # TODO: In the future, merge frames from different families of cameras
            if( not self.det_mgr.q_out.empty() ):
                data = self.det_mgr.q_out.get()
                self.publishDets( data ) # Make this a callback in the det man?

            # Look for misc & Orphans from cameraComms
            while( not self.com_mgr.q_misc.empty() ):
                _, data = self.com_mgr.q_misc.get( block=False, timeout=0.001 )
                print( data )
                dtype, timecode, msg = data
                self.data_pub.send_multipart( [ Comms.ABT_TOPIC_STATE_B, b"", msg ] )

    def publishDets( self, data ):
        time, strides, dets = data
        self.data_pub.send_multipart( [ Comms.ABT_TOPIC_ROIDS_B, b"",
                                        bytes( str( time ), "utf-8" ),
                                        strides.tobytes(),
                                        dets.tobytes() ] )

    def cleanClose( self ):
        print( self.system )
        # Close managers
        self.com_mgr.running.clear()
        self.det_mgr.running.clear()

        # Close sockets for graceful shutdown
        self.cnc_in.close()
        self.state_pub.close()
        self.data_pub.close()
        self._zctx.term()

if( __name__ == "__main__" ):
    app = Arbiter( "192.168.0.20" )
    app.execute()