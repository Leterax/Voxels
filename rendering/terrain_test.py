from pathlib import Path
import moderngl
import numpy as np
from pyrr import Matrix44
from time import perf_counter_ns

from base import CameraWindow, OrbitCameraWindow


class Timer:
    def __init__(self):
        self.history = []
        self.start = 0

    def __enter__(self):
        self.start = perf_counter_ns()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.history.append(perf_counter_ns() - self.start)

    def avg_time(self):
        return sum(self.history) / len(self.history)

    def reset(self):
        self.history = []


# class TerrainTest(OrbitCameraWindow):
class TerrainTest(CameraWindow):
    # moderngl_window settings
    gl_version = (3, 3)
    title = "terrain_test"
    resource_dir = (Path(__file__).parent / "resources").resolve()
    aspect_ratio = None
    window_size = 1280, 720
    resizable = True
    samples = 4
    clear_color = 51 / 255, 51 / 255, 51 / 255

    # app settings
    chunk_length = 16
    render_distance = 65
    N = int(chunk_length ** 3)
    seed = 1

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.player_pos = (
            self.chunk_length * (self.render_distance - 1) / 2,
            self.chunk_length * (self.render_distance - 1) / 2,
        )
        self.last_camera_position = np.array([self.chunk_length * (self.render_distance - 1) / 2, 0.])
        # load programs
        self.terrain_generation_program = self.load_program("programs/terrain_generation.glsl")
        self.cube_emit_program = self.load_program(
            vertex_shader="programs/cube_geometry_vs.glsl", geometry_shader="programs/cube_geometry_geo.glsl",
        )

        self.test_render_program = self.load_program("programs/test.glsl")

        self.cube_emit_program["chunk_length"] = self.chunk_length

        self.terrain_generation_program["seed"] = self.seed
        self.terrain_generation_program["scale"] = 0.01
        self.terrain_generation_program["amplitude"] = self.chunk_length
        self.terrain_generation_program["chunk_length"] = self.chunk_length
        self.terrain_generation_program["offset"] = (0.0, 0.0, 0.0)

        self.test_render_program["m_proj"].write(self.camera.projection.matrix)
        self.test_render_program["m_model"].write(Matrix44.identity(dtype="f4"))

        # create buffers and VAOs
        self.terrain_gen_out_buffer = self.ctx.buffer(reserve=self.N * 4)

        # since we dont use indirect rendering we need one buffer per vao, so lets create them
        chunk_buffers = []
        self.chunk_ids = dict()
        for x in range(self.render_distance):
            for y in range(self.render_distance):
                buf = self.ctx.buffer(reserve=int(4 * 3 * 12 * 6 * self.N * 0.07))
                chunk_buffers.append(buf)
                self.chunk_ids[buf.glo] = x + y * self.render_distance
        self.chunk_buffers = np.array(chunk_buffers).reshape(self.render_distance, self.render_distance)

        # VAO's
        self.terrain_generator = self.ctx.vertex_array(self.terrain_generation_program, [])
        self.geometry_vao = self.ctx.vertex_array(
            self.cube_emit_program, [(self.terrain_gen_out_buffer, "i", "in_block")]
        )
        # no indirect rendering for now.. so we just create a bunch of vaos
        self.rendering_vaos = [
            self.ctx.vertex_array(
                self.test_render_program, [(self.chunk_buffers[x, y], "3f4 3f4", "in_normal", "in_position")],
            )
            for y in range(self.render_distance)
            for x in range(self.render_distance)
        ]
        # number of vertices for each vao/buffer
        self.num_vertices = [0] * self.render_distance ** 2

        # Texture
        self.world_texture = self.ctx.texture(
            (self.N, self.render_distance ** 2), alignment=4, dtype="i4", components=1
        )

        self.q = self.ctx.query(primitives=True)
        self.timer = Timer()
        # generate some initial chunks
        self.generate_surrounding_chunks(self.player_pos)

        print(max(self.num_vertices))

    def update_surrounding_chunks(self, x_offset, y_offset, player_pos):
        def unique_elements(l):
            unique = []
            for element in l:
                if element not in unique:
                    unique.append(element)
            return unique

        player_pos = (
            (player_pos[0] // self.chunk_length) * self.chunk_length,
            (player_pos[1] // self.chunk_length) * self.chunk_length,
        )
        buffers_to_replace = []
        world_positions = []

        if x_offset == 1:  # shift to the right
            self.chunk_buffers = np.roll(self.chunk_buffers, 2, axis=1)
            buffers_to_replace.extend(self.chunk_buffers[:, -1])

            world_positions.extend(
                [
                    (
                        player_pos[0] + int((self.render_distance - 1) / 2) * self.chunk_length,
                        0.0,
                        player_pos[1] + self.chunk_length * y - int((self.render_distance - 1) / 2 * self.chunk_length),
                    )
                    for y in range(self.render_distance)
                ]
            )

        if x_offset == -1:  # shift to the left
            self.chunk_buffers = np.roll(self.chunk_buffers, -2, axis=1)
            buffers_to_replace.extend(self.chunk_buffers[:, 0])

            world_positions.extend(
                [
                    (
                        player_pos[0] - int((self.render_distance - 1) / 2) * self.chunk_length,
                        0.0,
                        player_pos[1] + self.chunk_length * y - int((self.render_distance - 1) / 2 * self.chunk_length),
                    )
                    for y in range(self.render_distance)
                ]
            )

        if y_offset == -1:  # shift down
            self.chunk_buffers = np.roll(self.chunk_buffers, -1, axis=0)
            buffers_to_replace.extend(self.chunk_buffers[-1, :])

            world_positions.extend(
                [
                    (
                        player_pos[0] + self.chunk_length * y - int((self.render_distance - 1) / 2 * self.chunk_length),
                        0.0,
                        player_pos[1] - int((self.render_distance - 1) / 2) * self.chunk_length,
                    )
                    for y in range(self.render_distance)
                ]
            )

        if y_offset == 1:  # shift up
            self.chunk_buffers = np.roll(self.chunk_buffers, 1, axis=0)
            buffers_to_replace.extend(self.chunk_buffers[0, :])

            world_positions.extend(
                [
                    (
                        player_pos[0] + self.chunk_length * y - int((self.render_distance - 1) / 2 * self.chunk_length),
                        0.0,
                        player_pos[1] + int((self.render_distance - 1) / 2) * self.chunk_length,
                    )
                    for y in range(self.render_distance)
                ]
            )

        buffers_to_replace = unique_elements(buffers_to_replace)
        world_positions = unique_elements(world_positions)

        for world_pos, buffer in zip(world_positions, buffers_to_replace):
            # print(f"generating chunk {buffer} @ {world_pos}")
            self.generate_chunk(buffer, world_pos)
        # print("done shifting")

    def generate_surrounding_chunks(self, pos):
        for y in range(self.render_distance):
            for x in range(self.render_distance):
                self.generate_chunk(
                    self.chunk_buffers[-y, -x],
                    (
                        (x - self.render_distance // 2) * self.chunk_length + pos[0],
                        0,
                        (y - self.render_distance // 2) * self.chunk_length + pos[1],
                    ),
                )

    def generate_chunk(self, out_buffer, world_pos):
        # x,y position in 2d chunk grid to write to [0, render_distance]
        # world_pos actual world position to write to [-inf, inf]
        # chunk_id = x + y * self.render_distance
        # out_buffer = self.chunk_buffers[chunk_id]
        chunk_id = self.chunk_ids[out_buffer.glo]

        self.terrain_generation_program["offset"] = world_pos
        self.terrain_generator.transform(self.terrain_gen_out_buffer, mode=moderngl.POINTS, vertices=self.N)

        self.world_texture.write(self.terrain_gen_out_buffer.read(), viewport=(0, chunk_id, self.N, 1))

        self.cube_emit_program["chunk_id"] = chunk_id
        self.cube_emit_program["chunk_pos"] = world_pos
        self.world_texture.use(0)
        with self.q:
            self.geometry_vao.transform(out_buffer, mode=moderngl.POINTS)

        self.num_vertices[chunk_id] = self.q.primitives * 3
        # print(f"{chunk_id}: {self.rendering_vaos[chunk_id]}, {out_buffer} @ {self.q.primitives  * 3}")

    def render(self, time: float, frame_time: float) -> None:
        self.ctx.enable_only(moderngl.DEPTH_TEST)

        camera_chunk = np.array([self.camera.position[0], self.camera.position[-1]])
        chunk_delta = self.last_camera_position // self.chunk_length - camera_chunk // self.chunk_length
        if np.linalg.norm(chunk_delta) >= 1:
            self.last_camera_position = camera_chunk
            self.update_surrounding_chunks(-chunk_delta[0], -chunk_delta[1], self.last_camera_position)

        # update camera values in both programs
        self.test_render_program["m_camera"].write(self.camera.matrix)
        self.test_render_program["m_proj"].write(self.camera.projection.matrix)

        for vao, num_vertices in zip(self.rendering_vaos, self.num_vertices):
            vao.render(mode=moderngl.TRIANGLES, vertices=num_vertices)

    def close(self):
        print(f"avg: {self.timer.avg_time()}")

    def key_event(self, key, action, modifiers):
        super().key_event(key, action, modifiers)
        keys = self.wnd.keys
        if action == keys.ACTION_PRESS:
            if key in {keys.LEFT, keys.RIGHT, keys.UP, keys.DOWN}:
                x_offset = -int(key == keys.LEFT) + int(key == keys.RIGHT)
                y_offset = -int(key == keys.DOWN) + int(key == keys.UP)
                self.player_pos = (self.player_pos[0] - int(key == keys.LEFT) * self.chunk_length, self.player_pos[1])
                self.player_pos = (self.player_pos[0] + int(key == keys.RIGHT) * self.chunk_length, self.player_pos[1])

                self.player_pos = (self.player_pos[0], self.player_pos[1] - int(key == keys.DOWN) * self.chunk_length)
                self.player_pos = (self.player_pos[0], self.player_pos[1] + int(key == keys.UP) * self.chunk_length)

                # print(self.player_pos, x_offset, y_offset)
                self.update_surrounding_chunks(x_offset, y_offset, self.player_pos)

            if key == keys.G:
                self.ctx.wireframe = not self.ctx.wireframe
                if self.ctx.wireframe:
                    self.ctx.enable_only(moderngl.DEPTH_TEST)
                else:
                    self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)


if __name__ == "__main__":
    TerrainTest.run()
