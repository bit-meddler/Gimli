# version 330

layout( location=0 ) in vec3 a_position ;

out vec3 v_colour ;

uniform mat4 u_mvp ;
uniform vec3 u_colour ;

void main() {
    gl_Position = u_mvp * vec4( a_position, 1.0f ) ;
    v_colour    = u_colour ;
}
