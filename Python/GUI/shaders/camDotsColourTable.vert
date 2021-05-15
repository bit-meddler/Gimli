    # version 330 core

    layout( location=0 ) in vec3 a_position ;
    layout( location=1 ) in int  a_id ;

    uniform mat4 u_projection ;

    // colour tables
    uniform vec3 u_cols[ {num_cols} ] ;
    uniform vec3 u_sids[ {num_sids} ] ;

    out vec3 v_colour ;

    void main() {{
        gl_Position  = u_projection * vec4( a_position.x, a_position.y, 0.0, 1.0 ) ;
        gl_PointSize = a_position.z * 2.0 ;
        if( a_id < 0 ) {{
            // frozen or a sid
            if( a_id <= {sid_bound} ) {{
                v_colour = u_sids[ abs( a_id + {sid_conv} ) ] ;
            }} else {{
                v_colour = vec3( 0.0, 0.0, 1.0 ) ;
            }}
        }} else {{
            v_colour = u_cols[ a_id ] ;
        }}
    }}