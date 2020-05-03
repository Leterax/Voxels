#version 460

#if defined VERTEX_SHADER

// block colors
vec4 block_colors[3] = { vec4(1., 0., 0., 1.), vec4(.3, .3, .3, 1.), vec4(.1, .1, .5, 1.) };

// vertex data
//in int gl_DrawID;

// Model geometry
in vec3 in_position;
in vec3 in_normal;

// Per instance data
in vec3 in_offset;


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
    vec4 p = m_view * vec4(in_position + in_offset, 1.0);
    gl_Position =  m_proj * p;
    mat3 m_normal = inverse(transpose(mat3(m_view)));
    normal = m_normal * normalize(in_normal);
    pos = p.xyz;
    color = block_colors[0];
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