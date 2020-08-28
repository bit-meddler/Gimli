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
cam_id = b"1"
try:
    while True:
        coms = dict( poller.poll( SERVER_TIMEOUT ) )

        if( coms.get( ins ) == zmq.POLLIN ):
            dgm = ins.recv_multipart()
            ins.send_multipart( [dgm[0], b'', b'K'] )
            verb = dgm[ 2 ]
            noun = dgm[ 3 ]
            tgt_idx = 5 if( verb == b"set" ) else 4
            tgt_out = len( dgm ) - 1

            tgts = dgm[ tgt_idx : tgt_out ]

            for tgt in tgts:
                print( "sending {} {} {} to {}".format(
                    verb, noun, dgm[4] if verb == b"set" else "", tgt )
                )
            count += 1
            send = True

        if( (count % 5) == 0 and send ):
            resp = "State update {}".format( count )
            state_pub.send_multipart( [TOPIC_STATE_B, b"", cam_id, bytes( resp, "utf-8")] )
            send = False
            
except:
    print( "Bailing" )
    state_pub.close()
    ins.close()
    zctx.term()
