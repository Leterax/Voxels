from dataclasses import dataclass
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import csv
import struct
from itertools import chain

import noise

from _types import *


def clamp(minimum: Number, x: Number, maximum: Number) -> Number:
    return max(minimum, min(x, maximum))


@dataclass
class Chunk:
    chunk_position: Point
    blocks: List[Block]
    size: Point = Point(16, 16, 16)

    max_blocks: int = size.x * size.y * size.z
    _packer: struct.Struct = struct.Struct('<' + 'BBBB' * size.x * size.y * size.z)
    block_size_bytes: int = struct.calcsize('<BBBB')
    byte_size: int = _packer.size

    def __getitem__(self, pos) -> Block:
        return self.blocks[self.get_index(*pos)]

    def get_global_pos(self) -> Point:
        return Point(self.chunk_position.x * self.size.x,
                     self.chunk_position.y * self.size.y,
                     self.chunk_position.z * self.size.z)

    @staticmethod
    def get_pos(index: int) -> Tuple[int, int, int]:
        y = index // (Chunk.size.x * Chunk.size.z)
        index -= (y * Chunk.size.x * Chunk.size.z)
        z = index // Chunk.size.x
        index -= (z * Chunk.size.z)
        x = index % Chunk.size.y
        return x, y, z

    @staticmethod
    def get_index(x: int, y: int, z: int) -> int:
        x, y, z = clamp(0, x, Chunk.size.x - 1), clamp(0, y, Chunk.size.y - 1), clamp(0, z, Chunk.size.z - 1)
        return Chunk.size.z * Chunk.size.x * y + Chunk.size.z * z + x

    def to_bytes(self) -> Tuple[bytes, int]:
        """Convert all non-air blocks to a bytes object and return how many blocks that is."""
        sorted_list = sorted(self.blocks, key=lambda block: block.type, reverse=True)
        flattened = chain(*sorted_list)
        non_air_count = Chunk.num_non_air_blocks(sorted_list)
        return Chunk._packer.pack(*flattened)[:Chunk.block_size_bytes*non_air_count], non_air_count

    @staticmethod
    def num_non_air_blocks(blocks) -> int:
        for i, block in enumerate(blocks):
            if block.type == BlockType.Air:
                return i

    def __hash__(self):
        return hash(self.chunk_position)


