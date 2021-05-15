    # version 330 core

    layout( location=0 ) in vec3 a_position ;
    layout( location=1 ) in int  a_id ;

    uniform mat4 u_projection ;

    out vec3 v_colour ;

    void main() {
        gl_Position  = u_projection * vec4( a_position.x, a_position.y, 0.0, 1.0 ) ;
        gl_PointSize = a_position.z * 2.0 ; // is gl_PointSize legit in this profile?

        vec3 sel_col ;

        if( a_id <= 0 ) {
            // frozen or a sid
            if( a_id < -2147479551 ) {
                int s_id = abs( a_id + 2147479552 ) ;

                if(        s_id == 0 ) {
                    sel_col = vec3( 1.0, 1.0, 1.0 ) ;

                } else if( s_id == 1 ) {
                    sel_col = vec3( 1.0, 0.0, 0.0 ) ;

                } else if( s_id == 2 ) {
                    sel_col = vec3( 0.0, 1.0, 0.0 ) ;

                } else if( s_id == 3 ) {
                    sel_col = vec3( 0.0, 0.0, 1.0 ) ;
                }

            } else {
                sel_col = vec3( 0.0, 0.0, 1.0 ) ; // <-------------------------
            }

        } else {
            // A label
            sel_col = vec3( 1.0, 1.0, 1.0 ) ;

            if(        a_id == 1 ) {
                sel_col = vec3( 1.0, 0.0, 0.0 ) ;
            } else if( a_id == 2 ) {
                sel_col = vec3( 1.0, 1.0, 0.0 ) ;
            } else if( a_id == 3 ) {
                sel_col = vec3( 0.0, 1.0, 0.0 ) ;
            } else if( a_id == 4 ) {
                sel_col = vec3( 0.0, 1.0, 1.0 ) ;
            } else if( a_id == 5 ) {
                sel_col = vec3( 0.0, 0.0, 1.0 ) ;
            }
            // Fall through to White
        }
        v_colour = sel_col ;
    }