import numpy as np

"""
https://see.stanford.edu/materials/lsoeldsee263/04-qr.pdf

"""

def setRot( rx, ry, rz ):
    # assume XYZ rot order
    R = np.array([ [np.cos(ry) * np.cos(rz),
                    np.cos(rz) * np.sin(rx) * np.sin(ry) - np.cos(rx) * np.sin(rz),
                    np.sin(rx) * np.sin(rz) + np.cos(rx) * np.cos(rz) * np.sin(ry)],
                   [np.cos(ry) * np.sin(rz),
                    np.sin(rx) * np.sin(ry) * np.sin(rz) + np.cos(rx) * np.cos(rz),
                    np.cos(rx) * np.sin(ry) * np.sin(rz) - np.cos(rz) * np.sin(rx)],
                   [-np.sin(ry),
                     np.cos(ry) * np.sin(rx),
                     np.cos(rx) * np.cos(ry)] ])
    return R


def rq2(A):
    ''' From the CVguy's blog 2010


    Implement rq decomposition using QR decomposition
 
    From Wikipedia,
     The RQ decomposition transforms a matrix A into the product of an upper triangular matrix R (also known as right-triangular) and an orthogonal matrix Q. The only difference from QR decomposition is the order of these matrices.
     QR decomposition is Gram-Schmidt orthogonalization of columns of A, started from the first column.
     RQ decomposition is Gram-Schmidt orthogonalization of rows of A, started from the last row.
    '''
    A = np.asarray(A)
 
    m, n = A.shape
 
    # Reverse the rows
    reversed_A = np.flipud(A)
 
    # Make rows into column, then find QR
    Q, R = np.linalg.qr( reversed_A.T )

    #print( Q, R )
 
    # The returned R is flipped updown, left right of transposed R
    R = np.flipud( np.transpose(R) )
    R[:,0:m-1] = R[:,m-1:0:-1]
 
    # The returned Q is the flipped up-down of transposed Q
    Q = np.transpose(Q)
    Q[0:m-1, :] = Q[m-1:0:-1, :]


    # actually close, but loses the t component!
    return R, Q # Nope thats a fail


def rq( P ):
    """
        Instructor provided (!) from Brown (!) University
        https://github.com/sreenithy/Camera-Calibration/blob/master/Calibrartion_sree%20.ipynb
    """
    M = P[0:3,0:3]

    Q, R = np.linalg.qr(P)

    K = R/float(R[2,2])

    if K[0,0] < 0:
        K[:,0] = -1*K[:,0]
        Q[0,:] = -1*Q[0,:]

    if K[1,1] < 0:
        K[:,1] = -1*K[:,1]
        Q[1,:] = -1*Q[1,:]

    if np.linalg.det(Q) < 0:
        print( 'Warning: Determinant of the supposed rotation matrix is -1' )

    P_3_3 = np.dot(K,Q)

    P_proper_scale = (P_3_3[0,0]*P)/float(P[0,0])

    t = np.dot(np.linalg.inv(K), P_proper_scale[:,3])

    return K, Q, t


def gramSchmidt( P ):
    """
    Notes: https://www.math.ucla.edu/~yanovsky/Teaching/Math151B/handouts/GramSchmidt.pdf
    Wikipedia:
    RQ decomposition is Gram-Schmidt orthogonalization of rows of A, started from the last row.
    """
    R = np.eye(3,dtype=np.float32)
    Q = np.zeros((3,4),dtype=np.float32)

    u_1 = P[2,:]
    e_1 = u_1 / np.linalg.norm( u_1 )

    #print( u_1, e_1 )
    
    u_2 = P[1,:] - np.dot( e_1, np.dot( e_1, P[1,:] ) )
    e_2 = u_2 / np.linalg.norm( u_2 )

    #print( u_2, e_2 )

    u_3 = P[0,:] - np.dot( e_1, np.dot( e_1, P[0,:] ) ) - np.dot( e_2, np.dot( e_2, P[0,:] ) )
    e_3 = u_3 / np.linalg.norm( u_3 )

    #print( u_3, e_3 )

    R = [ [ np.dot( P[2,:], e_1 ), np.dot( P[1,:], e_1 ), np.dot( P[0,:], e_1 ) ],
          [                     0, np.dot( P[1,:], e_2 ), np.dot( P[0,:], e_2 ) ],
          [                     0,                     0, np.dot( P[0,:], e_3 ) ] ]
    
    R = np.asarray( R )
    Q = np.hstack( (e_1, e_2, e_3) ).T.reshape(3,4)

    return (R, Q) # that's another Nope

