# 
# Copyright (C) 2016~2022 The Gimli Project
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

""" First fumbling with camera calibration.
"""
# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "Gimli", "Python" )
DATA_PATH = os.path.join( _git_root_, "Gimli", "ExampleData" )
sys.path.append( CODE_PATH )

from collections import Counter, defaultdict
from copy import deepcopy
import pickle
from pprint import pprint

import numpy as np
import cv2

from Core.labelling import labelWandFrame
from Core.math3D import FLOAT_T
from Core import Nodes

# ------------------------------------- This is all Just list & Dict bashing -------------------------------------------
def pairPermuteSorted( items ):
    """ assuming sorted list of items, make tuple permutations (was a comprehension, but hard to read)"""
    num = len( items )
    ret = []
    for i in range( num ):
        for j in range( i+1, num ):
            ret.append( (items[i], items[j]) )
    return ret

def safeMin( listlike ):
    """ min without puking on an empty list """
    if( len( listlike ) < 1 ):
        return 0
    return min( listlike )

def buildCaliData( frames, target_frames, start, step ):
    """ Try to find target_frames count of wands in every camera.  from start index
        take step so we don't sample too many 'sequential' frames with little wand movement
        hopefully this gives us random and average coverage over each camera's sensor.

        Args:
            frames       (list): MoCap Data structure - this is modified by the Labeller!
            target_frames (int): Goal number of frames to collect for every camera
            start         (int): Index to start collecting frames at
            step          (int): number of frames to skip when collecting frames

        Returns:
            counts    (Counter): wand counts - debug
            matches      (dict): Dict indexed on tuple of camera id (camA,cmaB) being a list
                                 of frames where both cams see the wand
            idx           (int): index that we got to when searching, in case we need to gather
                                 more wands (for refinement/bundle adjust)
    """
    wand_counts = Counter()
    matchings = defaultdict( list )

    num_frames = len( frames )
    idx = start
    rounds = 0

    while( safeMin( wand_counts.values() ) < target_frames ):

        report = wandLabelFrame( frames, idx )

        if( len( report ) < 2 ):
            idx += step
            continue # can't do anything with 0 or 1 wands

        wand_counts.update( report )
        for pair in pairPermuteSorted( report ):
            matchings[ pair ].append( idx )

        idx += step
        if( idx > num_frames ):
            rounds += 1
            idx = rounds
            if( rounds > target_frames ):
                # we've looped round without finding enough frames. bail.
                break

    return ( wand_counts, matchings, idx )

def wandLabelFrame( frames, idx ):
    """ attempt to ID the wand on frame idx of frames, update that frame with the labels"""
    strides, x2ds, old_ids = frames[ idx ]
    ids, report = labelWandFrame( x2ds, strides )
    frames[ idx ] = (strides, x2ds, ids) # update with labels
    return report

def matchReport( matchings ):
    """ Count the number of 'wands' camera pairs have seen, also report on number of cameras seen."""
    pair_counts = {}
    observed_cameras = set()
    for k, v, in matchings.items():
        pair_counts[k] = len(v)
        observed_cameras.add( k[0] )
        observed_cameras.add( k[1] ) 
    return pair_counts, observed_cameras

def keyWithMax( d ):
    """ Return Key of dict with max value """
    return max( d, key=lambda x:  d[x] )

def restrictedDict( d, exclued ):
    """ Return the subset of d not containing excluded (was a comprehension, but hard to read) """
    # sounds uncomfortable!
    ret = {}
    for k in d.keys():
        if( k[0] not in exclued and k[1] not in exclued ):
            ret[k] = d[k]
    return ret

def prioritizeDict( d, required ):
    """ Return the subset of d containing keys with a member in required (was a comprehension, but hard to read) """
    ret = {}
    for k in d.keys():
        if( k[0] in required or k[1] in required ):
            ret[k] = d[k]
    return ret

