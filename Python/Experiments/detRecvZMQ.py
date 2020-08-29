import numpy as np
np.set_printoptions( precision=3, suppress=True )

import zmq

ABT_PORT_DATA     = 5577
ABT_TOPIC_ROIDS   = "ROIDS" # Centroid Data
ABT_TOPIC_ROIDS_B = bytes( ABT_TOPIC_ROIDS, "utf-8" )


zctx = zmq.Context()

dets_recv = zctx.socket( zmq.SUB )
dets_recv.subscribe( ABT_TOPIC_ROIDS )
dets_recv.connect( "tcp://localhost:{}".format( ABT_PORT_DATA ) )

poller = zmq.Poller()
poller.register( dets_recv, zmq.POLLIN )

while True:
    coms = dict( poller.poll( 150 ) )
    if( coms.get( dets_recv ) == zmq.POLLIN ):
        topic, _, time, strides, data = dets_recv.recv_multipart()
        print( time,
               np.frombuffer( strides, dtype=np.int32 ),
               np.frombuffer( data, dtype=np.float32 ).reshape( -1, 3 ) )

