from random import randint
from enum import Enum

class Colors(Enum):
    Red = 0
    Green = 1
    Blue = 2
    Orange = 3
    Purple = 4

grid: list[list[Colors|int]] = [[randint(0, 5) for _ in range(6)] for __ in range(6)]
