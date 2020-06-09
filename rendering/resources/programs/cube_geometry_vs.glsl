#version 330

uniform int CHUNK_LENGTH;

uniform ChunkOffset
{
  vec3 offset[32*32];
} chunk_offsets;


vec3 get_pos(int index) {
    //int chunk_offset = int(index/CHUNK_SIZE);

    //index = int(mod(index, CHUNK_SIZE));

    int y = int(index / (CHUNK_LENGTH * CHUNK_LENGTH));
    index -= y * CHUNK_LENGTH * CHUNK_LENGTH;
    int z = int(index / CHUNK_LENGTH);
    index -= z * CHUNK_LENGTH;
    int x = int(mod(index, CHUNK_LENGTH));

    return vec3(x,y,z);
}

in int in_block;
out int block_type;
out int index;

void main() {
    vec3 pos = get_pos(gl_VertexID);
    block_type = in_block;
    index = gl_VertexID;
	gl_Position = vec4(pos, 1.0);
}