def unionDict( d, keys ):
    """ Return the subset of d containing keys (was a comprehension, but hard to read) """
    ret = {}
    for k in d.keys():
        if( k in keys ):
            ret[k] = d[k]
    return ret

def permutePairings( A, B ):
    """ Assuming a & b are exclusive, pair all a-b elements """
    pairings = set()
    for a in A:
        for b in B:
            option = [a,b]
            pairings.add( ( min(option), max(option) ) )

    return pairings

def getListContaining( item, holder ):
    """ Expecting a list of lists, return the member list containing the item """
    for X in holder:
        if item in X:
            return X
    return [ item, ]

def findGoodMarrage( pair_counts, cams, ungrouped, grouped ):
    """
    Args:
        pair_counts (Dict): Map of camera pair (A,B,) to a count of their corresponding frames
        cams (Set): Set of cameras to
        ungrouped (List): List of cameras that are not in a group
        grouped (List): List of camera groups (also a list)

    Returns:
        pairs (List): List of camera pairs to try and solve
        remains (List): List of cameras that couldn't be put in a group

    For UNGROUPED cameras:
            1 Find the pair with most shared views of the wand
            2 Remove these cameras from the 'available pairs'
                2.1 if one of the pair is in a group, remove it's partners as well
            3 until we run out
        For GROUPED cameras:
            1 find a pair linking two groups with most shared views of the wand
            2 remove all cameras from these groups from the 'available pairs'
            3 until we run out
            4 if a group is left over, prevent it's cameras being mis diagnosed as Ungrouped
            
        Return the pairs to join, and any ungrouped cameras that need to be joined next iteration
    """
    pairs = []
    banned_cams = set()

    if( len( ungrouped ) > 0 ):
        # Prioritize marrying ungrouped cameras
        available_pairs = prioritizeDict( pair_counts, ungrouped )

        while( len(available_pairs) > 1 ):
            pair = keyWithMax( available_pairs )
            pairs.append( pair )
            # test if either member of the pair is in a camera group,
            # add that group's cameras to the 'used' list
            for cam in [ pair[0], pair[1] ]:
                banned_cams.update( getListContaining( cam, grouped ) )
            available_pairs = restrictedDict( available_pairs, banned_cams )
            print( "Pairing Cameras: {}, Wands: {}".format( pair, pair_counts[ pair ] ) )

    if( len( grouped ) > 0 ):
        # If there are grouped cameras find the optimal pivot and make those a pair

        # if an ungrouped camera has been paired with a camera that's a member of a group,
        # restrict that group's cameras this round
        # might be depricated! as we try to do this above...
        for A, B in pairs:
            banned_cams.update( getListContaining( A, grouped ) )
            banned_cams.update( getListContaining( B, grouped ) )

        available_pairs = restrictedDict( pair_counts, banned_cams )
        available_groups = deepcopy( grouped ) # we'll be mutating available_groups

        while( len( available_groups ) > 1 ):
            gp_A = available_groups.pop()
            gp_B = None
            score = -1
            optimal_pair = None
            for gp in available_groups:
                candidate_pairs = permutePairings( gp_A, gp )
                if( len( candidate_pairs ) < 1 ):
                    continue
                candidate_matches = unionDict( available_pairs, candidate_pairs )
                if( len( candidate_matches ) < 1 ):
                    continue
                best = keyWithMax( candidate_matches )
                if( available_pairs[best] > score ):
                    gp_B = gp
                    optimal_pair = best
                    score = available_pairs[ optimal_pair ]

            if( gp_B is not None ):
                # take this pairing
                pairs.append( optimal_pair )
                available_groups.remove( gp_B )
                banned_cams.update( gp_A )
                banned_cams.update( gp_B )
                print( "Merging Groups, Group A: {}, Group B: {}, Pair: {}, Wands: {}".format(
                    gp_A, gp_B, optimal_pair, pair_counts[ optimal_pair ] ) )

            if( len( available_groups ) == 1 ):
                # a group we can't merge, B&!
                banned_cams.update( available_groups[0] )

    remains = list( cams - banned_cams )
    return pairs, remains


