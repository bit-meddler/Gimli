""" arbiter.py - "We sense a soul in search of answers"

    The Arbiter is the "core" loop. it will manage multiple ZMQ services:

    CameraCnC  : RR Multi Client access to camera settings
    SysState   : RR Camera List changes, Camea settings
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