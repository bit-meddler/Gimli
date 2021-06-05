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

""" simArbiter.py - "We sense a soul in search of answers"

    This Tool will simulate the desired functionality of the arbiter.  Like a simCam
    it will play back the exemplor data files to simulate a working MoCap system,
    and it will simulate cameras responding correctly to C&C messages.

    For now it will emulate a basic Mocap system of 10 cameras and 1 sync unit.
"""

# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
print( _git_root_ )
CODE_PATH = os.path.join( _git_root_, "Gimli", "Python" )
DATA_PATH = os.path.join( _git_root_, "Gimli", "ExampleData" )
sys.path.append( CODE_PATH )

# Logging
import logging
logging.basicConfig()
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

#detailed_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s][%(name)-16s] %(message)s {%(filename)s@%(lineno)s}", "%y%m%d %H:%M:%S" )
#terse_log = logging.Formatter( "%(asctime)s.%(msecs)04d [%(levelname)-8s] %(message)s", "%y%m%d %H:%M:%S" )

import argparse
import numpy as np
np.set_printoptions( precision=3, suppress=True )
import pickle
from queue import SimpleQueue
import struct
import threading
import time
import zmq

import Comms
from Core.math3D import FLOAT_T, ID_T

class Metronome( threading.Thread ):
    """ This looks familiar! """

    def __init__( self, the_flag, delay ):
        super( Metronome, self ).__init__()
        self._flag = the_flag
        self._delay = delay
        self.running = threading.Event()
        self.running.set()

    def run( self ):
        while self.running.isSet():
            time.sleep( self._delay )
            self._flag.set()

    def stop( self ):
        self.running.clear()


