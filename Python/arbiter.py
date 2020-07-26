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
    Transport  : PS Current & upcoming Take Name, Rec Status

    And receive Data from the Cameras, and _do the right thing_ with it!

    Problem is I don't know where to start...
"""

# Workaround not being in PATH
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from Comms.piComunicate import SysManager, AssembleDetFrame, SimpleComms


class Arbiter( object ):

    def __init__( self, local_ip ):
        # System State
        self.manager = SysManager()

        # Setup Communications
        self.local_ip = "127.0.0.1" if local_ip is None else local_ip
        self.com_mgr = piComunicate.SimpleComms( self.local_ip )
        #self.q_misc = SimpleQueue()

        # Packet Handlers
        self.det_mgr = AssembleDetFrame( self.com_mgr.q_dets, self.manager )
        #self.img_mgr = AssembleImages( self.com_mgr.q_imgs, self.manager )

        # Running
        self.running = threading.Event()
        self.running.set()


    def execute( self ):
        # Start Services
        self.det_mgr.start()
        self.com_mgr.start()

        while( self.running.isSet() ):
            # look for commands from clients

            # Check for Dets to send out
            pass

if( __name__ == "__main__" ):
    app = Arbiter( "192.168.0.20" )
    app.execute()