# ------------------------------------------ Computer Vision stuff starts here -----------------------------------------
def skew( x ):
    """
    Generate the Skew-Symmetric matrix for vector x

    Args:
        x (vec3): Vector to make skew Symmetric

    Returns:
        M (mat33): The Matrix
    """
    return np.array([[    0, -x[2],  x[1] ],
                     [ x[2],     0, -x[0] ],
                     [-x[1],  x[0],     0 ] ])

def projectionFromFundamental( F ):
    """
    From the Radkie Lecture
    https://youtu.be/DDjfhYxqp3w?list=PLuh62Q4Sv7BUJlKlt84HFqSWfW36MDd5a&t=922
    P' = [ [e_]x * F + e_*vv.T | l*e_ ], let vv=[0,0,0] l=1

    Args:
        F (mat34): The Fundamental matrix

    Returns:
        P (mat34): The Projection matrix
    """

    U, s, V_T = np.linalg.svd( F )

    e_ = V_T[:,-1]

    P = np.hstack( ( np.dot( skew(e_), F ) + e_, e_.reshape((3,1)) ) )

    pprint( P )
    return P

def projectionsFromMatrix( E ):
    """
    From Radkie and Cyril

    Args:
        E (mat34): The Essential matrix

    Returns:
        Ps (4 mat34s): The 4 possible Projection matrices
    """
    U, s, V_T = np.linalg.svd( E )

    # Test rotation
    if( np.linalg.det( np.dot(U, V_T) ) < 0. ):
        V_T = -V_T

    # Assess the 4 possible solutions
    W = np.asarray( [ [  0, -1,  0 ],
                      [  1,  0,  0 ],
                      [  0,  0,  1 ] ], dtype=FLOAT_T )

    u3 = U[ :, 2 ].reshape( (3, 1) )

    # Four permutations - or have I missed something?
    P_1 = np.hstack( (np.dot( np.dot( U, W   ), V_T ),  u3) )
    P_2 = np.hstack( (np.dot( np.dot( U, W   ), V_T ), -u3) )
    P_3 = np.hstack( (np.dot( np.dot( U, W.T ), V_T ),  u3) )
    P_4 = np.hstack( (np.dot( np.dot( U, W.T ), V_T ), -u3) )

    return [ P_1, P_2, P_3, P_4 ]

def makeMatchList( A, B, frame_idxs, frames ):
    """
    Make a list of corresponding image co-ords for cameras A & B using frame_idxs

    Args:
        A                (int): 'Left' camera index
        B                (int): 'Right' camera index
        frame_idxs      (list): list of frames with a correspondence between A & B
        frames (list of lists): MoCap Frames data structure

    Returns:
        matches         (list): The match list
    """
    matches = []
    for idx in frame_idxs:
        strides, x2ds, labels = frames[ idx ]
        A_si, A_so = strides[A], strides[A+1]
        B_si, B_so = strides[B], strides[B+1]
        A_order = np.argsort( labels[A_si:A_so] )
        B_order = np.argsort( labels[B_si:B_so] )

        for i in range( A_so - A_si ):
            matches.append( [ x2ds[ A_si + A_order[i] ], x2ds[ B_si + B_order[i] ] ] )

    return matches

def makeEquations( matches ):
    """
    Args:
        matches (list): list of pairs of corresponding detections

    Returns:
        List of Equations to form AX=0 problem (Kroniker)

    """
    Es = []
    for A2d, B2d in matches:
        u , v , _ = A2d # ignore bogo radius!
        u_, v_, _ = B2d
        Es.append( [u*u_, u*v_, u, v*u_, v*v_, v, u_, v_, 1] )

    return np.asarray( Es, dtype=FLOAT_T )

