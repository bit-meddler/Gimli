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

""" mathUtils

place for general maths helpers that straddle logical groupings, or don't fit anywhere else.

"""

def argsortLite( array ):
    """
    Simple Argsort implementation, OK for up to 10 elements
    Args:
        array: (listlike) List to get sorting data from

    Returns:
        idxs: (list) List of idx of elements in array, in sorted order.
    """
    num_elem = len( array )
    idxs = list( range( num_elem ) )
    for i in range( 1, num_elem ):
        val, pos = array[ idxs[ i ] ], i

        while ((pos > 0) and (array[ idxs[ pos - 1 ] ] > val)):
            idxs[ pos ] = idxs[ pos - 1 ]
            pos = pos - 1

        idxs[ pos ] = i

    return idxs