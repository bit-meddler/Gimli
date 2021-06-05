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

import numpy as np
import json

# Attempt to label a wand that looks like this:
#  1---2-----3            -80mm <- 0 -> 160 mm
#      |                           |
#      |                           |
#      4                         120mm
#      |                           |
#      |                           |
#      5                         240mm


PARALLEL_THRESHOLD = np.tan( np.deg2rad( 10 ) ) # degrees of deviance allowed

def distanceMatrix( A ):
    rows = len( A  )

    dm = np.empty( (rows, rows), dtype=np.float32 )
    
    for i in range( 0, rows ):
        for j in range( i, rows ):
            
            if( i == j ):
                dm[ i, j ] = 0.0
                
            else:
                dist = np.linalg.norm( A[i] - A[j] )
                dm[ i, j ] = dist
                dm[ j, i ] = dist
            
    return dm


def labelWand( dets, s_in, s_out, verbose=False ):
    
    num_dets = s_out - s_in
    
    if( num_dets != 5 ): # In the future could we survice 5+ candidates?
        return (None, None)

    cam_dets = np.array(dets[ s_in:s_out ], dtype=np.float32)
    dm = distanceMatrix( cam_dets )

    hyp_s = np.full( num_dets, 100.0, dtype=np.float32 )
    hyp_l = [ [] for i in range( num_dets ) ]
    
    for i, row in enumerate( dm ):
        # Hypothosis: assume i is 2
        ids = [0,0,0,0,0]
        
        if( verbose ):
            print( "Hypothisis {} {}".format( i, "*" * 10 ) )
            
        # closest should be 1, 2nd closest 3 or 4 - Todo: except in degenerate poses!
        close = np.argpartition( row,  4)[:4] # 2 + the zero
        close = close[ np.argsort( row[ close ] ) ][1:]
        
        # farthest should be 5
        far = np.argpartition( row, -1)[-1:]

        one = cam_dets[ close[0] ]
        two = cam_dets[ i ]
        one_two_u = (two - one) / dm[i, close[0]] 

        # check candidates
        # 'a' = close[1], 'b' = close[2]
        one_three_a_u = (cam_dets[ close[1] ] - one) / dm[close[0], close[1]]
        one_three_b_u = (cam_dets[ close[2] ] - one) / dm[close[0], close[2]]

        ang = [ 0.0, 0.0, 0.0 ] # trick to match idxs to close idx

        ang[1] = np.dot( one_two_u, one_three_a_u )
        ang[2] = np.dot( one_two_u, one_three_b_u )
        
        winner = 1 if( ang[1] > ang[2] ) else 2 # most parallel wins!
        loser  = 2 if(   winner == 1   ) else 1
        
        if( (ang[ winner ] + PARALLEL_THRESHOLD) < 1.0 ):
            # not a good candidate
            continue
        
        if( verbose ):
            print( "Winner '{}' sc {}, deg {}".format( close[winner], ang[winner], np.arccos(ang[winner]) ) )

        # test 2-5, 2-4 are parallel
        two_five_u = (cam_dets[ far[0] ] - two) / dm[ i, far[0] ]
        two_candidate_u = (cam_dets[ close[loser] ] - two) / dm[ i, close[loser] ]

        ang[0] = np.dot( two_five_u, two_candidate_u )
        
        if( (ang[0] + PARALLEL_THRESHOLD) < 1.0 ):
            # not a good candidate
            continue

        if( verbose ):
            print( "Candidate '{}' sc {}, deg {}".format( loser, ang[0], np.arccos(ang[0]) ) )

            
        # ratio test - because the wand has been "perspective projected", this is less reliable I think
        tee = (dm[ i, close[winner] ] / dm[ i, close[0] ]) / 2.0
        leg = (dm[ i, far[0] ] / dm[ i, close[loser] ]) / 2.0

        if( verbose ):
            print( "ratio Scores", tee, leg ) # closest to 1 wins

        # hypothisis score
        hyp_s[ i ] = (ang[winner] + ang[0] + tee + leg) / 4.0
        
        # hypothisis labelling
        ids[ close[ 0 ] ]      = 1
        ids[ i ]               = 2    
        ids[ close[ winner ] ] = 3
        ids[ close[ loser ] ]  = 4
        ids[ far[ 0 ] ]        = 5

        hyp_l = ids
        
    return( hyp_s, hyp_l )

    
with open( r"C:\code\rpiCap\exampleData\calibration.json", "r" ) as fh:
    frames = json.load( fh )

strides, x2ds, ids = frames[0]

for i in range( 10 ):
    print( "camera {}".format( i ) )
    
    scores, ids = labelWand( x2ds, strides[i], strides[i+1] )
    
    if( scores is None ):
        continue
    
    idx = (np.abs(scores - 1.0)).argmin()
    print( idx, scores )
    
