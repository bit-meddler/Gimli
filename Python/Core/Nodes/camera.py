import numpy as np
from . import Node, TYPE_CAMERA

class Camera( Node ):
    """ Basic class for cameras in the system, they could be:
            # Free cameras (Navigation, ortho)
            # Calibrated MoCap Cameras (Locked params, unless being calibrated)
            # Video or still cameras (like 3DE)

        We need to be OpenGL Compatible for drawing, but leave that upto UINodes
    """
    TYPE_INFO = TYPE_CAMERA

    def __init__( self, name, parent=None ):
        super( Camera, self ).__init__( name, parent )
        # Extrinsics - RT -----------------------------------------------
        # Internal
        self.RT = np.zeros( (3,4), dtype=np.float32 )
        self.R  = np.eye( 3, dtype=np.float32 )
        # Human
        self.position = np.zeros( (3,1), dtype=np.float32 )
        self.orientation = [0.,0.,0.] # expects degrees, X, Y, Z rotation

        # Intrinsics - K ------------------------------------------------
        #Internal
        self.K  = np.eye( 3, dtype=np.float32 )
        # Human
        self.pp = [0.,0.]
        self.fovX = 0.
        self.fovY = 0.
        self.skew = 0.

        # Distortion
        self.k1 = self.k2 = 0.

        # Projection Matrix ----------------------------------------------
        self.P = np.eye( 4, dtype=np.float32 )

    # lets do some camera maths ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def formK( self, apply=True ):
        K = np.asarray( [ [ self.fovX, self.skew, self.pp[0] ],
                          [         0, self.fovY, self.pp[1] ],
                          [         0,         0,          1 ] ], dtype=np.float32 )
        if( apply ):
            self.K = K

        return K

    def formR( self, apply=True ):
        """ form the R matrix from the orientation vector - rotations in X, Y, Z """
        R = np.eye(3,dtype=np.float32)
        if( apply ):
            self.R = R
        return R

    def formRT( self, apply=True, xR=None, xT=None ):
        """ Form the internal RT Matrix, an "Override" R or T can be supplied to
            superced the internal values it's expected the R is a 3x3 orthonormal
            rotation matirx, and not a list of roll, pitch, yaw values.

        """
        if( xR is not None ):
            R = np.asarray( xR, dtype=np.float32 )
        else:
            R = self.formR( False )

        if( xT is not None ):
            T = np.asarray( xT, dtype=np.float32 )
            T = T.reshape( 3, 1 )
        else:
            T = self.T

        RT = np.hstack( (R, T) )

        if( apply ):
            self.RT = RT

        return RT

    def formP( self, apply=True ):
        P = np.vstack( np.dot( self.K, self.RT ), np.asarray([[0,0,0,1]]), dtype=np.float32 )
        if( apply ):
            self.P = P
        return P