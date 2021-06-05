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
""" Generate the code for mask region's "NodeTrates", and their register addresses. """
num = 16
axis = ["x", "y", "m", "n"]
human = ["Left", "Top", "Right", "Bottom"]

for i in range( num ):
    for ax, hm in zip( axis, human ):
        print( """    "maskzone{0:0>2}{1}": CameraTraits( "maskzone{0:0>2}{1}", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone {0:0>2} {3}",
                                 desc="Mask {0:0>2} position {2}" ),
               """.format( i+1, ax, hm, ax.upper() ) )
        
reg = 298
for i in range( num ):
    for ax in axis:
        reg += 2
        print( """        "maskzone{0:0>2}{1}" : ( {2}, 2, True ),""".format( i+1, ax, reg ) )
