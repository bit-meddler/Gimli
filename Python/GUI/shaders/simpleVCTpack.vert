# version 330

layout( location=0 ) in vec3 a_position ;
layout( location=1 ) in vec3 a_colour ;
layout( location=2 ) in vec2 a_uvCoord ;

out vec3 v_colour ;
out vec2 v_uvCoord ;

uniform mat4 u_mvp ;
uniform float u_hilight ;

void main() {
    gl_Position = u_mvp * vec4( a_position, 1.0f ) ;
    if( u_hilight > 0.0f ) {
        v_colour = a_colour ;
    } else {
        v_colour = vec3( 0.8f, 0.0f, 0.0f ) ;
    }
    v_uvCoord   = a_uvCoord ;
}
