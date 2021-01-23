""" Generic Utils undeserving of separate modules """

try: # Weird issue on my linux VM not finding SimpleQueue, yes it's 3
    from queue import SimpleQueue
except ImportError:
    from queue import Queue as SimpleQueue

import socket


class SelectableQueue( SimpleQueue ):
    """ Nastiest hack I've ever done.  (To Date) """

    PORT = 0 # Binding to port Zero will find a random, available, non-privaledged port

    def __init__( self ):
        super( SelectableQueue, self ).__init__()

        temp_in = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        temp_in.bind( ( "127.0.0.1", self.PORT ) )
        temp_in.listen( 1 ) # Only one client
        in_addr = temp_in.getsockname()

        self._out = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        self._out.connect( in_addr )

        self._in, out_addr = temp_in.accept()

        temp_in.close()

    def fileno( self ): # select asks for the fd
        return self._in.fileno()

    def put( self, item ):
        super( SelectableQueue, self ).put( item ) # Might block for a moment
        self._out.send( b"!" )

    def get( self ):
        self._in.recv( 1 ) # only read one byte, so if 2 queue items exist, there will be readables on the socket
        return super( SelectableQueue, self ).get()

    def cleanClose( self ):
        self._out.close()
        self._in.close()

    def __del__( self ):
        self.cleanClose()


