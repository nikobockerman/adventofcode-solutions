from dataclasses import dataclass
from typing import Literal, NewType, TypeIs

Year = NewType("Year", int)
Day = NewType("Day", int)
type Part = Literal[1, 2]
type Verbosity = Literal[0, 1, 2]


@dataclass(frozen=True)
class PartId:
    year: Year
    day: Day
    part: Part


def is_part(part: int) -> TypeIs[Part]:
    return part in (1, 2)


def is_verbosity(verbosity: int) -> TypeIs[Verbosity]:
    return verbosity in (0, 1, 2)
