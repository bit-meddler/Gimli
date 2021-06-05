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

"""
Auto generate shaders, eg set divisions of the Point -> Circle Geometry shader
"""

def genGeoSdr( divisions=12 ):
    ret = """
#version 330 core

layout (points) in ;
layout (line_strip, max_vertices = {}) out;

void circle( vec4 position, float radius ) {{
    """.format( divisions )

    step = TWO_PI / divisions
    for i in range( divisions ):
        x = np.cos( i * step )
        y = np.sin( i * step )
        x = 0.0 if np.abs( x ) < 1.0e-8 else x
        y = 0.0 if np.abs( y ) < 1.0e-8 else y
        ret += """gl_Position = position + (vec4({x:.5f}, {y:.5f}, 0.0, 0.0) * radius) ;
    EmitVertex() ;
    """.format( x=x, y=y )

    ret += """EndPrimitive() ;
}

void main() {    
    circle( gl_in[0].gl_Position, gl_in[0].gl_PointSize ) ;
}  
"""

    return ret

