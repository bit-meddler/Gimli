import time
import zmq
import sys

if( len( sys.argv ) > 1 ):
    cam_id = sys.argv[ 1 ] 
else:
    cam_id = "1"

cam_id_bytes = bytes( cam_id, "utf-8" )

PORT_COMAND = 5555
PORT_STATE = 5556
TOPIC_STATE = "STATE"

CLIENT_TIMEOUT = 150
SERVER_TIMEOUT =  20

zctx = zmq.Context()

comand = zctx.socket( zmq.REQ )
comand.connect( "tcp://localhost:{}".format( PORT_COMAND ) )

state_recv = zctx.socket( zmq.SUB )
state_recv.subscribe( TOPIC_STATE )
state_recv.connect( "tcp://localhost:{}".format( PORT_STATE ) )

poller = zmq.Poller()
poller.register( state_recv, zmq.POLLIN )

time.sleep( 3 )
for i in range(23):
    print( "Req {}".format( i ) )

    req = "this is a message {}".format( "X" * i )

    comand.send( bytes( req, "utf-8" ), zmq.SNDMORE )
    comand.send( bytes( cam_id, "utf-8" ) )

    resp = comand.recv()
    print( "got '{}'".format( resp ) )

    coms = dict( poller.poll( CLIENT_TIMEOUT ) )
    if( coms.get( state_recv ) == zmq.POLLIN ):
        topic, _, cam, data = state_recv.recv_multipart()
        if( cam == cam_id_bytes ):
            print( data )
        
    time.sleep( 1 )
    
state_recv.close()
comand.close()
zctx.term()

