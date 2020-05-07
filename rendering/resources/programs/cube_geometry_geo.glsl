#version 330

#define CHUNK_SIZE 4096 // 16^3
#define CHUNK_LENGTH 16

layout (points) in;
layout (points, max_vertices = 1) out; // 4 vertices per side of the cube

in int block_type[];

uniform sampler2D world_tex;

//out vec2 uv;
//out vec3 normal;
//out vec3 out_pos;

// Define the 8 corners of a cube (back plane, front plane (counter clockwise))
//vec3 cube_corners[8] = vec3[]  (
//	vec3( 1.0,  1.0, -1.0), // right top far
//	vec3(-1.0,  1.0, -1.0), // left top far
//	vec3(-1.0, -1.0, -1.0), // left bottom far
//	vec3( 1.0, -1.0, -1.0), // right bottom far
//	vec3( 1.0,  1.0,  1.0), // right top near
//	vec3(-1.0,  1.0,  1.0), // left top near
//	vec3(-1.0, -1.0,  1.0), // left bottom near
//	vec3( 1.0, -1.0,  1.0)  // right bottom near
//);

//ivec2 get_index(ivec3 pos) {
//    ivec3 chunk = pos/CHUNK_SIZE;
//    pos = ivec3(mod(pos, CHUNK_SIZE));
//    int in_chunk_id = CHUNK_SIZE * CHUNK_SIZE * pos.y + CHUNK_SIZE * pos.z + pos.x;
//    int chunk_id = 0;
//    return ivec2(chunk_id, in_chunk_id);
//}
//
//int get_block(ivec3 pos) {
//    return int(texture(world_tex, get_index(pos)).x);
//}

void main()
{

    ivec3 point = ivec3(gl_in[0].gl_Position.xyz);
    if (block_type[0] == 1){
        gl_Position = vec4(point.xyz, 1.); // + cube_corners[3]);
        EmitVertex();

//        gl_Position = vec4(point.xyz, 1.);
//        EmitVertex();
//
//        gl_Position = vec4(point.xyz, 1.);
//        EmitVertex();

        EndPrimitive();
    }


//    emit_quad(corners[3], corners[2], corners[0], corners[1]); // back
//    emit_quad(corners[6], corners[7], corners[5], corners[4]); // front
//    emit_quad(corners[7], corners[3], corners[4], corners[0]); // right
//    emit_quad(corners[2], corners[6], corners[1], corners[5]); // left
//    emit_quad(corners[5], corners[4], corners[1], corners[0]); // top
//    emit_quad(corners[2], corners[3], corners[6], corners[7]); // bottom

}
