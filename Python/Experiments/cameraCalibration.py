"""
"""
# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
DATA_PATH = os.path.join( _git_root_, "midget", "ExampleData" )
sys.path.append( CODE_PATH )

from copy import deepcopy
import numpy as np
import pickle
from pprint import pprint

from collections import Counter, defaultdict
from Core.labelling import labelWandFrame
from Core.math3D import FLOAT_T

def preCondition( frames ):
    new = []
    for (strides, dets, ids) in frames:
        x2ds = np.asarray( dets, dtype=FLOAT_T )
        x2ds -= 512.0
        x2ds /= 512.0
        new.append( [strides, list(x2ds), ids] )
    return new

def pairPermuteSorted( items ):
    # assuming sorted list of items, make tuple permutations
    num = len( items )
    ret = []
    for i in range( num ):
        for j in range( i+1, num ):
            ret.append( (items[i], items[j]) )
    return ret

def __buildCaliData( frames ):
    wand_counts = Counter()
    matchings = defaultdict( list )
    wand_ids = []
    for idx, (strides, x2ds, ids) in enumerate( frames ):
        ids, report = labelWandFrame( x2ds, strides )
        if( len( report ) < 2 ):
            continue # can't do anything with 0 or 1 wands

        wand_ids.append( ids )
        wand_counts.update( report )
        for pair in pairPermuteSorted( report ):
            matchings[ pair ].append( idx )

    return ( wand_ids, wand_counts, matchings )

def safeMin( listlike ):
    if( len( listlike ) < 1 ):
        return 0
    return min( listlike )

def buildCaliData( frames, target_frames, start, step ):
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
    strides, x2ds, old_ids = frames[ idx ]
    ids, report = labelWandFrame( x2ds, strides )
    frames[ idx ] = (strides, x2ds, ids) # update with labels
    return report

def matchReport( matchings ):
    pair_counts = {}
    observed_cameras = set()
    for k, v, in matchings.items():
        pair_counts[k] = len(v)
        observed_cameras.add( k[0] )
        observed_cameras.add( k[1] ) 
    return pair_counts, observed_cameras

def keyWithMax( d ):
    return max( d, key=lambda x:  d[x] )

def restrictedDict( d, exclued ):
    # sounds uncomfortable!
    ret = {}
    for k in d.keys():
        if( k[0] not in exclued and k[1] not in exclued ):
            ret[k] = d[k]
    return ret

def prioritizeDict( d, required ):
    ret = {}
    for k in d.keys():
        if( k[0]  in required or k[1]  in required ):
            ret[k] = d[k]
    return ret

def unionDict( d, keys ):
    ret = {}
    for k in d.keys():
        if( k in keys ):
            ret[k] = d[k]
    return ret

def permutePairings( A, B ):
    # assuming a & b are exclusive, pair all a-b elements
    pairings = set()
    for a in A:
        for b in B:
            option = [a,b]
            pairings.add( ( min(option), max(option) ) )

    return pairings

def findGoodMarrage( pair_counts, cams, ungrouped, grouped ):
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
        # now if there are grouped cameras not joined in the ungrouped set,
        # find the optimal pivot and make those a pair

        # if an ungrouped camera has been paired with a camera that's a member of a group,
        # restrict that group's cameras this round
        for A, B in pairs:
            banned_cams.update( getListContaining( A, grouped ) )
            banned_cams.update( getListContaining( B, grouped ) )

        available_pairs = restrictedDict( pair_counts, banned_cams )
        available_groups = deepcopy( grouped )

        while( len( available_groups ) > 1 ):
            gp_A = available_groups.pop()
            gp_B = None
            score = -1
            for gp in available_groups:
                candidate_pairs = permutePairings( gp_A, gp )
                if( len( candidate_pairs ) < 1 ):
                    continue
                possible = unionDict( available_pairs, candidate_pairs )
                if( len( possible ) < 1 ):
                    continue
                best = keyWithMax( possible )
                if( available_pairs[best] > score ):
                    gp_B = gp
                    score = available_pairs[best]

            if( gp_B is not None ):
                # take this pairing
                pair = keyWithMax( unionDict( available_pairs, permutePairings( gp_A, gp_B ) ) )
                pairs.append( pair )
                available_groups.remove( gp_B )
                banned_cams.update( gp_A )
                banned_cams.update( gp_B )
                print( "Merging Groups, Group A: {}, Group B: {}, Pair: {}, Wands: {}".format( gp_A, gp_B, pair, pair_counts[ pair ] ) )

            if( len( available_groups ) == 1 ):
                # a group we can't merge, B&!
                banned_cams.update( available_groups[0] )

    remains = list( cams - banned_cams )
    return pairs, remains

def getListContaining( item, holder ):
    """ Expecting a list of lists, return the member list containing the item """
    for X in holder:
        if item in X:
            return X
    return [ item, ]

def skew( x ):
    return np.array([[    0, -x[2],  x[1] ],
                     [ x[2],     0, -x[0] ],
                     [-x[1],  x[0],     0 ] ])

