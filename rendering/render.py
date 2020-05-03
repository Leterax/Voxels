"""
Renders 100 x 100 cubes using instancing.
We are using the moderngl-window specific VAO wrapper.

Each cube is animated in the vertex shader offset by gl_InstanceID
"""
from pathlib import Path
from typing import List
import time
import numpy as np
from pyrr import Matrix44
import moderngl
import moderngl_window
from moderngl_window import geometry
from moderngl_window.conf import settings
import sched
from rendering.base import CameraWindow
import world_manager
from _types import Point, Chunk, ChunkRequested


def list_difference(list1, list2):
    s = set(list2)
    return [x for x in list1 if x not in s]


class CubeSimpleInstanced(CameraWindow):
    """Renders cubes using instancing"""

    gl_version = (4, 6)
    title = "Plain Cube"
    resource_dir = (Path(__file__).parent / "resources").resolve()
    aspect_ratio = None

    # render settings
    max_render_distance = 32
    render_distance = 16

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.frame_time_log = []

        self.wnd.mouse_exclusivity = True
        self._pressed_keys = set()

        self.cube_program = self.load_program("programs/cube.glsl")
        self.player_program = self.load_program("programs/player_render.glsl")

        self.cube_program["m_proj"].write(self.camera.projection.matrix)
        self.cube_program["m_model"].write(Matrix44.identity(dtype="f4"))

        self.player_program["m_proj"].write(self.camera.projection.matrix)
        self.player_program["m_model"].write(Matrix44.identity(dtype="f4"))
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
        # We assume a maximum of 4*MAX_RENDER_DISTANCE^2 chunks will ever be in the buffer.
        # A chunk offset (vec4) is four floats (4 bytes) so 4*4 bytes. Each chunk has one of these.
        # Each indirect draw call is 5 uints (4 bytes) so 5 * 4 bytes.
        self.instanced_data_buffer = self.ctx.buffer(
            reserve=Chunk.byte_size * (4 * self.max_render_distance ** 2)
        )
        self.chunk_offsets_buffer = self.ctx.buffer(
            reserve=4 * 4 * (4 * self.max_render_distance ** 2)
        )
        self.chunk_offsets_buffer.bind_to_uniform_block()
        self.indirect_buffer = self.ctx.buffer(
            reserve=4 * 5 * (4 * self.max_render_distance ** 2)
        )

        # bind the instanced data to our cube vao. this cube will be instanced many times.
        self.cube.buffer(
            self.instanced_data_buffer, "3u1 u1/i", ["in_offset", "in_color"]
        )

        s = time.time()
        self.reload_chunks()
        print(f"generated chunks in {time.time()-s:.3f}s")
        self.clock = sched.scheduler()
        self.clock.enter(1 / 2, 1, self.handle_key_events)

    def update_chunks(self):
        # calculate all chunks in view using the current player position
        player_position_chunk_space = (
            self.camera.position[0] // Chunk.size.x,
            self.camera.position[1] // Chunk.size.y,
            self.camera.position[2] // Chunk.size.z,
        )
        current_chunks_in_view = self.world.positions_in_radius(
            player_position_chunk_space, self.render_distance
        )
        # number_of_chunks_visible = len(current_chunks_in_view)
        # calculate the difference
        chunks_nolonger_in_view = list_difference(
            self.chunks_in_view, current_chunks_in_view
        )
        chunks_now_in_view = list_difference(
            current_chunks_in_view, self.chunks_in_view
        )

        # pre-load chunks, but dont render them.
        # chunks_one_further = self.world.positions_in_radius(
        #    player_position_chunk_space, self.render_distance + 1
        # )
        # new_chunks = list_difference(chunks_one_further, chunks_now_in_view)

        # num_added = 0
        # for chunk in new_chunks:
        #    pass
        # num_added += self.world.ask_generate_chunk(chunk)

        # go through and replace the chunks no longer in view with new ones
        for index, chunk_pos in enumerate(chunks_now_in_view):
            chunk_to_replace = chunks_nolonger_in_view[index]
            index_to_replace = self.chunks_in_view.index(chunk_to_replace)
            # replace the chunk
            self.write_chunk_to_buffers(chunk_pos, index_to_replace)

    def clear_all_buffers(self):
        self.chunk_offsets_buffer.clear()
        self.indirect_buffer.clear()
        self.instanced_data_buffer.clear()

    def reload_chunks(self):
        chunk_positions = self.world.positions_in_radius(
            self.camera.position, self.render_distance
        )
        self.clear_all_buffers()
        self.chunks_in_view.clear()

        # make sure all chunks exist
        for chunk_pos in chunk_positions:
            self.world.get_chunk(*chunk_pos)

        self.world.pull_new_chunks_block()

        for index, chunk_pos in enumerate(chunk_positions):
            self.chunks_in_view.append(chunk_pos)
            self.write_chunk_to_buffers(chunk_pos, index)

    def write_chunk_to_buffers(self, chunk_pos, index):
        s = time.time()
        non_air_count, chunk = self.world.get_chunk(*chunk_pos)
        if isinstance(chunk, ChunkRequested):
            # print("chunk missing")
            return

        self.chunks_in_view.pop(index)
        self.chunks_in_view.insert(index, chunk_pos)
        print(time.time()-s)

        block_bytes, num_blocks = Chunk.to_buffer_bytes(non_air_count, chunk)

        indirect_data = np.array(
            [36, num_blocks, 0, index * Chunk.max_blocks, 0], dtype=np.uint
        )
        self.indirect_buffer.write(indirect_data, offset=20 * index)

        self.instanced_data_buffer.write(block_bytes, offset=index * Chunk.byte_size)

        chunk_offset_data = np.array([*Chunk.get_global_pos(chunk_pos), 0], dtype="f4")
        self.chunk_offsets_buffer.write(chunk_offset_data, offset=4 * 4 * index)

    def render(self, elapsed: float, delta_time: float):
        if not delta_time < 0:
            self.frame_time_log.append((elapsed, delta_time))
        # process sched events
        self.clock.run(blocking=False)

        self.ctx.enable_only(moderngl.CULL_FACE | moderngl.DEPTH_TEST)

        # update camera values in both programs
        self.cube_program["m_camera"].write(self.camera.matrix)
        self.cube_program["m_proj"].write(self.camera.projection.matrix)

        # self.player_program["m_camera"].write(self.camera.matrix)
        # self.player_program["m_proj"].write(self.camera.projection.matrix)
        # self.player_program["position"].write(self.player_position.astype("f4"))

        # render all chunks in one draw call
        self.cube.render_indirect(self.cube_program, self.indirect_buffer)

        # render the player
        # self.player.render(self.player_program)

    def key_event(self, key, action, modifiers):
        super().key_event(key, action, modifiers)

        keys = self.wnd.keys
        if action == keys.ACTION_PRESS:
            self._pressed_keys.add(key)
        if action == keys.ACTION_RELEASE:
            self._pressed_keys.remove(key)

    def handle_key_events(self, *args):
        keys = self.wnd.keys
        self.update_chunks()
        # if keys.LEFT in self._pressed_keys:
        #     self.player_position += (2, 0, 0)
        #     self.update_chunks()
        # if keys.RIGHT in self._pressed_keys:
        #     self.player_position += (-2, 0, 0)
        #     self.update_chunks()
        # if keys.UP in self._pressed_keys:
        #     self.player_position += (0, 0, 2)
        #     self.update_chunks()
        # if keys.DOWN in self._pressed_keys:
        #     self.player_position += (0, 0, -2)
        #     self.update_chunks()

        self.clock.enter(1 / 2, 1, self.handle_key_events)

    def close(self):
        print("here")
        import matplotlib.pyplot as plt

        x, y = zip(*self.frame_time_log)
        print(y[:25])
        plt.scatter(x, y)
        plt.show()


if __name__ == "__main__":
    # noinspection PyTypeChecker
    moderngl_window.run_window_config(CubeSimpleInstanced)