def testFmat( F, matches ):
    """
    Test a Fundamental or Essential matrix by computing epipoles and testing a known correspondence

    Args:
        F (mat33): The Matrix to test
        matches (list): list of pairs of corresponding detections
    """
    u,  v , _ = matches[0][0]
    u_, v_, _ = matches[0][1]
    x  = np.asarray( [u,v,1], dtype=FLOAT_T )
    x_ = np.asarray( [u_,v_,1], dtype=FLOAT_T )
    zero = np.dot( np.dot(x_, F), x )
    epl = np.dot( x, F ) # F(x) -> epipolar line of x'

    if( np.linalg.det(F) > 1e-8 ):
        print( "Unacceptable Determinant!" )

    print( "x:{:.3f},{:.3f} x':{:.3f},{:.3f} epl [{:.5f}, {:.5f}, {:.5f}] Ferr {:.5f}\n".format(
        u, v, u_, v_, *epl, zero ) )

def computePair( A, B, frame_idxs, frames, cam_A, cam_B, clamp, force_eigen=False ):
    """ OK solve the fundamental matrix I guess....
            https://dellaert.github.io/19F-4476/Slides/S07-SFM-A.pdf
            https://www.robots.ox.ac.uk/~vgg/hzbook/hzbook2/HZepipolar.pdf
            http://users.umiacs.umd.edu/~ramani/cmsc828d/lecture27.pdf
            http://www.cse.psu.edu/~rtc12/CSE486/lecture19.pdf

        # Which is it E or F? I don't know the intrinsics initially, but hopefully we can refine them
        # We do have a good 1st guess at the inital Ks though

        A note on notation, I'm writing e', P' etc as e_, P_, and it follows a
        P'' would be P__.  However I'm also keeping track of np.svd emitting V Transpose
        by writing V_T - this doesn't mean V'T.  Sorry that's the best I've got

        Args:
            A                (int): 'Left'  camera index
            B                (int): 'Right' camera index
            frame_idxs      (list): list of frames with a correspondence between A & B
            frames (list of lists): MoCap Frames data structure
            cam_A    (Camera Node): Access to Initial Projection Matrix for Camera A
            cam_B    (Camera Node): Access to Initial Projection Matrix for Camera B
            clamp            (int): Limit number of frames that contribute to solution
            force_eigen     (bool): Force Eigenvalues of F (Compute the essential matrix)

        Returns:
            P_A (mat34): The Projection Matrix of camera A
            P_B (mat34): The Projection Matrix of camera B

    """
    # Get current P matrix
    P_A = cam_A.P
    P_B = cam_B.P

    # make Equations
    matches = makeMatchList( A, B, frame_idxs, frames )
    Es = makeEquations( matches )

    # SVD method
    print( "solving {} Equations".format( Es.shape[0] ) )
    U, s, V_T = np.linalg.svd( Es )
    Fa = V_T[:,-1].reshape( (3,3) ) # F aprox
    
    # Clamp to Rank 2
    U, s, V_T = np.linalg.svd( Fa )

    if( force_eigen ):
        # If we have Normalized using a known k matrix, we can compute the Essential Matrix
        s = [ 1., 1., 0.]

    D = np.diag( s )
    D[2,2] = 0

    F = np.dot( np.dot( U, D ), V_T )

    # An alternate way of getting E is K2.T @ F @ K1
    if( True ):
        E = np.dot( cam_B.K.T, np.dot( F, cam_A.K) )

    # test matrix's plausibility ?
    # testFmat(F,matches)

    # get possible solutions
    P_Bs = projectionsFromMatrix( E )

    # pick a point & make Homogenous
    a2d, b2d = matches[ 0 ]
    a2d[2] = b2d[2] = 1.

    # Test point is reconstructed in a plausible place
    P_B_computed = None
    for P in P_Bs:
        recon = triangulatePoint( a2d, b2d, P_A[:3,:], P )

        # if it's behind A, that's a no-go
        if( recon[2] < 0. ):
            continue

        P_B_ = np.linalg.inv( np.vstack( [P, [0., 0., 0., 1.]] ) )
        B_pos = np.dot( P_B_[:3, :4], recon )

        if( B_pos[2] > 0. ):
            P_B_computed = P

    if( P_B_computed is None ):
        print( "Unable to find valid P_B" )
    else:
        P_B = np.vstack( [P_B_computed, [0., 0., 0., 1.]] )

    return P_A, P_B