def new_vgg( P ):
    # Reverse the rows
    filped = np.flipud( P )
    
    # Decompose
    Qqr, Rqr = np.linalg.qr( filped.T )
    
    # Restore
    Rqr = np.flipud( Rqr.T )
    K = np.fliplr( Rqr )
    R = np.transpose( np.fliplr( Qqr ) ) # R has been transposed!
    
    # from the R, Q we now have, try the vgg method again
    # Fix the signs - I'm sure this isn't very correct, but it works!
    sg = np.sign( P )

    K = np.multiply( np.abs( K ), sg )
    R = np.multiply( np.abs( R ), sg )
    t = np.dot( np.linalg.inv( K ), -R )

    # Audment R with t, overwriting the partial values in col 3
    RT = R
    RT[:,3] = t[:,3]
    return K[:3,:3], RT[:3,:]

def vgg_RQ( P ):
    """
    From the Hallowed VGG https://www.robots.ox.ac.uk/~vgg/hzbook/code/

    Translated from the origenal Matlab into NumPy
    """

    P = P.T

    q, r = np.linalg.qr( P[ ::-1, ::-1], "complete" )
    
    q = q.T
    q = q[ ::-1, ::-1]
    
    r = r.T
    r = r[ ::-1, ::-1]

    if( np.linalg.det(q) < 0 ):
        r[:,0] *= -1
        q[0,:] *= -1
        
    return r, q

def vgg_KRT_from_P(P):
    N = 3
    H = P[:,0:N]  # if not numpy,  H = P.to_3x3()

    [K,R] = oxonRQ(H)

    K /= K[-1,-1]

    # from http://ksimek.github.io/2012/08/14/decompose/
    # make the diagonal of K positive
    sg = np.diag(np.sign(np.diag(K)))

    K = K * sg
    R = sg * R
    # det(R) negative, just invert; the proj equation remains same:
    if (np.linalg.det(R) < 0):
       R = -R
    # C = -H\P[:,-1]
    C = np.linalg.lstsq(-H, P[:,-1])[0]
    T = -R*C
    return K, R, T # another Nope, WTF AZ?


