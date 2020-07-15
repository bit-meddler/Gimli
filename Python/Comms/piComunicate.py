""" Communication routines to send & receive to a piCCam"""
import select
import socket
import threading

from Comms import piCam

SOCKET_TIMEOUT = 10
RECV_BUFF_SZ   = 10240 # bigger than a Jumbo Frame

def listIPs():
    """
    Conveniance to list available IP addresses on the system, ignoring Local Link and 127.0.0.1
    :return: (list) List of detected real ip addresses
    """
    candidates = []
    for ip in socket.getaddrinfo( socket.gethostname(), None ):
        if( ip[ 0 ] == socket.AF_INET ):
            addr = ip[4][0]
            if( (not addr.startswith( "169.254.")) and (addr != "127.0.0.1") ):
                candidates.append( addr )
    return sorted( candidates )


class SimpleComs( threading.Thread ):

    def __init__( self, host_ip ):
        # Thread setup
        super( SimpleComs, self ).__init__()
        self.daemon = True

        # Queues to comunicate in and out of the thread
        self.q_cmd = Queue.Queue()
        self.q_rep = Queue.Queue()

        # Activity Flag
        self.running = threading.Event()
        self.running.set()

        # Data Flag
        self.has_data = threading.Event()
        self.has_data.clear()

        # Socket Setup
        self.host_ip = "127.0.0.1" if host_ip is None else host_ip
        self.command_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.command_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        self.command_socket.bind( (self.host_ip, piCam.UDP_PORT_RX) )
        self.command_socket.settimeout( SOCKET_TIMEOUT )
        self._inputs = [ self.command_socket ]

        # Command Selector
        self._HANDLER = {
            "exe"   : self.do_exe,
            "get"   : self.do_get,
            "set"   : self.do_set,
            "bulk"  : self.do_bulk,
            "close" : self.close, # Maye not wise having a Kamakazi command...
        }

    def run( self ):
        # be nice to do this with ASIO...
        while( self.running.isSet() ):
            # look for commands
            if( not self.q_cmd.empty() ):
                try:
                    cmd_string = self.q_cmd.get( False )
                    target, commands = cmd_string.split( ":", 1 )
                    imperative, data = commands.split( " ", 1 )

                    self._HANDLER[ imperative ]( target, data )

                except Queue.Empty as e:
                    # no commands
                    pass
                except KeyError:
                    # unrecognised command, ignore
                    pass

            # Read Data from socket
            readable, _, _ = select.select( self._inputs, [], [] )
            for sock in readable:
                # TODO: should write a 'chunk' reader
                data, (src_ip, src_port) = sock.recvfrom( RECV_BUFF_SZ )
                # for now, just a digest
                self.q_rep.put( (src_ip, src_port, data) )
                self.has_data.set()

        # running flag has been cleared
        self.command_socket.close()


    def _send( self, target, msg ):
        """
        Send out the message to the Target
        :param target: (string) Target Camera IP
        :param msg: Command String
        :return: None
        """
        self.command_socket.sendto( msg, ( target, piCam.UDP_PORT_TX ) )

    def do_exe( self, target, command ):
        """
        Execute a Start or Stop
        :param target: (string) IP Address of camera being controlled
        :param command: (string) The request
        :return: None
        """
        self._send( target, piCam.composeCommand( command, None ) )

    def do_get( self, target, request ):
        """
        Request something, this might need to make a "ticket" to register that a given camera is expecting a response

        :param target: (string) IP Address of camera being controlled
        :param request: (string) The request
        :return: None
        """
        self._send( target, piCam.composeCommand( request, None ) )

    def do_set( self, target, args ):
        """
        Set a Setting - assumes the value has been pre-validated
        :param target: (string) IP Address of camera being controlled
        :param args: (string) The Paramiter and value, space separated.
        :return: None
        """
        param, vals = args.lower().split( " ", 1 )
        cast = piCam.CAMERA_CAPABILITIES[ param ]( vals )
        self._send( target, piCam.composeCommand( param, cast ) )


    def do_bulk( self, target, tasks ):
        """ Do a bulk operation, assume the commands are pre-validated
        :param target: (string) IP Address of camera being controlled
        :param tasks: (string) A Bulk execution string
        :return: None
        """
        commands = tasks.split(";")
        for cmd_string in commands:
            imperative, data = cmd_string.split( " ", 1 )
            self._HANDLER[ imperative ]( target, data )

    def close( self, *args ):
        """
        Set the Flag to end this process and do a graceful shutdown on the socket
        :return: None
        """
        self.running.clear()
