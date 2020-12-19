""" labelling.py

Functions for Labelling MoCap detections.

Labels are simply a number in the range 1..2147483647. (int32.max) they represent the Markers on an item
we are tracking in the MoCap volume.  This could eb a human, a rigid prop, or an articulated prop.  The
'subject management' systems will define a lookup between IDs and human readable marker names etc.

Note, if subjects are re-ordered the IDs will get out of sync.

ID === 0 is an unidentified detection, and could have a label applied manually ot with a labeller
ID < 0 could be "Prohibited", so not possible to label, and will not contribute to 3D reconstruction

ID < -2147479552 (int32.min + 4096) is a range of "special Labels" to let alternate colours be used efficiently

"""

import numpy as np

from Core.math3D import FLOAT_T, ID_T
from Core.mathUtils import argsortLite

# Special IDs
SID_BASE = -2147479552
SID_CONV =  2147479552 # np.abs( val+SID_CONV ) -> 0, 1 .. 4096

SID_WHITE = SID_BASE
SID_RED   = SID_BASE - 1
SID_GREEN = SID_BASE - 2
SID_BLUE  = SID_BASE - 3

SID_COLOURS = [
    [ 1.0, 1.0, 1.0 ],
    [ 1.0, 0.0, 0.0 ],
    [ 0.0, 1.0, 0.0 ],
    [ 0.0, 0.0, 1.0 ],
]


# Wand Colours
WAND_COLOURS = [
    [ 1.0, 0.0, 0.0 ], # Red
    [ 1.0, 1.0, 0.0 ], # Yellow
    [ 0.0, 1.0, 0.0 ], # Green
    [ 0.0, 1.0, 1.0 ], # Cyan
    [ 0.0, 0.0, 1.0 ], # Blue
]

# Wand Labelling ---------------------------------------------------------------
PARALLEL_THRESHOLD = np.tan( np.deg2rad( 10 ) ) # degrees of deviance allowed


def distanceMatrix( A ):
    rows = len( A )

    dm = np.empty( (rows, rows), dtype=np.float32 )

    for i in range( 0, rows ):
        for j in range( i, rows ):

            if (i == j):
                dm[ i, j ] = 0.0

            else:
                dist = np.linalg.norm( A[ i ] - A[ j ] )
                dm[ i, j ] = dist
                dm[ j, i ] = dist

    return dm


def labelWand( dets, s_in, s_out, verbose=False ):
    """

    :param dets: array of 2D detections
    :param s_in: stride in index
    :param s_out: stride out index
    :param verbose: debug flag
    :return: best labelling of each det in order (if labelled) or None if not labelled, and the hypothesis score
    """
    num_dets = s_out - s_in

    if (num_dets != 5):  # In the future could we service 5+ candidates?
        return (None, None)

    best_score = 10.0

    cam_dets = np.array( dets[ s_in:s_out ], dtype=np.float32 )
    dm = distanceMatrix( cam_dets )

    ids = None
    for i, row in enumerate( dm ):
        # Hypothosis: assume i is 2
        if (verbose):
            print( "Hypothisis {} {}".format( i, "*" * 10 ) )

        # closest should be 1, 2nd closest 3 or 4 - Todo: except in degenerate poses!
        close = np.argpartition( row, 4 )[ :4 ]  # 2 + the zero
        close = close[ argsortLite( row[ close ] ) ][ 1: ]

        # farthest should be 5
        far = np.argpartition( row, -1 )[ -1: ]

        one = cam_dets[ close[ 0 ] ]
        two = cam_dets[ i ]
        one_two_u = (two - one) / dm[ i, close[ 0 ] ]

        # check candidates
        # 'a' = close[1], 'b' = close[2]
        one_three_a_u = (cam_dets[ close[ 1 ] ] - one) / dm[ close[ 0 ], close[ 1 ] ]
        one_three_b_u = (cam_dets[ close[ 2 ] ] - one) / dm[ close[ 0 ], close[ 2 ] ]

        ang = [ 0.0, 0.0, 0.0 ]  # trick to match idxs to close idx

        ang[ 1 ] = np.dot( one_two_u, one_three_a_u )
        ang[ 2 ] = np.dot( one_two_u, one_three_b_u )

        winner = 1 if (ang[ 1 ] > ang[ 2 ]) else 2  # most parallel wins!
        loser = 2 if (winner == 1) else 1

        if ((ang[ winner ] + PARALLEL_THRESHOLD) < 1.0):
            # not a good candidate
            continue

        if (verbose):
            print( "Winner '{}' sc {}, angle {}".format( close[ winner ], ang[ winner ], np.arccos( ang[ winner ] ) ) )

        # test 2-5, 2-4 are parallel
        two_five_u = (cam_dets[ far[ 0 ] ] - two) / dm[ i, far[ 0 ] ]
        two_candidate_u = (cam_dets[ close[ loser ] ] - two) / dm[ i, close[ loser ] ]

        ang[ 0 ] = np.dot( two_five_u, two_candidate_u )

        if ((ang[ 0 ] + PARALLEL_THRESHOLD) < 1.0):
            # not a good candidate
            continue

        if (verbose):
            print( "Candidate '{}' sc {}, angle {}".format( loser, ang[ 0 ], np.arccos( ang[ 0 ] ) ) )

        # ratio test - because the wand has been "perspective projected", this is less reliable I think
        tee = (dm[ i, close[ winner ] ] / dm[ i, close[ 0 ] ]) / 2.0
        leg = (dm[ i, far[ 0 ] ] / dm[ i, close[ loser ] ]) / 2.0

        if (verbose):
            print( "ratio Scores", tee, leg )  # closest to 1 wins

        # Score the hypothesis
        score = (ang[ winner ] + ang[ 0 ] + tee + leg) / 4.0
        if( np.abs( score - 1.0 ) < best_score ):
            best_score = score

            ids = [ 0, 0, 0, 0, 0 ]

            ids[ close[ 0 ] ]      = 1
            ids[ i ]               = 2
            ids[ close[ winner ] ] = 3
            ids[ close[ loser ] ]  = 4
            ids[ far[ 0 ] ]        = 5

    return (ids, best_score)


def labelWandFrame( dets, strides ):
    """
    Labels the whole frame described by the dets array and the stride list.
    returns ids array, and label report of which cameras got labelled
    """
    report = []
    ids = np.full( len( dets ), 0, dtype=ID_T )

    for cam, (s_in, s_out) in enumerate( zip( strides[:-1], strides[1:] ) ):
        labels, score = labelWand( dets, s_in, s_out, False )
        if( labels is not None ):
            ids[ s_in : s_out ] = labels
            report.append( cam )

    return (ids, report)