#version 330

#define CHUNK_SIZE 4096 // 16^3
#define CHUNK_LENGTH 16

layout (points) in;
layout (triangle_strip, max_vertices = 36) out; // 4 vertices per side of the cube

in int block_type[];

uniform sampler2D world_tex;

//out vec2 uv;
out vec3 normal;
out vec3 out_pos;

// Define the 8 corners of a cube (back plane, front plane (counter clockwise))
vec3 cube_corners[8] = vec3[]  (
	vec3( 1.0,  1.0, -1.0), // right top far     0
	vec3(-1.0,  1.0, -1.0), // left top far      1
	vec3(-1.0, -1.0, -1.0), // left bottom far   2
	vec3( 1.0, -1.0, -1.0), // right bottom far  3
	vec3( 1.0,  1.0,  1.0), // right top near    4
	vec3(-1.0,  1.0,  1.0), // left top near     5
	vec3(-1.0, -1.0,  1.0), // left bottom near  6
	vec3( 1.0, -1.0,  1.0)  // right bottom near 7
);

ivec2 get_index(ivec3 pos) {
    ivec3 chunk = pos/CHUNK_SIZE;
    pos = ivec3(mod(pos, CHUNK_SIZE));
    int in_chunk_id = CHUNK_SIZE * CHUNK_SIZE * pos.y + CHUNK_SIZE * pos.z + pos.x;
    int chunk_id = 0;
    return ivec2(chunk_id, in_chunk_id);
}

int get_block(ivec3 pos) {
    return int(texture(world_tex, get_index(pos)).x);
}

void emit_quad(vec3 tl, vec3 bl, vec3 br, vec3 tr, vec3 in_normal) {
    //   top left, bottom left, bottom right, top right
    normal = in_normal;
    out_pos = tl;
    EmitVertex();
    normal = in_normal;
    out_pos = bl;
    EmitVertex();
    normal = in_normal;
    out_pos = br;
    EmitVertex();
    EndPrimitive();

    normal = in_normal;
    out_pos = tr;
    EmitVertex();
    normal = in_normal;
    out_pos = tl;
    EmitVertex();
    normal = in_normal;
    out_pos = br;
    EmitVertex();
    EndPrimitive();
}

void main()
{

    ivec3 point = ivec3(gl_in[0].gl_Position.xyz);
    if (block_type[0] == 2){
        // Calculate the 8 cube corners
        vec3 point = vec3(gl_in[0].gl_Position.xyz);
        vec3 corners[8];
        for(int i = 0; i < 8; i++)
        {
            vec3 pos = vec3(point.xyz + cube_corners[i] * 0.5);
            corners[i] = pos;
        }

        emit_quad(corners[5], corners[6], corners[7], corners[4], vec3( 0.0,  0.0,  1.0)); // front
        emit_quad(corners[1], corners[2], corners[3], corners[0], vec3( 0.0,  0.0, -1.0)); // back

        emit_quad(corners[1], corners[2], corners[6], corners[5], vec3( 1.0,  0.0,  0.0)); // left
        emit_quad(corners[0], corners[3], corners[7], corners[4], vec3( -1.0,  0.0,  0.0)); // right

        emit_quad(corners[1], corners[5], corners[4], corners[0], vec3( 0.0,  1.0,  0.0)); // top
        emit_quad(corners[2], corners[6], corners[7], corners[3], vec3( 0.0, -1.0,  0.0)); // bottom
    }


//    emit_quad(corners[3], corners[2], corners[0], corners[1]); // back
//                  1           2           0           3
//    emit_quad(corners[6], corners[7], corners[5], corners[4]); // front
//                  1           2           0           3
//    emit_quad(corners[7], corners[3], corners[4], corners[0]); // right
//    emit_quad(corners[2], corners[6], corners[1], corners[5]); // left
//    emit_quad(corners[5], corners[4], corners[1], corners[0]); // top
//    emit_quad(corners[2], corners[3], corners[6], corners[7]); // bottom

}
