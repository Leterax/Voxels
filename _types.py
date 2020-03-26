from collections import namedtuple
from typing import Union
from enum import IntEnum

Number = Union[float, int]


class BlockType(IntEnum):
    Air = 0
    Stone = 1
    Edge = 3


Block = namedtuple('Block', ['x', 'y', 'z', 'type'], defaults=[0, 0, 0, BlockType.Air])
Point = namedtuple('Point', ['x', 'y', 'z'], defaults=[0, 0, 0])
