#version 460

#if defined VERTEX_SHADER

in vec3 in_position;

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;

uniform vec3 position;

void main() {
    mat4 m_view = m_camera * m_model;
    gl_Position = m_proj * m_view * vec4(in_position + position, 1.0);

}

    #elif defined FRAGMENT_SHADER

out vec4 fragColor;

void main() {
    fragColor = vec4(0., 1., 0., 1.);

}
    #endif