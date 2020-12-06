import numpy as np

def insertSort( array ):
    num_elem = len( array )
    for i in range( 1, num_elem ):
        val, pos = array[ i ], i
        
        while( (pos>0) and (array[pos-1]>val) ):
            array[ pos ] = array[ pos - 1 ]
            pos = pos - 1

        array[ pos ] = val

def argSort( array ):
    num_elem = len( array )
    idxs = list( range( num_elem ) )
    for i in range( 1, num_elem ):
        val, pos = array[ idxs[i] ], i
        
        while( (pos>0) and (array[idxs[pos-1]]>val) ):
            idxs[ pos ] = idxs[ pos - 1 ]
            pos = pos - 1

        idxs[ pos ] = i
        
    return idxs


test = [ 5, 1, 2, 4, 3 ]

#insertSort( test )
#print( test )
npt = np.asarray( test )
print( np.argsort( npt ) )
print( argSort( test ) )
