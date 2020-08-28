""" Simple Req Res"""

import zmq

zctx = zmq.Context()

sock = zctx.socket( zmq.REQ )
sock.connect( "tcp://localhost:5555" )

for i in range(10):
    print( "Job {}".format( i ) )

    req = "this is a message {}".format( "X" * i )

    sock.send( bytes( req, "utf-8" ) )
    #sock.send_string( req )

    resp = sock.recv()
    print( "got '{}'".format( resp ) )
    
sock.close()
zctx.term()
