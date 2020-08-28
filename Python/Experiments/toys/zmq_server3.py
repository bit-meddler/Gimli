import zmq

PORT_COMAND = 5555
PORT_STATE = 5556
TOPIC_STATE = "STATE"
TOPIC_STATE_B = bytes( TOPIC_STATE, "utf-8" )

CLIENT_TIMEOUT = 150
SERVER_TIMEOUT =  20

zctx = zmq.Context()

ins = zctx.socket( zmq.ROUTER )
ins.bind( "tcp://*:{}".format( PORT_COMAND ) )

state_pub = zctx.socket( zmq.PUB )
state_pub.bind( "tcp://*:{}".format( PORT_STATE ) )

poller = zmq.Poller()
poller.register( ins, zmq.POLLIN )

count = 0
send = False
try:
    while True:
        coms = dict( poller.poll( SERVER_TIMEOUT ) )

        if( coms.get( ins ) == zmq.POLLIN ):
            client_id, _, msg, val = ins.recv_multipart()
            # Directly Construct ZMQ envelope
            ins.send_multipart( [client_id, b'', b'K'] )
            print( client_id, msg )
            count += 1
            send = True
            print( count )

        if( (count % 5) == 0 and send ):
            resp = "State update {}".format( count )
            state_pub.send_multipart( [TOPIC_STATE_B, b"", val, bytes( resp, "utf-8")] )
            send = False
            
except:
    print( "Bailing" )
    state_pub.close()
    ins.close()
    zctx.term()
