#version 330

#if defined VERTEX_SHADER

// Model geometry
in vec3 in_position;
in vec3 in_normal;

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
    vec4 p = m_view * vec4(in_position, 1.0);
    gl_Position =  m_proj * p;
    mat3 m_normal = inverse(transpose(mat3(m_view)));
    normal = m_normal * normalize(in_normal);
    pos = p.xyz;
    color = vec4(0.25882352941176473, 0.5294117647058824, 0.9607843137254902, 1.);

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