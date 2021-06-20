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
import numpy as np
import pickle
from pprint import pprint

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

def projectionsFromEssential( E ):
    """
    From Radkie and Cyril

    Args:
        E (mat34): The Essential matrix

    Returns:
        Ps (4 mat34s): The 4 possible Projection matrixs
    """
    U, s, V_T = np.linalg.svd( E )

    # Test rotation
    if( np.linalg.det( np.dot(U, V_T) ) < 0. ):
        V_T = -V_T

    # Assess the 4 possible solutions
    W = np.asarray( [ [  0, -1,  0 ],
                      [  1,  0,  0 ],
                      [  0,  0,  1 ] ], dtype=FLOAT_T )
    # Cyril has an alternate matrix???
    Z = np.asarray( [ [  0,  1,  0 ],
                      [ -1,  0,  0 ],
                      [  0,  0,  0 ] ], dtype=FLOAT_T )

    u3 = U[ :, 2 ].reshape( (3, 1) )

    # Four permutations - or have I missed something?
    P_1 = np.hstack( (np.dot( np.dot( U, W ), V_T ), u3) )
    P_2 = np.hstack( (np.dot( np.dot( U, W ), V_T ), -u3) )
    P_3 = np.hstack( (np.dot( np.dot( U, W.T ), V_T ), u3) )
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

def computePair( A, B, frame_idxs, frames, cam_A, cam_B, clamp, force_eigen=False ):
    """ OK solve the fundamental matrix I guess....
            https://dellaert.github.io/19F-4476/Slides/S07-SFM-A.pdf
            https://www.robots.ox.ac.uk/~vgg/hzbook/hzbook2/HZepipolar.pdf
            http://users.umiacs.umd.edu/~ramani/cmsc828d/lecture27.pdf
            http://www.cse.psu.edu/~rtc12/CSE486/lecture19.pdf

        # Which is it E or F? I don't know the intrinsics initially, but hopefully we can refine them

        A note on notation, I'm writing e', P' etc as e_, P_, and it follows a
        P'' would be P__.  However I'm also keeping track of np.svd emitting V Transpose
        by writing V_T - this doesn't mean V'T.  Sorry that's the best I've got

        Args:
            A                (int): 'Left' camera index
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

    # Make pairwise matches
    matches = makeMatchList( A, B, frame_idxs, frames )

    # assemble the equations
    Es = []
    for A2d, B2d in matches:
        u , v , _ = A2d # ignore bogo radius!
        u_, v_, _ = B2d
        Es.append( [u*u_, u*v_, u, v*u_, v*v_, v, u_, v_, 1] )

    # SVD method
    print( "solving {} Equations".format( len( Es ) ) )
    Es = np.asarray( Es, dtype=FLOAT_T )
    U, s, V_T = np.linalg.svd( Es )
    Ea = V_T[:,-1].reshape( (3,3) ) # E aprox
    
    # Clamp to Rank 2
    U, s, V_T = np.linalg.svd( Ea )

    if( force_eigen ):
        s = [ 1., 1., 0.]

    D = np.diag( s )
    D[2,2] = 0

    #F = np.dot( np.dot( U, D ), V_T )
    E = np.dot( U, np.dot( D, V_T ) )

    # Normalize E?
    #E /= E[2,2]

    # test matrix's plausibility ?
    u,  v , _ = matches[0][0]
    u_, v_, _ = matches[0][1]
    x  = np.asarray( [u,v,1], dtype=FLOAT_T )
    x_ = np.asarray( [u_,v_,1], dtype=FLOAT_T )
    zero = np.dot( np.dot(x_, E), x )
    epl = np.dot( x, E ) # F(x) -> epipolar line of x'

    if( np.linalg.det(E) > 1e-8 ):
        print( "Unacceptable Determinant!" )

    print( "x:{:.3f},{:.3f} x':{:.3f},{:.3f} epl [{:.5f}, {:.5f}, {:.5f}] Ferr {:.5f}\n".format(
        u, v, u_, v_, *epl, zero ) )

    # get possible solutions
    P_Bs = projectionsFromEssential( E )

    # pick a point & make Homogenous
    a2d, b2d = matches[ 0 ]
    a2d[2] = b2d[2] = 1.

    # Test point is reconstructed in a plausable place
    for P in P_Bs:
        recon = triangulatePoint( a2d, b2d, P_A, P )

        # if it's behind A, that's a no-go
        if( recon[2] < 0. ):
            continue

        P_B_ = np.linalg.inv( np.vstack( [P, [0., 0., 0., 1.]] ) )
        B_pos = np.dot( P_B_[:3, :4], recon )

        if( B_pos[2] > 0. ):
            P_B = P

    return P_A, P_B

def triangulatePoint( a2d, b2d, P_A, P_B ):
    """
    # ???
    Args:
        a2s  (vec3): detection image coordinate in camera A
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


###########################################################################################

# Todo: So much... :(
frames=[]
with open( os.path.join( DATA_PATH, "calibration.pik" ), "rb" ) as fh:
    frames = pickle.load( fh )

num_frames = len( frames )

# Try using the Camera Nodes I started work on ages ago...
root_node = Nodes.factory( Nodes.TYPE_ROOT )

if( num_frames > 0 ):


    GOAL_FRAMES = 125
    step = int( num_frames / GOAL_FRAMES )
    start = 0

    print( "Labelling {} frames, seeking {} wands per camera".format( num_frames, GOAL_FRAMES ) )

    # Prime the calibration with approx matching
    counts, matches, last_idx = buildCaliData( frames, GOAL_FRAMES, start, step )
    pair_counts, cam_idxs = matchReport( matches )
    num_cams = len( cam_idxs )

    ungrouped = sorted( list( cam_idxs ) )
    cam_groups = []
    all_cams_grouped = False

    # Initialize all cameras
    cams = [ Nodes.factory( Nodes.TYPE_CAMERA, name="Cam_{:0<2}".format( i ), parent=root_node ) for i in range( max( ungrouped ) ) ]

    print( "Calibrating {} cameras: {}\n".format( num_cams, counts ) )
    print( "Merging pairs to inital estimate" )
    while( not all_cams_grouped ):
        stereo_tasks, ungrouped = findGoodMarrage( pair_counts, cam_idxs, ungrouped, cam_groups )
        cam_groups = stereoCalibrate( stereo_tasks, cam_groups, frames, matches, cams, GOAL_FRAMES )
        print( "Cal'd Cam Groups: {}, leftover cameras: {}\n".format( cam_groups, ungrouped ) )
        if( len( cam_groups ) == 1 ):
            all_cams_grouped = True

    # Refine calibration, openCv PnP ?

