
import time
import zmq

zctx = zmq.Context()
sock = zctx.socket( zmq.REP )
sock.bind( "tcp://*:5555" )

count = 0
try:
    while True:
        message = sock.recv()
        print( "Received: '{}'".format( message ) )
        time.sleep( 1 )
        sock.send_string( "recv: {}".format( count ) )
        count += 1
except:
    sock.close()
    zctx.term()
