#version 330


layout (points) in;
layout (points, max_vertices = 1) out; // 4 vertices per side of the cube

in int block_type[];

void main()
{
    ivec3 point = ivec3(gl_in[0].gl_Position.xyz);
    if (block_type[0] == 1){
        gl_Position = vec4(point.xyz, 1.);
        EmitVertex();
        EndPrimitive();
    }
}