def triangulatePoint( a2d, b2d, P_A, P_B ):
    """
    Taken from https://github.com/alyssaq/3Dreconstruction for testing
    I'd rather write my own to fully understand the problem

    Args:
        a2d  (vec3): detection image coordinate in camera A
        b2d  (vec3): detection image coordinate in camera B
        P_A (mat34): Projection matrix A
        P_B (mat34): Projection matrix B

    Returns:

    """
    A = np.vstack( [
        np.dot( skew( a2d ), P_A),
        np.dot( skew( b2d ), P_B)
    ] )

    U, s, V_T = np.linalg.svd( A )
    P_ = np.ravel( V_T[-1, :4] )
    P_ /= P_[ 3 ]

    return P_

def stereoCalibrate( pairs, groups, frames, matches, cams, clamp ):
    """
    For each of the proposed pairing of cameras (A,B) in pairs.
        # find the groups A & B are members of
        # Calibrate A & B, locking A at RT=np.eye(4)
        # transform groupA into A's space
        # transform groupB into B's space
        # merge to a new group

    Args:
        pairs (list): A list of pairs of cameras having many corresponding points
        groups (list): A list of lists, being groups of cameras in a 'shared' coordinate system
        frames (list): MoCap Frame datastructure
        matches (Dict): A map of Camera Pairs to a list of frames with correspondances for that pair
        cams (list of Camera Nodes): The Current Camera data
        clamp (int): Limit the number of frames computed

    Returns:
        new_groups (list): The new Camera Groupings - mats is modified in place
    """
    new_groups = []
    for A, B in pairs:
        print( "Calibrating Pair ({}, {})".format( A, B ) )
        gp_A = getListContaining( A, groups )
        gp_B = getListContaining( B, groups )

        if( gp_A in groups ): groups.remove( gp_A )
        if( gp_B in groups ): groups.remove( gp_B )

        pair_frames = matches[ (A,B) ]

        # Todo: Computer Vision PhD at Oxon or Surrey

        # at an inital process, we're going from an "initalized" Camera to the 1st estimate
        P_A, P_B = computePair( A, B, pair_frames, frames, cams[A], cams[B], clamp )

        # if A or B in a group, do the rigid transform

        # return the solved camera group

        gp_A.extend( gp_B )
        new_groups.append( gp_A )

    if( len(groups) > 0 ):
        new_groups.extend( groups ) # make sure existing groups are preserved

    return new_groups

def initalizeCalibration( frames, cameras, cams, matches, pair_counts, goal_frames ):
    # cam grouping
    ungrouped = list( cameras )
    cam_groups = []
    all_cams_grouped = False

    # sanity testing
    strikes = 3
    last_state = 0

    print( "Merging pairs to initial estimate" )
    while ( (not all_cams_grouped) and (strikes > 0) ):
        stereo_tasks, ungrouped = findGoodMarrage( pair_counts, cameras, ungrouped, cam_groups )
        cam_groups = stereoCalibrate( stereo_tasks, cam_groups, frames, matches, cams, goal_frames )
        print( "Cal'd Cam Groups: {}, leftover cameras: {}\n".format( cam_groups, ungrouped ) )
        if (len( cam_groups ) == 1):
            all_cams_grouped = True

        # Force termination in unsolvable camera setup
        state = hash( (ungrouped,) )
        print( state )
        if( state == last_state ):
            strikes -= 1
        last_state = state

    if( not all_cams_grouped ):
        print( "degenerate!" )

###########################################################################################

