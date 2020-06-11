from pathlib import Path
import moderngl
from pyrr import Matrix44

from base import CameraWindow, OrbitCameraWindow


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
    render_distance = 32
    N = int(chunk_length ** 3)
    seed = 1

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.player_pos = (0, 0)

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
        self.chunk_buffers = [
            self.ctx.buffer(reserve=4 * 3 * 12 * 6 * self.N)
            for _ in range(self.render_distance)
            for _ in range(self.render_distance)
        ]

        # VAO's
        self.terrain_generator = self.ctx.vertex_array(self.terrain_generation_program, [])
        self.geometry_vao = self.ctx.vertex_array(
            self.cube_emit_program, [(self.terrain_gen_out_buffer, "i", "in_block")]
        )
        # no indirect rendering for now.. so we just create a bunch of vaos
        self.rendering_vaos = [
            self.ctx.vertex_array(
                self.test_render_program,
                [(self.chunk_buffers[x + y * self.render_distance], "3f4 3f4", "in_normal", "in_position")],
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

        # generate some initial chunks
        self.generate_surrounding_chunks(self.player_pos)

    def generate_surrounding_chunks(self, pos):
        for y in range(self.render_distance):
            for x in range(self.render_distance):
                self.generate_chunk(x, y, (x * self.chunk_length + pos[0], 0, y * self.chunk_length + pos[1]))

    def generate_chunk(self, x, y, world_pos):
        # x,y position in 2d chunk grid to write to [0, render_distance]
        # world_pos actual world position to write to [-inf, inf]
        chunk_id = x + y * self.render_distance
        out_buffer = self.chunk_buffers[chunk_id]

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

        # print(self.camera.angle_x, self.camera.angle_y)

        # update camera values in both programs
        self.test_render_program["m_camera"].write(self.camera.matrix)
        self.test_render_program["m_proj"].write(self.camera.projection.matrix)

        for vao, num_vertices in zip(self.rendering_vaos, self.num_vertices):
            vao.render(mode=moderngl.TRIANGLES, vertices=num_vertices)

    def key_event(self, key, action, modifiers):
        super().key_event(key, action, modifiers)
        keys = self.wnd.keys
        if action == keys.ACTION_PRESS:
            if key in {keys.LEFT, keys.RIGHT, keys.UP, keys.DOWN}:
                self.player_pos = (self.player_pos[0] - int(key == keys.LEFT) * self.chunk_length, self.player_pos[1])
                self.player_pos = (self.player_pos[0] + int(key == keys.RIGHT) * self.chunk_length, self.player_pos[1])

                self.player_pos = (self.player_pos[0], self.player_pos[1] - int(key == keys.DOWN) * self.chunk_length)
                self.player_pos = (self.player_pos[0], self.player_pos[1] + int(key == keys.UP) * self.chunk_length)

                self.generate_surrounding_chunks(self.player_pos)

            if key == keys.G:
                self.ctx.wireframe = not self.ctx.wireframe
                if self.ctx.wireframe:
                    self.ctx.enable_only(moderngl.DEPTH_TEST)
                else:
                    self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)


if __name__ == "__main__":
    TerrainTest.run()
