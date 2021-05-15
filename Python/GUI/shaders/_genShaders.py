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