def linear_triangulation(m1, m2, p1, p2):
    """
    Taken from https://github.com/alyssaq/3Dreconstruction for testing
    I'd rather write my own to fully understand the problem

    Linear triangulation (Hartley ch 12.2 pg 312) to find the 3D point X
    where p1 = m1 * X and p2 = m2 * X. Solve AX = 0.
    :param p1, p2: 2D points in homo. or catesian coordinates. Shape (3 x n)
    :param m1, m2: Camera matrices associated with p1 and p2. Shape (3 x 4)
    :returns: 4 x n homogenous 3d triangulated points
    """
    num_points = len( p1 )
    res = np.ones((4, num_points))

    for i in range(num_points):
        A = np.asarray([
            (p1[i][0] * m1[2, :] - m1[0, :]),
            (p1[i][1] * m1[2, :] - m1[1, :]),
            (p2[i][0] * m2[2, :] - m2[0, :]),
            (p2[i][1] * m2[2, :] - m2[1, :])
        ])

        _, _, V = np.linalg.svd(A)
        X = V[-1, :4]
        res[:, i] = X / X[3]

    return res

def cvTriangulate( P_A, P_B, a2ds, b2ds ):
    """
    Wrap cv2.triangulate and deal with formating my inputs and normalizing the return
    Args:
        P_A (mat44): 'Left' camera Projection matrix
        P_B (mat44): 'Right' camera Projection matrix
        a2ds (ndarray): nx3 list of 'left' camera points
        b2ds (ndarray): nx3 list of 'right' camera points

    Returns:
        x3ds (ndarray): nx3 array of 3d reconstructions
    """
    cv3d = cv2.triangulatePoints( P_A[ :3, : ], P_B[ :3, : ], a2ds.T[ :2, : ], b2ds.T[ :2, : ] )
    cv3d = cv3d.astype( np.float32 )
    cv3d /= cv3d[ 3, : ]  # normalize
    return cv3d[ :3, : ]  # drop the w component


def calibrateFrom3d( camera, x3ds, x2ds, lock_pp=False, lock_f=False, lock_dist=False ):
    """
    use cv2 'calibrateCamera' to solve the K, RT, and CV model distortion of a camera based on the
    3d:2d correspondences of x3ds and x2ds (which are in lockstep)

    It's that FacePalm feeling... It turns out OpenCV can't handle the -1,1 NDC coordinate system we use
    so we'll need to add the 'half width' of some fake image size to the 2ds, and then subtract it from the PP

    Args:
        camera (Node:camera): The camera object we are solving
        x3ds (ndarray): Nx3 array of 3D points
        x2ds (ndarray): Nx2 array of 2d detections in camera coordinates

    Returns:

    """
    calib_flags  = cv2.CALIB_FIX_ASPECT_RATIO | cv2.CALIB_FIX_K3 | cv2.CALIB_ZERO_TANGENT_DIST
    calib_flags |= cv2.CALIB_USE_INTRINSIC_GUESS # flag that we're priming the K

    if( lock_pp ):
        calib_flags |= cv2.CALIB_FIX_PRINCIPAL_POINT

    if( lock_f ):
        calib_flags |= cv2.CALIB_FIX_FOCAL_LENGTH

    if( lock_dist) :
        calib_flags |= cv2.CALIB_FIX_K1 | cv2.CALIB_FIX_K2

    # :(
    halfwit = 8.
    fake_size = (16,16) # int( halfwit * 2 )

    # Get camera params to prime the calibration
    distortion = np.asarray( [camera.k1, camera.k2, 0, 0 ,0] )
    camMat = camera.K.copy()
    camMat[:2,2] += halfwit # Add the fake offset to stop it asserting

    # Prepare the input data
    obj_pts = np.asarray( [x3ds], dtype=np.float32 )
    img_pts = np.asarray( [x2ds + halfwit ], dtype=np.float32 ) # detections get the fake offset as well

    # calibrate
    rms_errro, K, dist_coefs, rvecs, tvecs = cv2.calibrateCamera( obj_pts, img_pts, fake_size, camMat, distortion, flags=calib_flags )

    # Get R, T, RT
    R = cv2.Rodrigues( np.array( rvecs[ 0 ] ) )[ 0 ]
    T = np.array( tvecs[0], dtype=np.float32 )
    RT = np.hstack( (R, T) )

    K[:2,2] -= halfwit # Remove the fake offset to get us back to (-1,1)

    P = np.dot( K, RT )

    return rms_errro, P

