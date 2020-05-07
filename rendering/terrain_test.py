from math import ceil
from pathlib import Path
import struct
import moderngl
import numpy as np
from moderngl_window.opengl.vao import VAO
import moderngl_window as mglw


class TerrainTest(mglw.WindowConfig):
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
        self.program = self.load_program("programs/terrain_generation.glsl")
        self.cube_emit = self.load_program(
            vertex_shader="programs/cube_geometry_vs.glsl",
            geometry_shader="programs/test_geo.glsl",
            fragment_shader="programs/cube_geometry_fs.glsl",
        )

        # self.cube_emit["world_tex"] = 0
        chunk_offsets_buffer = self.ctx.buffer(data=np.zeros((32 * 32, 3)).astype("f4"))
        chunk_offsets_buffer.bind_to_uniform_block()

        self.program["seed"] = self.seed
        self.program["scale"] = 0.1
        self.program["amplitude"] = self.chunk_size
        self.program["chunk_size"] = self.chunk_size
        self.program["offset"] = (0.0, 0.0, 0.0)

        # create a buffer and a VAO
        ids = np.arange(self.N).astype("i")
        id_template = self.ctx.buffer(ids)

        # buffers
        self.out_buffer = self.ctx.buffer(reserve=self.N * 4)
        self.geo_out_buffer = self.ctx.buffer(reserve=self.N * 24 * 4 * 3)
        self.chunk_offsets = self.ctx.buffer(
            reserve=(3 * 4) * self.render_distance ** 2
        )

        # VAO's
        self.vao = self.ctx.vertex_array(self.program, [(id_template, "i", "in_id")])
        self.geometry_vao = self.ctx.vertex_array(
            self.cube_emit, [(self.out_buffer, "i", "in_block")]
        )
        # self.vao = VAO(name="vao")
        # self.vao.buffer(id_template, "i", ["in_id"])
        #
        # self.geometry_vao = VAO(name="geo_vao")
        # self.geometry_vao.buffer(self.out_buffer, "i", ["in_block"])

        # Texture
        self.world_texture = self.ctx.texture(
            (self.N, self.render_distance ** 2), alignment=4, dtype="i4", components=1
        )

        self.q = self.ctx.query(primitives=True)
        # data = struct.unpack(f'{self.render_distance**2 * self.N}i', self.world_texture.read(alignment=4))[:self.N]

    def generate_chunk(self, pos=(0.0, 0.0, 0.0), chunk_id=0):
        self.program["offset"] = pos
        self.vao.transform(self.out_buffer, mode=moderngl.POINTS, vertices=self.N)

        self.world_texture.write(
            self.out_buffer.read(), viewport=(0, chunk_id, self.N, 1)
        )

        self.world_texture.use(0)
        with self.q:
            self.geometry_vao.render(mode=moderngl.POINTS)
        print(self.q.primitives)
        print(self.ctx.error)

    def render(self, time: float, frame_time: float) -> None:
        self.ctx.clear(51 / 255, 51 / 255, 51 / 255)
        self.generate_chunk()
        # self.wnd.close()

        # render the result
        # self.vao.render(self.program, mode=moderngl.POINTS)


if __name__ == "__main__":
    # noinspection PyTypeChecker
    mglw.run_window_config(TerrainTest)
