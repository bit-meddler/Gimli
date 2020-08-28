import sys
import zmq

topics = ["egg", "bacon", "spam" ]

if( len( sys.argv ) > 1 ):
    interest = sys.argv[ 1 ] 
    if( interest not in topics ):
        interest = "egg"
else:
    interest = ""

zctx = zmq.Context()
sock = zctx.socket( zmq.SUB )

sock.connect( "tcp://localhost:5555" )


sock.subscribe( interest )

try:
    while True:
        print( sock.recv() )
except:
    sock.close()
    zctx.term()