def scoreWands( x3ds, inlyers=None, triple=(0,1,2), ratio=2.0, wand_len=240.0, stride=5, discard_quatile=False ):
    """
    Attempt to 'score' the PB matrix based on how close to the 'real' size of wand reconstructions are.
    Reconstruct the correspondences (a2ds,b2ds) using the Projection Mats PA, PB.
    for each stride (number of dots on a wand, expects 5 or 3) test the wand's triple.
    the 0-1:1-2 ratio should be close to ratio.
    the length 0-2 should be close to wand_len.
    collect lengths of wands with an acceptable ratio
    throw away the top and botom quartiles (bogus reconstructions)
    compute the scale factor that the avg. lengths are from wand_len.

    TODO: make this more RANSACy.  note which frames are bad and drop them.

    Args:
        x3ds (ndarray): Nx3 matrix of reconstructions of the wand
        inlyers (list): list of indexes of good frames(?)
        triple (tuple): Tuple of indexs of wand markers that satisfy A-B--C  2AB = BC
        ratio (float): ratio of the triple
        wand_len (float): expected length of wand from A-C
        stride (int): Number of markers on a wand Will be 5 or 3 for this method to work
        discard_quatile (bool): should the top and bottom quartiles be rejected

    Returns:
        score (float): The scale factor the avg. reconstructed wand length is away from the ideal
        inlyers (list): List of indexes we thing are good to optimize with
    """
    num_frames = x3ds.shape[1] // stride
    lens = []

    for i in range( num_frames ):
        n = i * stride
        M0 = x3ds[:,n+triple[0]]
        M1 = x3ds[:,n+triple[1]]
        M2 = x3ds[:,n+triple[2]]

        ratio_score = np.abs( ratio - np.linalg.norm( M2 - M1 ) / np.linalg.norm( M1 - M0 ) )
        t_length = np.linalg.norm( M2 - M0 )
        #print( "{: >2} T-len {} T-Ratio {}".format( i, t_length, ratio_score ) )
        if( ratio_score < 0.25 ):
            lens.append( (i,t_length,) )

    lens = np.asarray( sorted( lens, key=lambda x: x[1] ) )

    if( discard_quatile ):
        pcs = len(lens) // 4
        lens = lens[pcs:-pcs,:]

    #print( lens )

    wand_sz = np.mean( lens[:,1] )
    #print( "Avg. Reconstructed wand size {}".format( wand_sz ) )
    score = wand_len / wand_sz

    inlyers = lens[:,0]

    return score, inlyers


# Todo: So much... :(
frames=[]
with open( os.path.join( DATA_PATH, "calibration.pik" ), "rb" ) as fh:
    frames = pickle.load( fh )

num_frames = len( frames )

if( num_frames < 20 ):
    print( "Not enough MoCap to Calibrate from" )
    exit()

# Label Frames
GOAL_FRAMES = 160
step = int( num_frames / GOAL_FRAMES )
start = 0

print( "Labelling {} frames, seeking {} wands per camera".format( num_frames, GOAL_FRAMES ) )

counts, matches, last_idx = buildCaliData( frames, GOAL_FRAMES, start, step )
pair_counts, cam_idxs = matchReport( matches )

num_cams = len( cam_idxs )
cam_list = sorted( list( cam_idxs ) )

print( "Calibrating with {} cameras: {}\n".format( num_cams, counts ) )

# Initialize all cameras
root_node = Nodes.factory( Nodes.TYPE_ROOT )
cams = [ Nodes.factory( Nodes.TYPE_CAMERA, name="Cam_{:0<2}".format( i ), parent=root_node ) for i in range( max( cam_list ) ) ]

