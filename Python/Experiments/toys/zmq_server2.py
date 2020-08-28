import zmq
import time
import random

zctx = zmq.Context()
sock = zctx.socket( zmq.PUB )

sock.bind( "tcp://*:5555" )

topics = ["egg", "bacon", "spam" ]
count = 0
try:
    while True:
        topic = random.choice( topics )
        msg = "'{}' Blar blar {}".format( count, topic )
        dgm = "{} {}".format( topic, msg )
        
        print( dgm )
        
        sock.send( bytes( dgm, "utf-8" ) )
        time.sleep( 1 )
        count += 1
        
except:
    sock.close()
    zctx.term()
