#version 330

#if defined VERTEX_SHADER

#include programs/noise.glsl

//in int in_id;
uniform vec3 offset;

uniform float seed;
uniform float scale;
uniform float amplitude;
uniform int chunk_length;

out int block_type;

vec3 get_pos(int index) {
    int y = int(index / (chunk_length * chunk_length));
    index -= y * chunk_length * chunk_length;
    int z = int(index / chunk_length);
    index -= z * chunk_length;
    int x = int(mod(index, chunk_length));

    return vec3(x,y,z);
}


void main() {
    vec3 location = offset + get_pos(gl_VertexID);
    float height = (snoise(vec3(location.xz*scale, seed)) + 1.) / 2. * amplitude;
    if (location.y < height) {
        block_type = 1;
    }
    else{
        block_type = 0;
    }

}
#endif