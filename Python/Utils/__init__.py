""" Generic Utils undeserving of separate modules """

try: # Weird issue on my linux VM not finding SimpleQueue, yes it's 3
    from queue import SimpleQueue
except ImportError:
    from queue import Queue as SimpleQueue

import socket


class SelectableQueue( SimpleQueue ):
    """ A (Threadsafe) Queue that can be polled in a "select" statement, such that queued items can be 'got' without
        spinning.
        Nastiest hack I've ever done.  (To Date)
    """

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

    def fileno( self ):
        """
        Select asks for the filedevice to poll it
        Returns:
            fileno: (int) filehandle of the input socket
        """
        return self._in.fileno()

    def put( self, item ):
        """
        Overload the Queue put function to emit a packet as well
        Args:
            item: (any) Queued Item
        """
        super( SelectableQueue, self ).put( item ) # Might block for a moment
        self._out.send( b"!" )

    def get( self ):
        """
        Overload the Queue get function to remove a byte from the socket
        Returns:
            item: (any) Queued Item
        """
        # only read one byte, so if 2 queue items exist, there will still be readables on the socket
        self._in.recv( 1 )
        return super( SelectableQueue, self ).get()

    def cleanClose( self ):
        """
        This Queue has responsibilities to the sockets it created.  Need to close these cleanly.
        Returns:

        """
        self._out.close()
        self._in.close()

    def __del__( self ):
        self.cleanClose()


