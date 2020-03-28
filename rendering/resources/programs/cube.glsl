#version 460

#if defined VERTEX_SHADER
#define MAX_RENDER_DISTANCE 32

// chunk offsets ~r^2
uniform ChunkOffset
{
  vec4 offset[MAX_RENDER_DISTANCE*MAX_RENDER_DISTANCE];
} chunk_offsets;

// block colors
vec4 block_colors[3] = { vec4(1., 0., 0., .5), vec4(.3, .3, .3, 1.), vec4(.1, .1, .5, 1.) };

// vertex data
//in int gl_DrawID;

// Model geometry
in vec3 in_position;
in vec3 in_normal;

// Per instance data
in uvec3 in_offset;
in uint in_color;

// uniform matrices
uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;


// out variables
out vec3 pos;
out vec3 normal;
out vec4 color;

void main() {
    mat4 m_view = m_camera * m_model;
    vec4 p = m_view * vec4(in_position + in_offset + chunk_offsets.offset[gl_DrawID].xyz, 1.0);
    gl_Position =  m_proj * p;
    mat3 m_normal = inverse(transpose(mat3(m_view)));
    normal = m_normal * normalize(in_normal);
    pos = p.xyz;
    color = block_colors[in_color];
}

#elif defined FRAGMENT_SHADER

out vec4 fragColor;

in vec3 pos;
in vec3 normal;
in vec4 color;

void main() {
    float l = dot(normalize(-pos), normalize(normal));
    fragColor = vec4(color.xyz * (0.25 + abs(l) * 0.75), color.w);

}
#endif