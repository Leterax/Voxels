from pathlib import Path
import moderngl
import numpy as np
import moderngl_window as mglw
from pyrr import Matrix44

from base import CameraWindow


class TerrainTest(CameraWindow):
    # moderngl_window settings
    gl_version = (3, 3)
    title = "terrain_test"
    resource_dir = (Path(__file__).parent / "resources").resolve()
    aspect_ratio = None
    window_size = 1280, 720
    resizable = False
    samples = 4

    # app settings
    chunk_size = 16
    render_distance = 32
    N = int(chunk_size ** 3)
    seed = 1

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # load programs
        self.terrain_generation_program = self.load_program(
            "programs/terrain_generation.glsl"
        )
        self.cube_emit_program = self.load_program(
            vertex_shader="programs/cube_geometry_vs.glsl",
            geometry_shader="programs/cube_geometry_geo.glsl",
            # fragment_shader="programs/cube_geometry_fs.glsl",
        )
        self.test_render_program = self.load_program("programs/test.glsl")

        self.terrain_generation_program["seed"] = self.seed
        self.terrain_generation_program["scale"] = 0.05
        self.terrain_generation_program["amplitude"] = self.chunk_size
        self.terrain_generation_program["chunk_size"] = self.chunk_size
        self.terrain_generation_program["offset"] = (0.0, 0.0, 0.0)

        self.test_render_program["m_proj"].write(self.camera.projection.matrix)
        self.test_render_program["m_model"].write(Matrix44.identity(dtype="f4"))

        # create buffers and VAOs
        # buffers
        chunk_offsets_buffer = self.ctx.buffer(data=np.zeros((32 * 32, 3)).astype("f4"))
        chunk_offsets_buffer.bind_to_uniform_block()

        self.out_buffer = self.ctx.buffer(reserve=self.N * 4)

        self.geo_out_buffer = self.ctx.buffer(reserve=4 * 3 * 12 * 6 * self.N)

        # VAO's
        self.terrain_generator = self.ctx.vertex_array(
            self.terrain_generation_program, []
        )
        self.geometry_vao = self.ctx.vertex_array(
            self.cube_emit_program, [(self.out_buffer, "i", "in_block")]
        )
        self.test_render_vao = self.ctx.vertex_array(
            self.test_render_program,
            [(self.geo_out_buffer, "3f4 3f4", "in_normal", "in_position")],
        )

        # Texture
        self.world_texture = self.ctx.texture(
            (self.N, self.render_distance ** 2), alignment=4, dtype="i4", components=1
        )

        self.q = self.ctx.query(primitives=True)

    def generate_chunk(self, pos=(0.0, 0.0, 0.0), chunk_id=0):
        self.terrain_generation_program["offset"] = pos
        self.terrain_generator.transform(
            self.out_buffer, mode=moderngl.POINTS, vertices=self.N
        )

        self.world_texture.write(
            self.out_buffer.read(), viewport=(0, chunk_id, self.N, 1)
        )

        self.cube_emit_program["chunk_id"] = chunk_id
        self.cube_emit_program["chunk_pos"] = pos
        self.world_texture.use(0)
        with self.q:
            self.geometry_vao.transform(self.geo_out_buffer, mode=moderngl.POINTS)

    def render(self, time: float, frame_time: float) -> None:
        self.ctx.clear(51 / 255, 51 / 255, 51 / 255)
        self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        # update camera values in both programs
        self.test_render_program["m_camera"].write(self.camera.matrix)
        self.test_render_program["m_proj"].write(self.camera.projection.matrix)

        for x in range(5):
            for y in range(5):
                self.generate_chunk(pos=(self.chunk_size * x, 0, self.chunk_size * y), chunk_id=x*y)

                self.test_render_vao.render(
                    mode=moderngl.TRIANGLES, vertices=self.q.primitives * 3
                )


if __name__ == "__main__":
    # noinspection PyTypeChecker
    mglw.run_window_config(TerrainTest)