# Testing solving the Fundamental Mat for a single pair of cameras
A, B = 0, 1

print( "Computing F for pair {} {} using {} correspondence frames".format( A, B, len( matches[ (A, B,) ] ) ) )

P_A, P_B = computePair( A, B, matches[ (A, B,) ], frames, cams[A], cams[B], 42 )

from directRQ import new_vgg, directRQ

print( "Decomposing 'Right' Projection Matrix" )
K, RT = directRQ( P_B )

print( "Intrinsics" )
print(K)

print( "Extrinsics" )
print(RT)

P = np.vstack( (np.dot( K, RT ), [0., 0., 0., 1.]) )

WANDS = 55

LIMIT = WANDS * 5
pairs = makeMatchList( A, B, matches[ (A, B,) ], frames )[:LIMIT]
a2d = []
b2d = []
for a,b in pairs:
    a2d.append(a)
    b2d.append(b)
    
xA = np.asarray( a2d, dtype=np.float32 )
xB = np.asarray( b2d, dtype=np.float32 )

x3ds = cvTriangulate( P_A, P, xA, xB )

scale = 1.0
good_wands = None

for i in range( 1, 6 ):
    print( "Optimizing scene scale. round {}".format( i ) )
    x3ds *= scale
    score, good_wands = scoreWands( x3ds[:,:15], inlyers=good_wands, discard_quatile=False )
    ratio = 1.0 - score
    print( "Wand length score {}".format( ratio ) )
    scale *= score
    if( np.abs( ratio ) < 1e-6 ):
        break

print( "\nNow trying a poor man's Bundle adjust" )
last_error = 666.
scale = 1.0

_pp = True
_focal = True
_dist = True
CLAMP = 30
for i in range( 1, 4 ):
    print( "Bungle Adjust round {: >2}".format( i ) )
    # try:
    error, new_P = calibrateFrom3d( cams[B], x3ds.T[:CLAMP,:], xB[:CLAMP,:2], lock_pp=_pp, lock_f=_focal, lock_dist=_dist )

    # except:
    #     print( "CV2 Error" )
    #     break

    score, good_wands = scoreWands( x3ds )
    scale *= score
    Kn, RTn = directRQ( np.vstack( (new_P,[0.,0.,0.,1.]) ) )
    print( "Calibration Error: {} Wand length score {}".format( error, 1.0 - score ) )
    print( Kn )
    #print( RTn )

    if( error < last_error ):
        P = new_P
        last_error = error
        print( "Error reduced, accepting new params" )
        cams[ B ].K = Kn

    if( i > 5 ):
        _focal = False

    if( i > 8 ):
        _pp = False

    # Don't really have many tools to 'change' the calibration :S
    x3ds = cvTriangulate( P_A, P, xA, xB )


import matplotlib.pyplot as plt

fig = plt.figure()
fig.suptitle( "3D Reconstruction", fontsize=16 )
ax = fig.gca( projection="3d" )

ax.set_xlabel( "X-axis" )
ax.set_ylabel( "Y-axis" )
ax.set_zlabel( "Z-axis" )

cols = [ "r.", "g.", "b.", "c.", "m.", "y.", "k." ]
num_cols = len( cols )
lens = []

for i in range ( WANDS ):
    col = cols[ i %  num_cols ]
    in_ =  i    * 5
    out = (i+1) * 5

    M1 = x3ds[ :, in_ ]
    M2 = x3ds[ :, in_ + 2 ]
    t_length = np.linalg.norm( M2 - M1 )

    #print( "{: >2} T length: {}".format( i, t_length ) )
    lens.append( t_length )
    
    if( True ):
        ax.plot( x3ds[ 0, in_:out ], x3ds[ 1, in_:out ], x3ds[ 2, in_:out ], col )

plt.show()


# Prime the calibration ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#initalizeCalibration( frames, cam_idxs, cams, matches, pair_counts, GOAL_FRAMES )

# Refine calibration, openCv PnP / Bundle?

