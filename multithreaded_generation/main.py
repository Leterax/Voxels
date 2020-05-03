import random
import time
from math import ceil
from pathlib import Path

import moderngl
import numpy as np
from pyrr import Matrix44
import struct
import sched
from rendering.base import CameraWindow
from moderngl_window.opengl.vao import VAO
from moderngl_window.geometry import cube
import moderngl_window as mglw
import multiprocessing

from multithreaded_generation.test import WorkerManager


class ThreadTest(CameraWindow):
    # moderngl-window settings
    gl_version = (4, 3)
    title = "main"
    resource_dir = (Path(__file__) / "../resources").absolute()
    aspect_ratio = None
    window_size = 1280, 720
    resizable = False
    samples = 4

    # app settings
    N = 5

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # load programs
        self.program = self.load_program("cube_program.glsl")

        self.program["m_proj"].write(self.camera.projection.matrix)
        self.program["m_model"].write(Matrix44.identity(dtype="f4"))

        self.cube_vao = cube()
        # create a buffer and a VAO
        #positions = np.random.random((self.N, 3)).astype("f4") * 10
        positions = np.ones((self.N, 3)).astype('f4')
        self.buffer_01 = self.ctx.buffer(positions)
        self.buffer_02 = self.ctx.buffer(positions)

        self.cube_vao.buffer(self.buffer_01, "3f/i", ["in_offset"])

        self.manager = WorkerManager(4, self.buffer_01, self.buffer_02)
        self.scheduler = sched.scheduler()
        self.add_work()
        self.request_swap_buffer()

    def request_swap_buffer(self):
        self.manager.ask_switch_buffers(self.swap_buffers)
        self.scheduler.enter(2, 1, self.request_swap_buffer)

    def swap_buffers(self):
        print("swapping buffers")
        self.buffer_02, self.buffer_01 = self.buffer_01, self.buffer_02

    def add_work(self):
        self.manager.add_item(
            (random.randint(0, self.N - 1), np.array([0, 0, 0]).astype("f4"))
        )
        self.scheduler.enter(0.1, 1, self.add_work)

    def render(self, time: float, frame_time: float) -> None:
        self.scheduler.run(blocking=False)
        self.ctx.enable_only(moderngl.CULL_FACE | moderngl.DEPTH_TEST)
        self.ctx.clear(51 / 255, 51 / 255, 51 / 255)

        self.program["m_camera"].write(self.camera.matrix)
        self.program["m_proj"].write(self.camera.projection.matrix)

        # render the vao
        #data_buff1 = self.buffer_02.read()
        #print(f"rendering {self.buffer_01}, {struct.unpack('f'*3*self.N, data_buff1)}")
        self.cube_vao.render(self.program, instances=self.N)


if __name__ == "__main__":
    # noinspection PyTypeChecker
    mglw.run_window_config(ThreadTest)