class Arbiter( object ):

    def __init__( self, replay=None, rate=None, step=None ):
        # inits
        self.replay = replay or "calibration"
        self.rate = rate or 25
        self.step = step or 3

        # System State
        self.system = Comms.SysManager()

        # No actual system communications, hold the det/com mans queues yourself
        self.q_misc = SimpleQueue()

        # Client Communications (ZMQ)
        self.acks = 0
        self._zctx = zmq.Context()

        self.cnc_in = self._zctx.socket( zmq.ROUTER )
        self.cnc_in.bind( "tcp://*:{}".format( Comms.ABT_PORT_SYSCNC ) )

        self.state_pub = self._zctx.socket( zmq.PUB )
        self.state_pub.bind( "tcp://*:{}".format( Comms.ABT_PORT_SYSSTATE ) )

        self.data_pub = self._zctx.socket( zmq.PUB )
        self.data_pub.bind( "tcp://*:{}".format( Comms.ABT_PORT_DATA ) )

        self.poller = zmq.Poller()
        self.poller.register( self.cnc_in, zmq.POLLIN )

        # Setup a bogus system
        _BOGO_SYS_ = {
            "Sync" : "192.168.10.100",
            "Cam1" : "192.168.10.101",
            "Cam2" : "192.168.10.102",
            "Cam3" : "192.168.10.103",
            "Cam4" : "192.168.10.104",
            "Cam5" : "192.168.10.105",
            "Cam6" : "192.168.10.106",
            "Cam7" : "192.168.10.107",
            "Cam8" : "192.168.10.108",
            "Cam9" : "192.168.10.109",
            "CamA" : "192.168.10.110",
        }
        cam_list = [ c for c in _BOGO_SYS_.keys() if c.startswith("C") ]
        for cam in cam_list:
            self.system.manualAdd( cam )
        self.system.remarshelCameras()


        # setup replay
        self.ticks = 0
        self.cur_frame = 0
        self.frames = []
        self.strides = []
        self.num_frames = 0
        self.sent_frames = 0
        self._setupReplay()

        # a clock thread to tick the data replay
        self.tick = threading.Event()
        self.tick.clear()
        self.timer = Metronome( self.tick, 1.0 / self.rate )

        # Enable Running
        self.running = threading.Event()
        self.running.set()

    def _setupReplay( self ):
        # load up the replay files
        frames=[]
        with open( os.path.join( DATA_PATH, self.replay + ".pik" ), "rb" ) as fh:
            frames = pickle.load( fh )

        # repack each frame
        self.num_frames = len( frames )
        empties = 0
        for (stride, frame, ids) in frames:
            # I'll have that as NumPy, thanks
            np_frames = np.array( frame, dtype=FLOAT_T )
            np_stride = np.array( stride, dtype=ID_T )
            if( len(np_frames) == 0 ):
                empties += 1
            self.frames.append( np_frames )
            self.strides.append( np_stride )
            
        print( "Prepared {} frames, containing {} Empty frames".format( self.num_frames, empties ) )

    def handleCNC( self, dgm ):
        # currently just cameras
        verb = dgm[ 2 ]
        noun = dgm[ 3 ]

        # setting like msg?
        setting = False
        tgt_idx = 4
        if( verb == b"set" or verb == b"try" ):
            setting = True
            tgt_idx = 5

        # Multi-target flood message
        tgt_out = len( dgm ) - 1
        tgts = dgm[ tgt_idx: tgt_out ]
        for tgt in tgts:
            ip = self.system.getCamIP( int( tgt.decode("utf-8") ) )
            if( ip is None ):
                print("Unknown Cam id")
                continue
            msg = ""
            if( setting ):
                msg = "{}:set {} {}".format( ip, noun, dgm[ 4 ] )
                # todo: set on the bogo sys
            else:
                msg = "{}:{} {}".format( ip, verb, noun )
            log.info( "hCNC> " + msg )
        # Simulate the result of this??

    def execute( self ):
        # Start Services
        self.timer.start()

        # run
        while( self.running.isSet() ):
            try:
                # look for commands from clients
                coms = dict( self.poller.poll( 0 ) )
                if( coms.get( self.cnc_in ) == zmq.POLLIN ):
                    dgm = self.cnc_in.recv_multipart()
                    # Should we could test the validity of the request?
                    # Acknowledge receipt, and give a "Message Number"
                    self.acks += 1
                    ack = struct.pack( "I", self.acks )
                    self.cnc_in.send_multipart( [ dgm[ 0 ], b'', ack ] )
                    self.handleCNC( dgm )

                    # Emit a pub saying msg 'ack' has been done.
                    self.data_pub.send_multipart( [ Comms.ABT_TOPIC_STATE_B, b"", b"DID", ack ] )

                # Send some data
                if( self.tick.isSet() ):
                    data = [ self.cur_frame, self.strides[self.cur_frame], self.frames[self.cur_frame] ]
                    self.publishDets( data ) # Make this a callback in the det man?
                    self.ticks += 1
                    self.cur_frame += (self.step + 1)
                    if( self.cur_frame > self.num_frames ):
                        self.cur_frame = 0
                    self.tick.clear()

                # Look for misc & Orphans from cameraComms
                while( not self.q_misc.empty() ):
                    _, data = self.q_misc.get( block=False, timeout=0.001 )
                    print( data )
                    dtype, timecode, msg = data
                    self.data_pub.send_multipart( [ Comms.ABT_TOPIC_STATE_B, b"", msg ] )

            except KeyboardInterrupt:
                print( "Closing due to Interupt" )
                self.running.clear()

        # while running
        self.cleanClose()
        print( "Sent {} frames".format( self.sent_frames ) )

    def publishDets( self, data ):
        _, strides, dets = data
        self.data_pub.send_multipart( [ Comms.ABT_TOPIC_ROIDS_B, b"",
                                        bytes( str( self.ticks ), "utf-8" ),
                                        strides.tobytes(),
                                        dets.tobytes() ] )
        #log.info( "sent dets" )
        self.sent_frames += 1

    def cleanClose( self ):
        print( self.system )
        self.timer.stop()
        # Close sockets for graceful shutdown
        self.cnc_in.close()
        self.state_pub.close()
        self.data_pub.close()
        self._zctx.term()


if( __name__ == "__main__" ):
    parser = argparse.ArgumentParser()
    parser.add_argument( "-s", "--simulate", action="store", dest="replay", default="calibration",
                         help="Replay data file. Can be 'calibration' or 'rom'. Default: calibration" )
    parser.add_argument( "-r", "--rate", action="store", dest="rate", default=25,
                         help="Rate (fps). Default: 25", type=int )
    parser.add_argument( "-k", "--skip", action="store", dest="step", default=3,
                         help="Frames to skip. if data is 100fps and rate is 25 skip=3 to get realtime. Default:3",
                         type=int )

    args = parser.parse_args()

    app = Arbiter( replay=args.replay, rate=args.rate, step=args.step )
    app.execute()