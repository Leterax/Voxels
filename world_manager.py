import math
import multiprocessing
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import struct
from itertools import chain
from threaded_world_gen import TerrainWorker
import noise
from queue import Empty as EmptyException

from _types import *


class World:
    saves_dir = resource_dir = (Path(__file__) / "../saves").resolve().absolute()

    def __init__(self, seed=0, generate_new=False):
        self._seed = seed
        self.amplitude = Chunk.size.y // 2
        self._generation_scale = 1 / 50

        manager = multiprocessing.Manager()
        self.chunks: Dict[
            Point, Tuple[int, Union[Chunk, ChunkRequested]]
        ] = manager.dict()

        self._generation_queue = multiprocessing.Queue()
        self.work_count = multiprocessing.Value("i")
        self.num_threads = 8
        self._workers: List[TerrainWorker] = []
        self.start_generation_workers()

    def inspect_block(
        self, x: int, y: int, z: int, _return_chunk: bool = False
    ) -> Block:
        chunk = self.get_chunk(x // Chunk.size.x, y // Chunk.size.y, z // Chunk.size.z)
        block = chunk[x % Chunk.size.x, y % Chunk.size.y, z % Chunk.size.z]
        if _return_chunk:
            return block, chunk
        else:
            return block

    def break_block(self, x: int, y: int, z: int) -> None:
        self.inspect_block(x, y, z).type = BlockType.Air

    def set_block(self, x: int, y: int, z: int, new_type: BlockType) -> None:
        self.inspect_block(x, y, z).type = new_type

    def get_chunk(self, x: int, y: int, z: int) -> Tuple[int, Chunk]:
        chunk_pos = Point(x, y, z)

        if chunk_pos in self.chunks:
            return self.chunks[chunk_pos]
        else:
            self.ask_generate_chunk(chunk_pos)
            return self.chunks[chunk_pos]

    def pull_new_chunks_block(self):
        while self.work_count.value > 0:
            time.sleep(0.25)

    def ask_generate_chunk(self, chunk_pos: Point):
        if chunk_pos in self.chunks:
            return False
        self.chunks[chunk_pos] = (-1, ChunkRequested())
        with self.work_count.get_lock():
            self.work_count.value += 1
        self._generation_queue.put(chunk_pos)
        return True

    @staticmethod
    def _get_global_pos(local_pos: Point, chunk_pos: Point) -> Point:
        return Point(
            Chunk.size.x * chunk_pos.x + local_pos.x,
            local_pos.y,
            Chunk.size.z * chunk_pos.z + local_pos.z,
        )

    def load_world(self, world_name: str) -> None:
        world_path = self.saves_dir / world_name
        config_file = world_path / (world_name + ".config")
        logging.info(
            f"Loading world '{world_name}' from '{world_path}' with config_file {config_file}"
        )
        with open(config_file, "r") as f:
            # ignore any line that starts with '#'
            lines = list(filter(lambda s: not s.startswith("#"), f.readlines()))
            # first line of the config file should be the comma separated chunk size
            Chunk.size = Point(*map(int, lines[0].split(",")))
            self._seed = int(lines[1])
            self.amplitude = int(lines[2])

        # get all chunk files
        for chunk_filename in world_path.glob("**/*.chunk"):
            # there shouldn't be any dirs in here, but just to be sure.
            if not chunk_filename.is_file():
                logging.info(
                    f"Encountered non-file type '{chunk_filename}' in save dir '{world_path}'"
                )
                continue

            chunk_position = Point(*map(int, chunk_filename.stem.split(".")))
            with open(chunk_filename, "rb") as f:
                data = Chunk.packer.unpack(f.read())
                # group data into tuples of 4
                data = list(zip(*(iter(data),) * 4))
                # convert to Block - named tuples
                blocks = list(map(lambda args: Block._make(args), data))

            self.chunks[chunk_position] = Chunk(chunk_position, blocks)

    def save_world(self, world_name: str) -> None:
        world_path = self.saves_dir / world_name
        # if the world dir doesn't exist yet, create it
        world_path.mkdir(parents=True, exist_ok=True)

        config_file = world_path / (world_name + ".config")

        logging.info(
            f"Saving world '{world_name}' to '{world_path}' with config_file '{config_file}'"
        )

        # overwrite the config file just to be sure.
        with open(config_file, "w") as f:
            config_string = (
                "# Chunk size:\n"
                f"{Chunk.size.x}, {Chunk.size.y}, {Chunk.size.z}\n"
                "# World _seed:\n"
                f"{self._seed}\n"
                "# Wold generation amplitude:\n"
                f"{self.amplitude}\n"
            )
            print(config_string, file=f, end="")

        # save all visited chunks
        for chunk_pos in self.chunks:
            self.save_chunk(world_path, chunk_pos)

    def save_chunk(self, world_path: Path, chunk_pos: Point) -> None:
        with open(str(world_path / "{0}.{1}.{2}.chunk".format(*chunk_pos)), "wb") as f:
            as_bytes = self.chunks[chunk_pos].to_bytes()
            f.write(as_bytes)

    def start_generation_workers(self):
        new_workers = [
            TerrainWorker(self._generation_queue, self.chunks, self.work_count)
            for _ in range(self.num_threads)
        ]
        for worker in self._workers:
            worker.terminate()
        self._workers = new_workers

    def _generate_chunk_from_height_map(self, chunk_pos: Point) -> None:
        blocks = []

        def height_at(x: int, z: int) -> float:
            return (
                noise.snoise3(
                    x * self._generation_scale,
                    z * self._generation_scale,
                    self._seed,
                    octaves=6,
                )
                * self.amplitude
                + self.amplitude / 2
            )

        chunk_height_map = []

        # generate the actual height_map
        for z in range(Chunk.size.z):
            sublist = []
            for x in range(Chunk.size.x):
                global_pos = self._get_global_pos(Point(z, 0, x), chunk_pos)
                sublist.append(height_at(global_pos.x, global_pos.z))

            chunk_height_map.append(sublist)

        # fill the chunk with blocks
        for y in range(Chunk.size.y):
            for z in range(Chunk.size.z):
                for x in range(Chunk.size.x):

                    if y > chunk_height_map[x][z] and y > 1:
                        blocks.append(Block(x, y, z, BlockType.Air))
                    else:
                        blocks.append(Block(x, y, z, BlockType.Stone))

        chunk = Chunk(chunk_pos, blocks)
        self.chunks[chunk_pos] = chunk

    def _generate_chunk_as_empty(self, chunk_pos: Point) -> None:
        blocks = []

        for y in range(Chunk.size.y):
            for z in range(Chunk.size.z):
                for x in range(Chunk.size.x):
                    blocks.append(Block(x, y, z, BlockType.Air))

        chunk = Chunk(chunk_pos, blocks)
        self.chunks[chunk_pos] = chunk

    @staticmethod
    def distance_to(point: Point, origin: Point):
        return math.sqrt(
            (point.x - origin.x) ** 2
            + (point.y - origin.y) ** 2
            + (point.z - origin.z) ** 2
        )

    @staticmethod
    def positions_in_radius(position: Point, radius: int):
        position = Point._make(position)
        out = []
        for z in range(-radius, radius):
            for x in range(-radius, radius):
                if World.distance_to(Point(x, 0, z), Point(0, 0, 0)) <= radius:
                    out.append(Point(x + position.x, 0, z + position.z))
        return out


def main():
    logging.basicConfig(filename="game_log.log", level=logging.DEBUG)

    world = World(generate_new=True)
    world.load_world("world_bytes")
    world.inspect_block(0, 0, 0)
    world.inspect_block(Chunk.size.x + 1, 0, 0)
    # world.save_world('world_bytes')


if __name__ == "__main__":
    main()
