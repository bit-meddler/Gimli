    #version 330 core

    layout (points) in ;
    layout (line_strip, max_vertices = 12) out;

    void circle( vec4 position, float radius ) {

        gl_Position = position + (vec4(1.0, 0.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.8660254037844387, 0.49999999999999994, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.5000000000000001, 0.8660254037844386, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.0, 1.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.4999999999999998, 0.8660254037844387, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.8660254037844385, 0.5000000000000003, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-1.0, 0.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.8660254037844388, -0.4999999999999997, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(-0.5000000000000004, -0.8660254037844385, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.0, -1.0, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.49999999999999933, -0.866025403784439, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        gl_Position = position + (vec4(0.8660254037844384, -0.5000000000000004, 0.0, 0.0) * radius) ;
        EmitVertex() ;
        EndPrimitive() ;
    }

    void main() {
        // Is gl_PointSize legit in profile 330?
        circle( gl_in.gl_Position, gl_PointSize ) ;
    }