#version 330

uniform int chunk_size;


vec3 get_pos(int index) {
    //int chunk_offset = int(index/CHUNK_SIZE);

    //index = int(mod(index, CHUNK_SIZE));

    int y = int(index / (chunk_size * chunk_size));
    index -= y * chunk_size * chunk_size;
    int z = int(index / chunk_size);
    index -= z * chunk_size;
    int x = int(mod(index, chunk_size));

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