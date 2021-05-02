# version 330

in vec3 v_colour ;
in vec2 v_uvCoord ;

out vec4 outColor ;
uniform sampler2D s_texture ;

void main() {
  outColor = texture( s_texture, v_uvCoord ) * vec4( v_colour, 1.0f ) ;
}
