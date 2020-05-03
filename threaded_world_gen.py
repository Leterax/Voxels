import multiprocessing
import time

import noise
from multiprocessing import Array

from _types import *


class TerrainWorker(multiprocessing.Process):
    def __init__(self, queue, output, work_counter):
        super().__init__()
        self.daemon = True

        self.queue = queue
        self.output = output
        self.work_counter = work_counter

        self.start()

    def run(self) -> None:
        # print(f"starting thread {self.pid}")
        while True:
            work_target = self.queue.get()

            chunk = self.generate_chunk_from_height_map(work_target)

            self.output[work_target] = chunk
            with self.work_counter.get_lock():
                self.work_counter.value -= 1
            # print(f"{work_target} completed.")

    @staticmethod
    def get_global_pos(local_pos: Point, chunk_pos: Point) -> Point:
        return Point(
            Chunk.size.x * chunk_pos.x + local_pos.x,
            local_pos.y,
            Chunk.size.z * chunk_pos.z + local_pos.z,
        )

    def generate_chunk_from_height_map(self, chunk_pos: Point) -> Tuple[int, List[int]]:
        blocks = []

        def height_at(x: int, z: int) -> float:
            return noise.snoise3(x * 1 / 50, z * 1 / 50, 42, octaves=6,) * 16 + 16 / 2

        # generate the actual height_map
        for z in range(Chunk.size.z):
            for x in range(Chunk.size.x):
                global_pos = self.get_global_pos(Point(x, 0, z), chunk_pos)
                height = max(int(height_at(global_pos.x, global_pos.z)), 1)
                for y in range(height):
                    blocks.extend([x, y, z, BlockType.Stone])

        non_air = len(blocks) // 4

        for _ in range(Chunk.max_blocks - len(blocks) // 4):
            blocks.extend(Block(type=BlockType.Air))

        return non_air, blocks


class ChunkManager:
    def __init__(self, worker_count):
        self.worker_count = worker_count

    def request_chunk(self, pos):
        pass

    def get_chunk(self, pos):
        pass



if __name__ == "__main__":
    manager = multiprocessing.Manager()
    chunk_dict = manager.dict()
    targets = multiprocessing.Queue()
    work_count = multiprocessing.Value("i")
    [targets.put_nowait(Point(x, 0, z)) for x in range(32) for z in range(32)]
    with work_count.get_lock():
        work_count.value = 32 * 32

    workers = [TerrainWorker(targets, chunk_dict, work_count) for _ in range(8)]

    def get_chunk(x: int, y: int, z: int) -> Tuple[int, Chunk]:
        chunk_pos = Point(x, y, z)
        if chunk_pos in chunk_dict:
            return chunk_dict[chunk_pos]

    dt = time.time()
    while work_count.value > 0:
        # time.sleep(0.01)
        get_chunk(31, 0, 31)
        print(time.time() - dt)
        dt = time.time()

    print(chunk_dict.keys())
