#version 330

#define CHUNK_SIZE 4096 // 16^3
#define CHUNK_LENGTH 16

#if defined VERTEX_SHADER

uniform ChunkOffset
{
  vec3 offset[32*32];
} chunk_offsets;


vec3 get_pos(int index) {
    int chunk_offset = int(index/CHUNK_SIZE);

    index = int(mod(index, CHUNK_SIZE));

    int y = int(index / (CHUNK_LENGTH * CHUNK_LENGTH));
    index -= y * CHUNK_LENGTH * CHUNK_LENGTH;
    int z = int(index / CHUNK_LENGTH);
    index -= z * CHUNK_LENGTH;
    int x = int(mod(index, CHUNK_LENGTH));

    return chunk_offsets.offset[chunk_offset] + vec3(x,y,z);
}

in int in_id;

void main() {
    vec3 pos = get_pos(in_id);
	gl_Position = vec4(pos, 1.0);
}
#endif

 #if defined GEOMETRY_SHADER

layout (points) in;
layout (triangle_strip, max_vertices = 24) out; // 4 vertices per side of the cube

uniform sampler2D world_tex;

//out vec2 uv;
//out vec3 normal;
out vec3 out_pos;

// Define the 8 corners of a cube (back plane, front plane (counter clockwise))
vec3 cube_corners[8] = vec3[]  (
	vec3( 1.0,  1.0, -1.0), // right top far
	vec3(-1.0,  1.0, -1.0), // left top far
	vec3(-1.0, -1.0, -1.0), // left bottom far
	vec3( 1.0, -1.0, -1.0), // right bottom far
	vec3( 1.0,  1.0,  1.0), // right top near
	vec3(-1.0,  1.0,  1.0), // left top near
	vec3(-1.0, -1.0,  1.0), // left bottom near
	vec3( 1.0, -1.0,  1.0)  // right bottom near
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

//#define EMIT_V(POS) \
//	out_pos = POS; \
//	EmitVertex()

void emit_quad(vec3 p1, vec3 p2, vec3 p3, vec3 p4) {
    out_pos = p1;
    EmitVertex();

    out_pos = p2;
    EmitVertex();

    out_pos = p3;
    EmitVertex();

    out_pos = p4;
    EmitVertex();

    EndPrimitive();
}

//#define EMIT_QUAD(P1, P2, P3, P4) \
//	EMIT_V(corners[P1]); \
//	EMIT_V(corners[P2]); \
//	EMIT_V(corners[P3]); \
//	EMIT_V(corners[P4]); \
//	EndPrimitive()

//#define EMIT_V(POS, UV, NORMAL) \
//	uv = UV; \
//	normal = NORMAL; \
//	gl_Position = vec4(POS, 1.0); \
//	EmitVertex()

//#define EMIT_QUAD(P1, P2, P3, P4, NORMAL) \
//	EMIT_V(corners[P1], vec2(0.0, 0.0), NORMAL); \
//	EMIT_V(corners[P2], vec2(1.0, 0.0), NORMAL); \
//	EMIT_V(corners[P3], vec2(0.0, 1.0), NORMAL); \
//	EMIT_V(corners[P4], vec2(1.0, 1.0), NORMAL); \
//	EndPrimitive()


void main()
{
	// Calculate the 8 cube corners
	//ivec3 point = ivec3(gl_in[0].gl_Position.xyz);
	//vec3 corners[8];
//	for(int i = 0; i < 8; i++)
//	{
//		vec3 pos = vec3(point.xyz + cube_corners[i] * 0.5);
//		corners[i] = pos;
//	}
    out_pos = point.xyz + cube_corners[3];
    EmitVertex();

    out_pos = point.xyz + cube_corners[2];
    EmitVertex();

    out_pos = point.xyz + cube_corners[0];
    EmitVertex();

    out_pos = point.xyz + cube_corners[1];
    EmitVertex();

    EndPrimitive();

//    emit_quad(corners[3], corners[2], corners[0], corners[1]); // back
//    emit_quad(corners[6], corners[7], corners[5], corners[4]); // front
//    emit_quad(corners[7], corners[3], corners[4], corners[0]); // right
//    emit_quad(corners[2], corners[6], corners[1], corners[5]); // left
//    emit_quad(corners[5], corners[4], corners[1], corners[0]); // top
//    emit_quad(corners[2], corners[3], corners[6], corners[7]); // bottom

//    if (get_block(point-ivec3(0,0,-1)) == 0) {
//        EMIT_QUAD(3, 2, 0, 1); // back
//    }
//	if (get_block(point-ivec3(0,0,1)) == 0) {
//        EMIT_QUAD(6, 7, 5, 4); // front
//    }
//    if (get_block(point-ivec3(1,0,0)) == 0) {
//        EMIT_QUAD(7, 3, 4, 0); // right
//    }
//    if (get_block(point-ivec3(-1,0,0)) == 0) {
//        EMIT_QUAD(2, 6, 1, 5); // left
//    }
//    if (get_block(point-ivec3(0,1,0)) == 0) {
//        EMIT_QUAD(5, 4, 1, 0); // top
//    }
//    if (get_block(point-ivec3(0,-1,0)) == 0) {
//        EMIT_QUAD(2, 3, 6, 7); // bottom
//    }
//    if (get_block(point-ivec3(0,0,-1)) == 0) {
//        EMIT_QUAD(3, 2, 0, 1, vec3( 0.0,  0.0, -1.0)); // back
//    }
//	if (get_block(point-ivec3(0,0,1)) == 0) {
//        EMIT_QUAD(6, 7, 5, 4, vec3( 0.0,  0.0,  1.0)); // front
//    }
//    if (get_block(point-ivec3(1,0,0)) == 0) {
//        EMIT_QUAD(7, 3, 4, 0, vec3( 1.0,  0.0,  0.0)); // right
//    }
//    if (get_block(point-ivec3(-1,0,0)) == 0) {
//        EMIT_QUAD(2, 6, 1, 5, vec3(-1.0,  0.0,  0.0)); // left
//    }
//    if (get_block(point-ivec3(0,1,0)) == 0) {
//        EMIT_QUAD(5, 4, 1, 0, vec3( 0.0,  1.0,  0.0)); // top
//    }
//    if (get_block(point-ivec3(0,-1,0)) == 0) {
//        EMIT_QUAD(2, 3, 6, 7, vec3( 0.0, -1.0,  0.0)); // bottom
//    }

}

#endif