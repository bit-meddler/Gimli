"""
"""
# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
print( _git_root_ )
CODE_PATH = os.path.join( _git_root_, "midget", "Python" )
DATA_PATH = os.path.join( _git_root_, "rpiCap", "exampleData" )
sys.path.append( CODE_PATH )

from copy import deepcopy
import json
import numpy as np
from pprint import pprint

from collections import Counter, defaultdict
from Core.labelling import labelWandFrame
from Core.math3D import FLOAT_T


def pairPermuteSorted( items ):
    # assuming sorted list of items, make tuple permutations
    num = len( items )
    ret = []
    for i in range( num ):
        for j in range( i+1, num ):
            ret.append( (items[i], items[j]) )
    return ret

def buildCaliData( frames ):
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
            print( "Pairing: Pair: {}, Wands: {}".format( pair, pair_counts[ pair ] ) )

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

    remains = list( cams - banned_cams )
    return pairs, remains

def getListContaining( item, holder ):
    """ Expecting a list of lists, return the member list containing the item """
    for X in holder:
        if item in X:
            return X
    return [ item, ]

def computePair( A, B, frame_idxs, frames, labels ):
    # OK solve the fundamental matrix I guess....
    # https://dellaert.github.io/19F-4476/Slides/S07-SFM-A.pdf
    # https://www.robots.ox.ac.uk/~vgg/hzbook/hzbook2/HZepipolar.pdf
    # http://users.umiacs.umd.edu/~ramani/cmsc828d/lecture27.pdf
    # http://www.cse.psu.edu/~rtc12/CSE486/lecture19.pdf
    Es = []
    for idx in frame_idxs:
        strides, x2ds, _ = frames[ idx ]
        A_si, A_so = strides[A], strides[A+1]
        B_si, B_so = strides[B], strides[B+1]
        A_order = np.argsort( labels[idx][A_si:A_so] )
        B_order = np.argsort( labels[idx][B_si:B_so] )

        for i in range( A_so - A_si ):
            xu,  xv  = x2ds[ A_si + A_order[i] ]
            xu_, xv_ = x2ds[ B_si + B_order[i] ]

            Es.append( [xu*xu_, xu*xv_, xu, xv*xu_, xv*xv_, xv, xu_, xv_] )

    # I've no idea what I'm doing here
    Es = np.asarray( Es, dtype=FLOAT_T )
    b  = -np.ones( (Es.shape[0],), dtype=FLOAT_T )
    F, residuals, rank, s = np.linalg.lstsq( Es, b, rcond=None )
    # Maybe I should use SVD, that was CD's answer for everything
    # that's right SVD: https://www.youtube.com/watch?v=DDjfhYxqp3w&t=1736s
    F = np.append( F, 1.0 )
    U, s, V_T = np.linalg.svd( F.reshape( (3,3) ) )
    W = np.asarray( [[0, -1, 0],
                     [1,  0, 0],
                     [0,  0, 1]], dtype=FLOAT_T )

    u3 = U[:,2].reshape((3,1))

    # Four permutations
    P_1 = np.hstack( (U * W   * V_T,  u3) )
    P_2 = np.hstack( (U * W   * V_T, -u3) )
    P_3 = np.hstack( (U * W.T * V_T,  u3) )
    P_4 = np.hstack( (U * W.T * V_T, -u3) )

    # How do I triangulate the dets to 3Ds, with some slack?
    
    return None, None

def sterioCalibrate( pairs, groups, frames, labels, matches, mats ):
    # pair A & B
    # find the groups A & B are members of
    # Calibrate A & B, locking A at RT=np.eye(4)
    # transform groupA into A's space
    # transform groupB into B's space
    # merge to a new group
    new_groups = []
    for A, B in pairs:
        gp_A = getListContaining( A, groups )
        gp_B = getListContaining( B, groups )

        if( gp_A in groups ): groups.remove( gp_A )
        if( gp_B in groups ): groups.remove( gp_B )

        pair_frames = matches[ (A,B) ]

        # Todo: Computer Vision PhD at Oxon or Surrey

        P_A, P_B = computePair( A, B, pair_frames, frames, labels )

        # if A or B in a group, do the rigid transform

        # return the solved camea group

        gp_A.extend( gp_B )
        new_groups.append( gp_A )
    
    return new_groups




#########################################################################################
with open( os.path.join( DATA_PATH, "calibration.json" ), "r" ) as fh:
    frames = json.load( fh )

    # Damn, these detections are "native" (px) and need to be in NDCs
    ids, counts, matches = buildCaliData( frames )

    # Prime the calibration with approx matching
    pair_counts, cams = matchReport( matches )
    P_mats = [ np.zeros((3,4), dtype=FLOAT_T) for _ in cams ]
    ungrouped = sorted( list( cams ) )
    cam_groups = []
    all_cams_grouped = False

    while( not all_cams_grouped ):
        sterio_tasks, ungrouped = findGoodMarrage( pair_counts, cams, ungrouped, cam_groups )
        cam_groups = sterioCalibrate( sterio_tasks, cam_groups, frames, ids, matches, P_mats )
        print( "Cal'd Cam Groups: {}, leftover cameras: {}".format( cam_groups, ungrouped ) )
        if( len( cam_groups ) == 1 ):
            all_cams_grouped = True

    # Refine calibration, openCv PnP ?

print( "done" )
