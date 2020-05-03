from collections import namedtuple
from typing import Union
from enum import IntEnum
import struct
from itertools import chain
from dataclasses import dataclass

from typing import Dict, List, Tuple

Number = Union[float, int]


class BlockType(IntEnum):
    Air = 0
    Stone = 1


Block = namedtuple("Block", ["x", "y", "z", "type"], defaults=[0, 0, 0, BlockType.Air])
Point = namedtuple("Point", ["x", "y", "z"], defaults=[0, 0, 0])


def clamp(minimum: Number, x: Number, maximum: Number) -> Number:
    """Clamp a number between two other numbers."""
    return max(minimum, min(x, maximum))


class ChunkRequested:
    def __getattr__(self, item):
        raise AttributeError("Chunk has been requested, but not completed generation.")


@dataclass(frozen=True)
class Chunk:
    """Class to keep track of a chunk."""

    # chunk position. this is in chunk space, so a increase in one means one chunk over.
    chunk_position: Point
    # all blocks contained in this chunk
    blocks: List[Block]
    # size of the chunk, this should stay constant
    size: Point = Point(16, 32, 16)

    max_blocks: int = size.x * size.y * size.z
    # packer for packing chunk data into bytes
    packer: struct.Struct = struct.Struct("<" + "BBBB " * size.x * size.y * size.z)
    block_size_bytes: int = struct.calcsize("<BBBB")
    byte_size: int = packer.size

    def __getitem__(self, pos) -> Block:
        """Get the block at `pos`."""
        return self.blocks[self.get_index(*pos)]

    @staticmethod
    def get_global_pos(chunk_position) -> Point:
        """Get the global position of this chunk."""
        return Point(
            chunk_position.x * Chunk.size.x,
            chunk_position.y * Chunk.size.y,
            chunk_position.z * Chunk.size.z,
        )

    @staticmethod
    def get_pos(index: int) -> Tuple[int, int, int]:
        """Blocks are stored in a 1D array, calculate the position of the block at `index`."""
        y = index // (Chunk.size.x * Chunk.size.z)
        index -= y * Chunk.size.x * Chunk.size.z
        z = index // Chunk.size.x
        index -= z * Chunk.size.z
        x = index % Chunk.size.y
        return x, y, z

    @staticmethod
    def get_index(x: int, y: int, z: int) -> int:
        """Blocks are stored in a 1D array, calculate the index of the block at `position`."""
        x, y, z = (
            clamp(0, x, Chunk.size.x - 1),
            clamp(0, y, Chunk.size.y - 1),
            clamp(0, z, Chunk.size.z - 1),
        )
        return Chunk.size.z * Chunk.size.x * y + Chunk.size.z * z + x

    # @staticmethod
    # def to_buffer_bytes(blocks) -> Tuple[bytes, int]:
    #     """Convert all non-air blocks to a bytes object and return how many blocks that is."""
    #     sorted_list = sorted(blocks, key=lambda block: block.type, reverse=True)
    #     flattened = chain(*sorted_list)
    #     non_air_count = Chunk.num_non_air_blocks(sorted_list)
    #     return (
    #         Chunk.packer.pack(*flattened)[: Chunk.block_size_bytes * non_air_count],
    #         non_air_count,
    #     )

    @staticmethod
    def to_buffer_bytes(non_air_count, blocks) -> Tuple[bytes, int]:
        """Convert all non-air blocks to a bytes object and return how many blocks that is."""

        return (
            Chunk.packer.pack(*blocks)[: Chunk.block_size_bytes * non_air_count],
            non_air_count,
        )

    @staticmethod
    def to_bytes(blocks) -> bytes:
        """Convert the entire chunk to bytes."""
        flattened = chain(*blocks)
        return Chunk.packer.pack(*flattened)

    @staticmethod
    def num_non_air_blocks(blocks) -> int:
        """calculate how many non-air blocks are in the sorted list `blocks`"""
        for i, block in enumerate(blocks):
            if block.type == BlockType.Air:
                return i

    def __hash__(self):
        """Calculate the hash of this chunk based on its position."""
        return hash(self.chunk_position)

    def __repr__(self):
        return f"<Chunk {self.chunk_position} | {self.num_non_air_blocks(self.blocks)} non air blocks>"
