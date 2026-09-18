from dataclasses import dataclass
from typing import Literal, NewType, TypeIs, get_args

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
    return part in get_args(Part.evaluate_value())  # type: ignore [call-arg]


def is_verbosity(verbosity: int) -> TypeIs[Verbosity]:
    return verbosity in get_args(Verbosity.evaluate_value())  # type: ignore [call-arg]
