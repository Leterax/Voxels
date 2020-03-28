"""
Renders 100 x 100 cubes using instancing.
We are using the moderngl-window specific VAO wrapper.

Each cube is animated in the vertex shader offset by gl_InstanceID
"""
from pathlib import Path
from typing import List

import numpy as np
from pyrr import Matrix44
import moderngl
import moderngl_window
from moderngl_window import geometry

from rendering.base import CameraWindow
import world_manager
from _types import Point


def list_difference(list1, list2):
    s = set(list2)
    return [x for x in list1 if x not in s]


class CubeSimpleInstanced(CameraWindow):
    """Renders cubes using instancing"""
    gl_version = (4, 6)
    title = "Plain Cube"
    resource_dir = (Path(__file__).parent / 'resources').resolve()
    aspect_ratio = None

    # render settings
    max_render_distance = 32
    render_distance = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.wnd.mouse_exclusivity = True

        self.cube_program = self.load_program('programs/cube.glsl')
        self.player_program = self.load_program('programs/player_render.glsl')

        self.cube_program['m_proj'].write(self.camera.projection.matrix)
        self.cube_program['m_model'].write(Matrix44.identity(dtype='f4'))

        self.player_program['m_proj'].write(self.camera.projection.matrix)
        self.player_program['m_model'].write(Matrix44.identity(dtype='f4'))
        self.player_position = np.array((0, 15, 0))

        self.camera.projection.update(near=1, far=1000)

        # the model rendered at each voxels position
        self.cube = geometry.cube(size=(1, 1, 1))
        # the model rendered at the players position
        self.player = geometry.sphere()

        # Generate per instance data representing a grid of cubes
        self.world = world_manager.World(2, generate_new=True)

        # set of chunks with their index in the buffers and their position. the actual chunk instance is not saved here
        self.chunks_in_view: List[Point, ...] = list()

        # reserve the buffers:
        # We assume a maximum of MAX_RENDER_DISTANCE^2 chunks will ever be in the buffer.
        # A chunk offset (vec4) is four floats (4 bytes) so 4*4 bytes. Each chunk has one of these.
        # Each indirect draw call is 5 uints (4 bytes) so 5 * 4 bytes.
        self.instanced_data_buffer = self.ctx.buffer(
            reserve=world_manager.Chunk.byte_size * self.max_render_distance ** 2)
        self.chunk_offsets_buffer = self.ctx.buffer(reserve=4 * 4 * self.max_render_distance ** 2)
        self.chunk_offsets_buffer.bind_to_uniform_block()
        self.indirect_buffer = self.ctx.buffer(reserve=4 * 5 * self.max_render_distance ** 2)

        # bind the instanced data to our cube vao. this cube will be instanced many times.
        self.cube.buffer(self.instanced_data_buffer, '3u1 u1/i', ['in_offset', 'in_color'])

        self.reload_chunks()

        # indirect_data = []
        # chunk_offsets = []
        #
        # for index, chunk in enumerate(chunks):
        #     block_bytes, num_blocks = chunk.to_buffer_bytes()
        #     indirect_data.extend([36, num_blocks, 0, index * chunk.max_blocks, 0])
        #     buffer.write(block_bytes, offset=index * chunk.byte_size)
        #     chunk_offsets.append((*chunk.get_global_pos(), 0))
        #
        # indirect_data = np.array(indirect_data).astype(np.uint)
        # chunk_offsets_buffer.write(np.array(chunk_offsets).astype('f4').flatten())
        #
        # chunk_offsets_buffer.bind_to_uniform_block()
        # self.indirect_buffer = self.ctx.buffer(indirect_data)

    def update_chunks(self):
        # calculate all chunks in view using the current player position
        player_position_chunk_space = (
            self.player_position[0] // world_manager.Chunk.size.x,
            self.player_position[1] // world_manager.Chunk.size.y,
            self.player_position[2] // world_manager.Chunk.size.z
        )
        current_chunks_in_view = self.world.positions_in_radius(player_position_chunk_space, self.render_distance)
        number_of_chunks_visible = len(current_chunks_in_view)
        # calculate the difference
        chunks_nolonger_in_view = list_difference(self.chunks_in_view, current_chunks_in_view)
        chunks_now_in_view = list_difference(current_chunks_in_view, self.chunks_in_view)
        # go through and replace the chunks no longer in view with new ones
        for index, chunk_pos in enumerate(chunks_now_in_view):
            chunk_to_replace = chunks_nolonger_in_view[index]
            index_to_replace = self.chunks_in_view.index(chunk_to_replace)
            # replace the chunk
            self.chunks_in_view.pop(index_to_replace)
            self.chunks_in_view.insert(index_to_replace, chunk_pos)

            self.write_chunk_to_buffers(chunk_pos, index_to_replace)

    def clear_all_buffers(self):
        self.chunk_offsets_buffer.clear()
        self.indirect_buffer.clear()
        self.instanced_data_buffer.clear()

    def reload_chunks(self):
        chunk_positions = self.world.positions_in_radius(self.player_position, self.render_distance)
        self.clear_all_buffers()
        self.chunks_in_view.clear()
        for index, chunk_pos in enumerate(chunk_positions):
            self.write_chunk_to_buffers(chunk_pos, index)
            self.chunks_in_view.append(chunk_pos)

        print(self.chunks_in_view)

    def write_chunk_to_buffers(self, chunk_pos, index):
        chunk = self.world.get_chunk(*chunk_pos)
        block_bytes, num_blocks = chunk.to_buffer_bytes()

        indirect_data = np.array([36, num_blocks, 0, index * chunk.max_blocks, 0], dtype=np.uint)
        self.indirect_buffer.write(indirect_data, offset=20 * index)

        self.instanced_data_buffer.write(block_bytes, offset=index * chunk.byte_size)

        chunk_offset_data = np.array([*chunk.get_global_pos(), 0], dtype='f4')
        self.chunk_offsets_buffer.write(chunk_offset_data, offset=4 * 4 * index)

    def render(self, time: float, frametime: float):
        self.ctx.enable_only(moderngl.CULL_FACE | moderngl.DEPTH_TEST)

        # update camera values in both programs
        self.cube_program['m_camera'].write(self.camera.matrix)
        self.cube_program['m_proj'].write(self.camera.projection.matrix)

        self.player_program['m_camera'].write(self.camera.matrix)
        self.player_program['m_proj'].write(self.camera.projection.matrix)
        self.player_program['position'].write(self.player_position.astype('f4'))

        # render all chunks in one draw call
        self.cube.render_indirect(self.cube_program, self.indirect_buffer)

        # render the player
        self.player.render(self.player_program)

    def key_event(self, key, action, modifiers):
        super().key_event(key, action, modifiers)

        keys = self.wnd.keys

        if key == keys.LEFT:
            self.player_position += (2, 0, 0)
            self.update_chunks()
        if key == keys.RIGHT:
            self.player_position += (-2, 0, 0)
            self.update_chunks()
        if key == keys.UP:
            self.player_position += (0, 0, 2)
            self.update_chunks()
        if key == keys.DOWN:
            self.player_position += (0, 0, -2)
            self.update_chunks()


if __name__ == '__main__':
    # noinspection PyTypeChecker
    moderngl_window.run_window_config(CubeSimpleInstanced)
