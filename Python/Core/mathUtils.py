""" mathUtils

place for general maths helpers that stradle logical groupings, or don't fit anywhere else.

"""

def argsortLite( array ):
    num_elem = len( array )
    idxs = list( range( num_elem ) )
    for i in range( 1, num_elem ):
        val, pos = array[ idxs[ i ] ], i

        while ((pos > 0) and (array[ idxs[ pos - 1 ] ] > val)):
            idxs[ pos ] = idxs[ pos - 1 ]
            pos = pos - 1

        idxs[ pos ] = i

    return idxs