class World:
    saves_dir = resource_dir = (Path(__file__) / '../saves').resolve().absolute()

    def __init__(self, seed=0, generate_new=False):
        self._seed = seed
        self.amplitude = Chunk.size.y // 2
        self.chunks: Dict[Point, Chunk] = {}

        self._generate_chunk = self._generate_chunk_from_height_map if generate_new else self._generate_chunk_as_empty

    def inspect_block(self, x: int, y: int, z: int, _return_chunk: bool = False) -> Block:
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

    def get_chunk(self, x: int, y: int, z: int) -> Chunk:
        chunk_pos = Point(x, y, z)

        if chunk_pos in self.chunks:
            return self.chunks[chunk_pos]
        else:
            self._generate_chunk(chunk_pos)
            return self.chunks[chunk_pos]

    @staticmethod
    def _get_global_pos(local_pos: Point, chunk_pos: Point) -> Point:
        return Point(Chunk.size.x * chunk_pos.x + local_pos.x,
                     local_pos.y,
                     Chunk.size.z * chunk_pos.z + local_pos.z)

    def load_world(self, world_name: str) -> None:
        world_path = self.saves_dir / world_name
        config_file = world_path / (world_name + '.config')
        logging.info(f"Loading world '{world_name}' from '{world_path}' with config_file {config_file}")
        with open(config_file, 'r') as f:
            # ignore any line that starts with '#'
            lines = list(filter(lambda s: not s.startswith('#'), f.readlines()))
            # first line of the config file should be the comma separated chunk size
            Chunk.size = Point(*map(int, lines[0].split(',')))
            self._seed = int(lines[1])
            self.amplitude = int(lines[2])

        # get all chunk files
        for chunk_filename in world_path.glob("**/*.chunk"):
            # there shouldn't be any dirs in here, but just to be sure.
            if not chunk_filename.is_file():
                logging.info(f"Encountered non-file type '{chunk_filename}' in save dir '{world_path}'")
                continue

            chunk_position = Point(*map(int, chunk_filename.stem.split('.')))
            blocks = [*map(lambda args: Block._make(map(int, args)), csv.reader(open(str(chunk_filename), 'r')))]

            self.chunks[chunk_position] = Chunk(chunk_position, blocks)

    def save_world(self, world_name: str) -> None:
        world_path = self.saves_dir / world_name
        # if the world dir doesn't exist yet, create it
        world_path.mkdir(parents=True, exist_ok=True)

        config_file = world_path / (world_name + '.config')

        logging.info(f"Saving world '{world_name}' to '{world_path}' with config_file '{config_file}'")

        # overwrite the config file just to be sure.
        with open(config_file, 'w') as f:
            config_string = ("# Chunk size:\n"
                             f"{Chunk.size.x}, {Chunk.size.y}, {Chunk.size.z}\n"
                             "# World _seed:\n"
                             f"{self._seed}\n"
                             "# Wold generation amplitude:\n"
                             f"{self.amplitude}\n"
                             )
            print(config_string, file=f, end='')

        # save all visited chunks
        for chunk_pos in self.chunks:
            self.save_chunk(world_path, chunk_pos)

    def save_chunk(self, world_path: Path, chunk_pos: Point) -> None:
        with open(str(world_path / "{0}.{1}.{2}.chunk".format(*chunk_pos)), 'w') as f:
            blocks = self.chunks[chunk_pos].blocks
            block_string = '\n'.join("{0}, {1}, {2}, {3}".format(*block) for block in blocks)
            print(block_string, file=f)

    def _generate_chunk_from_height_map(self, chunk_pos: Point) -> None:
        blocks = []

        def height_at(x: int, z: int) -> float:
            return noise.snoise3(x / 20, z / 20, self._seed,
                                 octaves=6) * self.amplitude + self.amplitude / 2

        chunk_height_map = []

        # generate the actual height_map
        for z in range(Chunk.size.z):
            sublist = []
            for x in range(Chunk.size.x):
                global_pos = self._get_global_pos(Point(x, 0, z), chunk_pos)
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
        return abs(origin.x - point.x) + abs(origin.y - point.y) + abs(origin.z - point.z)

    @staticmethod
    def positions_in_radius(position: Point, radius: int):
        out = []
        for z in range(-radius // 2, radius // 2):
            for x in range(-radius // 2, radius // 2):
                if World.distance_to(Point(x, 0, z), Point(0, 0, 0)) <= radius:
                    out.append(Point(x + position.x, position.y, z + position.z))
        return out

    # ### FLOODFILLING ###
    #
    # @staticmethod
    # def distance_to(point: Point, origin: Point):
    #     return abs(origin.x - point.x) + abs(origin.y - point.y) + abs(origin.z - point.z)
    #
    # def get_neighbours(self, block: Block) -> List[Tuple[Block, Chunk]]:
    #     neighbour_offsets = ((-1, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    #     neighbours = []
    #     for x, y, z in neighbour_offsets:
    #         neighbour_position = Point(block.x + x, block.y + y, block.z + z)
    #         b, chunk = self.inspect_block(*neighbour_position, _return_chunk=True)
    #         neighbours.append((b, chunk))
    #
    #     return neighbours
    #
    # def flood_fill(self, origin: Tuple[Block, Chunk], max_distance: int):
    #     origin_pos = self._get_global_pos(origin[0], origin[1].chunk_position)
    #
    #     looked_at = set()
    #     open_queue = deque()
    #     edge: Set[Block] = set()
    #
    #     open_queue.append(origin)
    #     while len(open_queue) > 0:
    #         # get the next block to look at
    #         current_block, current_chunk = open_queue.pop()
    #         current_pos = self._get_global_pos(current_block, current_chunk.chunk_position)
    #         if current_pos in looked_at:
    #             continue
    #         else:
    #             looked_at.add(current_pos)
    #
    #         # ignore the block if its outside of our viewing distance
    #         if self.distance_to(current_pos, origin_pos) > max_distance:
    #             print(f"distance: {self.distance_to(current_pos, origin_pos)} is too far")
    #             edge.add((Block(*current_block[:-1], BlockType.Edge), current_chunk))
    #             continue
    #
    #         if current_block.type == BlockType.Air:
    #             # add neighbours to open list
    #             open_queue.extend(self.get_neighbours(current_pos))
    #         else:
    #             # add self to the edge list
    #             edge.add((current_block, current_chunk))
    #
    #     return edge, open_queue


def main():
    logging.basicConfig(filename="game_log.log", level=logging.DEBUG)

    world = World(generate_new=True)
    world.inspect_block(0, 0, 0)
    world.inspect_block(Chunk.size.x + 1, 0, 0)
    world.save_world('world_02')


if __name__ == "__main__":
    main()
