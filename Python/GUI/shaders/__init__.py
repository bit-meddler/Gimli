""" Shader Helper"""
import os
import re

class ShaderHelper( object ):
    # path to find the shader programs, if None, expect local (relative) to calling app
    shader_path = None

    # Overload these with your shader program
    vtx_src = None
    frg_src = None
    geo_src = None

    # or place a path to the file / QResource
    vtx_f = None
    frg_f = None
    geo_f = None

    LAYOUT_RE = r".*(?:layout)" + \
                r"(?:\(\s*location\s*=\s*(?P<location>\d)\s*\))?" + \
                r"\s+(?P<specifier>\w+)" + \
                r"\s+(?P<type>[a-z]+)(?P<shape>\d*(?:x\d)?)" + \
                r"\s*(?P<name>.*?)\s*;"

    UNIFORM_RE = r".*(?:uniform)" + \
                 r"\s+(?P<type>[a-z]+)(?P<shape>\d*(?:x\d)?)" + \
                 r"\s*(?P<name>.*?)\s*;"

    MAIN_RE = r".*void\s+main\(\).*"

    LAYOUT_MATCH  = re.compile( LAYOUT_RE  )
    UNIFORM_MATCH = re.compile( UNIFORM_RE )
    MAIN_MATCH    = re.compile( MAIN_RE )

    def __init__( self ):
        # Attempt to load files
        for file_name in ( self.vtx_f, self.frg_f, self.geo_f, ):
            if( file_name is None ):
                continue

            # if a path is set look in the right place
            if( self.shader_path is not None ):
                file_path = os.path.join( self.shader_path, file_name )
            else:
                file_path = file_name

            # there is a path, attempt to load
            if( os.path.exists( file_path ) ):
                with open( file_path, "r" ) as fh:
                    program = fh.read()

                if( file_name.endswith(".vert") ):
                    self.vtx_src = program

                elif( file_name.endswith(".frag") ):
                    self.frg_src = program

                elif( file_name.endswith(".geom") ):
                    self.geo_src = program

                # elif( file_name.endswith(".tesc") ):
                #     self.unimp = program

                # elif( file_name.endswith(".tese") ):
                #     self.unimp = program

                # elif( file_name.endswith(".comp") ):
                #     self.unimp = program

        # Examine the Vertex Shader's attributes
        attr_data = []
        uniforms = []
        for line in self.vtx_src.splitlines():
            if( not line ):
                continue

            match = self.LAYOUT_MATCH.match( line )
            if( match ):
                attr_data.append( match.groupdict() )
                continue

            match = self.UNIFORM_MATCH.match( line )
            if( match ):
                uniforms.append( match.groupdict() )
                continue

            match = self.MAIN_MATCH.match( line )
            if( match ):
                break

        # Determine the layout data
        offset = 0
        encountered = set()
        layout_data = {}

        for idx, attr in enumerate( attr_data ):
            # some preemptive error checks
            if (attr[ "name" ] in encountered):
                print( "Warning, already processed a variable called '{}'".format( attr[ "name" ] ) )
            encountered.add( attr[ "name" ] )

            if (attr[ "location" ] in layout_data):
                print( "Warning, already processed data in location '{}'".format( attr[ "location" ] ) )

            # New in GLSL 4.0 double, dvecN, dmatN, dmatNxM
            size = 8 if (attr[ "type" ].startswith( "d" )) else 4  # even a bool is a 32-bit value

            dims = 0
            if (attr[ "shape" ] == ""):  # Scaler
                dims = 1

            elif ("x" in attr[ "shape" ]):  # Has to be a matrix
                N, M = map( int, attr[ "shape" ].split( "x" ) )
                dims = N * M

            else:  # either a vec or a square mat
                N = int( attr[ "shape" ] )
                if ("mat" in attr[ "type" ]):
                    dims = N * N
                else:
                    dims = N

            layout_data[ int( attr[ "location" ] ) ] = ( attr[ "name" ], dims, offset )
            offset += dims * size

        # Stash the layout data
        self.attr_locs = {}

        layout = []
        for idx in sorted( layout_data.keys() ):
            data = layout_data[ idx ]
            layout.append( data )
            self.attr_locs[ data[0] ] = idx

        self.layout = tuple( layout )
        self.line_size = offset

        # TODO: Look for uniforms as well
        # TODO: Validate vtx 'outs' match frg 'in's


if( __name__ == "__main__" ):
    # Test the Shader helper
    class BasicShaders( ShaderHelper ):
        vtx_src = """
            # version 330
            layout( location=0 ) in vec3 a_position ;
            layout( location=1 ) in vec3 a_colour ;
            layout( location=2 ) in vec2 a_uvCoord ;
            out vec3 v_colour ;
            out vec2 v_uvCoord ;
            uniform mat4 u_rotation ;
            void main() {
                gl_Position = u_rotation * vec4( a_position, 1.0f ) ;
                v_colour = a_colour ;
                v_uvCoord = a_uvCoord ;
            }
        """
        frg_src = """
            # version 330
            in vec3 v_colour ;
            in vec2 v_uvCoord ;
            out vec4 outColor ;
            uniform sampler2D s_texture ;
            void main() {
              outColor = texture( s_texture, v_uvCoord ) * vec4( v_colour, 1.0f ) ;
              // outColor = vec4( v_colour, 1.0 ) ;
            }
        """

        shader_info = BasicShaders()

        for name, num, offset in shader_info:
            location = shader_info.attr_locs[ name ]
            print( "Found Vertex Attribute '{}' @ location {} with {} elems from {}b".format( name, location, num, offset ) )
            print( "The Line Size is {}".format( shader_info.line_size ) )