def directRQ( P, axis_x=1., axis_y=1., axis_z=1. ):
    # 
    # Copyright (C) 2016~2021 The Gimli Project
    # This file is part of Gimli <https://github.com/bit-meddler/Gimli>.
    #
    # Gimli is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.
    #
    # Gimli is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.
    #
    # You should have received a copy of the GNU General Public License
    # along with Gimli.  If not, see <http://www.gnu.org/licenses/>.
    #

    """
    Directly solving per element, knowing this is P -> K, RT rather than a generalized case.

    Danger, I'm assuming that R is playing nicly (det-1, rows orthonormal)

    Here is the P matrix, multipliyed out:
    
    [ ['(fx*arxx)+(sk*arxy)+(ox*arxz)', '(fx*aryx)+(sk*aryy)+(ox*aryz)', '(fx*arzx)+(sk*arzy)+(ox*arzz)', '(fx*atx)+(sk*aty)+(ox*atx)'],
      [          '(fy*arxy)+(oy*arxz)',           '(fy*aryy)+(oy*aryz)',           '(fy*arzy)+(oy*arzz)',          '(fy*aty)+(oy*atx)'],
      [                     '(f*arxz)',                      '(f*aryz)',                      '(f*arzz)',                    '(f*atx)']]

    """
    fx = sk = ox = fy = oy = 0
    RT = np.zeros( (3,4), dtype=np.float32 )
    
    # Row 2:      f * RT[2,:] ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #        K[2,2] * RT[2,:]
    # f Should be === 1, so we get this entire row for free
    RT[2,:] = P[2,]


    # Row 1:       fy*RT[1,:] + oy*RT[2,:] ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #        K[1,1] * RT[1,:] + K[1,2] * RT[2,:]
    # we have RT[2,:3]. first 3 elements of rows 2 and 3 are rotations, so should be orthogonal
    oy = np.dot( P[1,:3], RT[2,:3] )
    
    # gram schmit ???
    fy_R1 = P[1,:] - (RT[2,:] * oy)
    
    # Because the Rotation Part started as a unit vector, then it's norm is the scalor fy
    fy = np.linalg.norm( fy_R1[:3] )
    # so the whole row can be recovered by division
    RT[1,:] = fy_R1 / fy
    
    

    # Row 0:       fx*RT[0,:] + sk*RT[1,:]       + ox*RT[2,:] ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #        K[0,0] * RT[0,:] + K[0,1] * RT[1,:] + K[0,2] * RT[2,:]

    # RT[0,:3] is the ROT and again should be Orthogonal to RT[1:,:3] & RT[2:,:3]
    # so ox and sk can be recovered by dotting with the rotations we have
    ox = np.dot( P[0,:3], RT[2,:3] )
    sk = np.dot( P[0,:3], RT[1,:3] )

    # and the last unknowns, as above
    fx_R0 = P[0,:] - (RT[2,:] * ox)  - (RT[1,:] * sk)
    fx = np.linalg.norm( fx_R0[:3] )
    RT[0,:] = fx_R0 / fx


    # final suitability test
    assert( np.allclose( RT[0,:3], np.cross( RT[1,:3], RT[2,:3] ) ) )
    
    # Complete
    K = np.asarray( [ [ fx, sk, ox ],
                      [  0, fy, oy ],
                      [  0,  0,  1 ] ], dtype=np.float32 )

    # Axis flips, as suggested in: http://ksimek.github.io/2012/08/14/decompose/
    # ! Experimental !
    K[:,0]   *= axis_x
    RT[0,:3] *= axis_x

    K[:,1]   *= axis_y
    RT[1,:3] *= axis_y

    K[:,2]   *= axis_z
    RT[2,:3] *= axis_z
    
    return K, RT


# Lets see if any of these work...

# form an aproximatly correct P matrix, by K x RT, with realistic K and RT components
np.set_printoptions( precision=6, suppress=True )

# Give me a K!
K = np.eye(3)
K[0,0] = K[1,1] = 2500 # focal length in px (12.5mm / 5umm) = what I'd expect for a modern 4MP camea and lens combo
K[:2,2] = 1001 # Image centre

# Give me an R!
R = setRot( np.deg2rad(-20), np.deg2rad(15), np.deg2rad(6) )

# test othonormality
for i in range( 3 ):
    print( np.linalg.norm( R[i,:] ) )

# Give me a T!
t = np.asarray( [ 305, 1822, 305 ] ).reshape( 3, 1 )

# Give me a P!
RT = np.hstack( (R,t) )
P = np.dot( K, RT )
P = np.vstack( (P, np.asarray([[0,0,0,1]])) )
print( "Test configuration:" )
print( K )
print( RT )
print( P )

# Try out RQ Decomposition with various methods I've googled for over the last week...
#algos = [ rq, rq2, gramSchmidt, vgg_KRT_from_P, directRQ ]
algos = [ new_vgg, directRQ ]
for algo in algos:
    print( "\nRunning '{}'".format( algo.__name__ ) )

    try:
        K_, RT_ = algo( P )
        print( K_ )
        print( RT_ )
    except:
        print( "That's a Nope" )

    else:
        print( "Intrinsic closeness:" )
        try:
            print( K_ - K )
        except ValueError:
            print( "error", K_.shape )

        print( "Extrinsic closeness:" )
        try:
            print( RT_ - RT )
        except ValueError:
            print( "error", RT_.shape )
