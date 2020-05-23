#version 330

#define CHUNK_SIZE 4096 // 16^3
#define CHUNK_LENGTH 16

layout (points) in;
layout (triangle_strip, max_vertices = 36) out; // 4 vertices per side of the cube

in int block_type[];

uniform isampler2D world_tex;

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

vec2 get_index(ivec3 pos) {
    //ivec3 chunk = pos/CHUNK_SIZE;
    // check if position is outside of chunk.
    if ((0 <= pos.x && pos.x <= CHUNK_LENGTH) && (0 <= pos.y && pos.y <= CHUNK_LENGTH) && (0 <= pos.y && pos.y <= CHUNK_LENGTH)) {
        int in_chunk_id = CHUNK_LENGTH * CHUNK_LENGTH * pos.y + CHUNK_LENGTH * pos.z + pos.x;
        int chunk_id = 0;
        return vec2(in_chunk_id, chunk_id);
    }
    else {
        return vec2(-1, -1);
    }
}

int get_block(ivec3 pos) {
    vec2 index = get_index(pos);
    if (index.x < 0) {
        return 2;
    }
    return texture(world_tex, index.xy).x;
}

void emit_triangle(vec3 p1, vec3 p2, vec3 p3, vec3 in_normal) {
    normal = in_normal;
    out_pos = p1;
    EmitVertex();

    normal = in_normal;
    out_pos = p2;
    EmitVertex();

    normal = in_normal;
    out_pos = p3;
    EmitVertex();

    EndPrimitive();

}

void emit_quad(vec3 tl, vec3 bl, vec3 br, vec3 tr, vec3 in_normal) {
    //   top left, bottom left, bottom right, top right
    emit_triangle(tl, bl, br, in_normal);

    emit_triangle(tr, tl, br, in_normal);
}

void main()
{

    if (block_type[0] == 1){
        // Calculate the 8 cube corners
        ivec3 point = ivec3(gl_in[0].gl_Position.xyz);
        vec3 corners[8];
        for(int i = 0; i < 8; i++)
        {
            vec3 pos = vec3(point.xyz + cube_corners[i] * 0.5);
            corners[i] = pos;
        }

        if (get_block(point + ivec3(0, 0, -1)) == 0) {
            emit_quad(corners[5], corners[6], corners[7], corners[4], vec3( 0.0,  0.0,  1.0)); // front
        }
        if (get_block(point + ivec3(0, 0, 1)) == 0) {
             emit_quad(corners[3], corners[2], corners[1], corners[0], vec3( 0.0,  0.0, -1.0)); // back
        }
        if (get_block(point + ivec3(-1, 0, 0)) == 0) {
            emit_quad(corners[1], corners[2], corners[6], corners[5], vec3( 1.0,  0.0,  0.0)); // left
        }
        if (get_block(point + ivec3(1, 0, 0)) == 0) {
            emit_quad(corners[7], corners[3], corners[0], corners[4], vec3( -1.0,  0.0,  0.0)); // right
        }
        if (get_block(point + ivec3(0, 1, 0)) == 0) {
            emit_quad(corners[1], corners[5], corners[4], corners[0], vec3( 0.0,  1.0,  0.0)); // top
        }
        if (get_block(point + ivec3(0, -1, 0)) == 0) {
            emit_quad(corners[7], corners[6], corners[2], corners[3], vec3( 0.0, -1.0,  0.0)); // bottom
        }
    }

}
