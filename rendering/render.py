"""
Renders 100 x 100 cubes using instancing.
We are using the moderngl-window specific VAO wrapper.

Each cube is animated in the vertex shader offset by gl_InstanceID
"""
from pathlib import Path

import numpy as np
from pyrr import Matrix44
import moderngl
import moderngl_window
from moderngl_window import geometry

from rendering.base import CameraWindow
import world_manager

#                   grass           stone             edge of rendering
block_colors = [(0.1, .5, 0.1, 1.), (.3, .3, .3, 1.), (.1, .1, .5, .25)]


class CubeSimpleInstanced(CameraWindow):
    """Renders cubes using instancing"""
    gl_version = (4, 6)
    title = "Plain Cube"
    resource_dir = (Path(__file__).parent / 'resources').resolve()
    aspect_ratio = None

    # render settings
    max_render_distance = 16
    render_distance = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wnd.mouse_exclusivity = True
        self.camera.projection.update(near=1, far=1000)
        self.cube = geometry.cube(size=(1, 1, 1))
        self.prog = self.load_program('programs/cube_simple_instanced.glsl')
        self.prog['m_proj'].write(self.camera.projection.matrix)
        self.prog['m_model'].write(Matrix44.identity(dtype='f4'))

        # Generate per instance data representing a grid of cubes
        world = world_manager.World(2, generate_new=True)
        # load some chunks into memory
        for z in range(6):
            for x in range(2):
                world.get_chunk(x, 0, z)
        # world.save_world('world-24x24')

        chunks = list(world.chunks.values())

        buffer = self.ctx.buffer(reserve=world_manager.Chunk.byte_size * len(chunks))

        indirect_data = []
        chunk_offsets = []

        for index, chunk in enumerate(chunks):
            block_bytes, num_blocks = chunk.to_bytes()
            indirect_data.extend([36, num_blocks, 0, index * chunk.max_blocks, 0])
            buffer.write(block_bytes, offset=index * chunk.byte_size)
            chunk_offsets.append(chunk.get_global_pos())

        chunk_offsets = np.array(chunk_offsets).astype('f4').flatten()
        elements_in_chunk_offset = 3 * self.max_render_distance ** 2  # total of vec3 * max_render_distance^2
        print(elements_in_chunk_offset - chunk_offsets.size)
        chunk_offsets = np.pad(chunk_offsets, (0, elements_in_chunk_offset - chunk_offsets.size))
        print(chunk_offsets.size)
        indirect_data = np.array(indirect_data).astype(np.uint)

        self.prog['chunk_offsets'].write(chunk_offsets)
        self.indirect_buffer = self.ctx.buffer(indirect_data)

        self.cube.buffer(buffer, '3u1 u1/i', ['in_offset', 'in_color'])

    def render(self, time: float, frametime: float):
        self.ctx.enable_only(moderngl.CULL_FACE | moderngl.DEPTH_TEST)

        self.prog['m_camera'].write(self.camera.matrix)
        # print(struct.unpack('3fi', self.buffer.read(16, offset=16)))
        self.cube.render_indirect(self.prog, self.indirect_buffer)
        # self.cube.render(self.prog, instances=self.num_blocks)

    def key_event(self, key, action, modifiers):
        super().key_event(key, action, modifiers)


if __name__ == '__main__':
    # noinspection PyTypeChecker
    moderngl_window.run_window_config(CubeSimpleInstanced)