def computePair( A, B, frame_idxs, frames, clamp ):
    # OK solve the fundamental matrix I guess....
    # https://dellaert.github.io/19F-4476/Slides/S07-SFM-A.pdf
    # https://www.robots.ox.ac.uk/~vgg/hzbook/hzbook2/HZepipolar.pdf
    # http://users.umiacs.umd.edu/~ramani/cmsc828d/lecture27.pdf
    # http://www.cse.psu.edu/~rtc12/CSE486/lecture19.pdf

    # Make pairwise matches
    matches = []
    for idx in frame_idxs[:clamp]:
        strides, x2ds, labels = frames[ idx ]
        A_si, A_so = strides[A], strides[A+1]
        B_si, B_so = strides[B], strides[B+1]
        A_order = np.argsort( labels[A_si:A_so] )
        B_order = np.argsort( labels[B_si:B_so] )

        for i in range( A_so - A_si ):
            matches.append( [ x2ds[ A_si + A_order[i] ], x2ds[ B_si + B_order[i] ] ] )

    # assemble the equations
    Es = []
    for A2d, B2d in matches:
        u , v, _  = A2d # ignore bogo radius!
        u_, v_, _ = B2d
        Es.append( [u*u_, u*v_, u, v*u_, v*v_, v, u_, v_, 1] )

    # SVD method
    Es = np.asarray( Es, dtype=FLOAT_T )
    U, s, V_T = np.linalg.svd( Es )
    Fa = V_T[:,-1].reshape( (3,3) )
    
    # Clamp to Rank 2
    U, s, V_T = np.linalg.svd( Fa ) 
    D = np.diag( s )
    D[2,2] = 0
    F = np.dot( np.dot( U, D ), V_T )

    # test F's plausability
    x,  y, _  = matches[0][0]
    x_, y_, _ = matches[0][1]
    u = np.asarray( [x,y,1], dtype=FLOAT_T )
    v = np.asarray( [x_,y_,1], dtype=FLOAT_T )
    zero = np.dot( np.dot(v, F), u )
    epl = np.dot( u, F ) # F(x) -> epipolar line of x'

    print( "Det:{:.3f} x:{:.3f},{:.3f} x':{:.3f},{:.3f} epl [{:.5f}, {:.5f}, {:.5f}] Ferr {:.5f}\n".format(
        np.linalg.det(F), x, y, x_, y_, *epl, zero ) )


    # from the Radke lecture...
    # https://youtu.be/DDjfhYxqp3w?list=PLuh62Q4Sv7BUJlKlt84HFqSWfW36MDd5a&t=922
    # P' = [ [e_]x * F + e_*vv.T | l*e_ ], let vv=[0,0,0] l=1
    U, s, V_T = np.linalg.svd( F )
    e_ = V_T[:,-1]

    P_ = np.hstack( ( np.dot( skew(e_), F ) + e_, e_.reshape((3,1)) ) )



    # If essential matrix known...
    if( False ):
        U, s, V_T = np.linalg.svd( E )
        W = np.asarray( [[0, -1, 0],
                         [1,  0, 0],
                         [0,  0, 1]], dtype=FLOAT_T )
        Z = np.asarray( [[ 0, 1, 0],
                         [-1, 0, 0],
                         [ 0, 0, 0]], dtype=FLOAT_T )

        u3 = U[:,2].reshape((3,1))

        # Four permutations
        P_1 = np.hstack( (U * W   * V_T,  u3) )
        P_2 = np.hstack( (U * W   * V_T, -u3) )
        P_3 = np.hstack( (U * W.T * V_T,  u3) )
        P_4 = np.hstack( (U * W.T * V_T, -u3) )

    # How do I triangulate the dets to 3Ds, with some slack?

    return None, None

def sterioCalibrate( pairs, groups, frames, matches, mats, clamp ):
    # pair A & B
    # find the groups A & B are members of
    # Calibrate A & B, locking A at RT=np.eye(4)
    # transform groupA into A's space
    # transform groupB into B's space
    # merge to a new group
    new_groups = []
    for A, B in pairs:
        print( "Calibrating Pair ({}, {})".format( A, B ) )
        gp_A = getListContaining( A, groups )
        gp_B = getListContaining( B, groups )

        if( gp_A in groups ): groups.remove( gp_A )
        if( gp_B in groups ): groups.remove( gp_B )

        pair_frames = matches[ (A,B) ]

        # Todo: Computer Vision PhD at Oxon or Surrey

        #P_A, P_B = computePair( A, B, pair_frames, frames, clamp )

        # if A or B in a group, do the rigid transform

        # return the solved camea group

        gp_A.extend( gp_B )
        new_groups.append( gp_A )

    if( len(groups) > 0 ):
        new_groups.extend( groups ) # make sure existing groups are preserved

    return new_groups




###########################################################################################

# Todo: Need to use more than 20 frames, and provide ExampleData in the repo
frames=[]
with open( os.path.join( DATA_PATH, "calibration.pik" ), "rb" ) as fh:
    frames = pickle.load( fh )

num_frames = len( frames )


if( num_frames > 0 ):
    # need to store, K, R, T, RT, P, and k1, k2 for each camera...

    GOAL_FRAMES = 125
    step = int( num_frames / GOAL_FRAMES )
    start = 0

    print( "Labelling {} frames, seeking {} wands per camera".format( num_frames, GOAL_FRAMES ) )

    # Prime the calibration with approx matching
    counts, matches, last_idx = buildCaliData( frames, GOAL_FRAMES, start, step )
    pair_counts, cams = matchReport( matches )

    ungrouped = sorted( list( cams ) )
    cam_groups = []
    all_cams_grouped = False
    print( "Calibrating {} cameras: {}\n".format( len( cams ), counts ) )
    print( "Merging pairs to inital estimate" )
    while( not all_cams_grouped ):
        sterio_tasks, ungrouped = findGoodMarrage( pair_counts, cams, ungrouped, cam_groups )
        cam_groups = sterioCalibrate( sterio_tasks, cam_groups, frames, matches, None, GOAL_FRAMES )
        print( "Cal'd Cam Groups: {}, leftover cameras: {}\n".format( cam_groups, ungrouped ) )
        if( len( cam_groups ) == 1 ):
            all_cams_grouped = True

    # Refine calibration, openCv PnP ?

