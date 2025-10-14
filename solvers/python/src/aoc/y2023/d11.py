import contextlib
from typing import TYPE_CHECKING

from aoc.tooling.coordinates import Coord2d
from aoc.tooling.map import Map2d
from aoc.tooling.run import run

if TYPE_CHECKING:
    from collections.abc import Iterable


class _InputMap(Map2d):
    def __init__(self, data: Iterable[str]) -> None:
        super().__init__(list(data))


def _calculate_distance(
    coord1: Coord2d,
    coord2: Coord2d,
    expansion_indices_x: set[int],
    expansion_indices_y: set[int],
    expansion_distance: int,
) -> int:
    min_x = min(coord1.x, coord2.x)
    max_x = max(coord1.x, coord2.x)
    min_y = min(coord1.y, coord2.y)
    max_y = max(coord1.y, coord2.y)
    distance = max_x - min_x + max_y - min_y
    traveled_x_indices = set(range(min_x + 1, max_x))
    traveled_y_indices = set(range(min_y + 1, max_y))

    distance += len(traveled_x_indices & expansion_indices_x) * (expansion_distance - 1)
    distance += len(traveled_y_indices & expansion_indices_y) * (expansion_distance - 1)

    return distance


def calculate_distance_between_galaxies(input_str: str, expansion_distance: int) -> int:
    input_map = _InputMap(input_str.splitlines())
    empty_x_indices = set(range(input_map.width))
    empty_y_indices = set(range(input_map.height))
    galaxy_coords: list[Coord2d] = []
    # filter(lambda d: d[1] == "#",
    iter_ = (
        (y, x) for y, x_iter in input_map.iter_data() for x, sym in x_iter if sym == "#"
    )
    for y, x in iter_:
        with contextlib.suppress(KeyError):
            empty_x_indices.remove(x)
        with contextlib.suppress(KeyError):
            empty_y_indices.remove(y)
        galaxy_coords.append(Coord2d(y, x))

    return sum(
        _calculate_distance(
            coord, other_coord, empty_x_indices, empty_y_indices, expansion_distance
        )
        for first_ind, coord in enumerate(galaxy_coords[:-1])
        for other_coord in galaxy_coords[first_ind + 1 :]
    )


def p1(input_str: str) -> int:
    return calculate_distance_between_galaxies(input_str, 2)


def p2(input_str: str) -> int:
    return calculate_distance_between_galaxies(input_str, 1_000_000)


if __name__ == "__main__":
    run(p1, p2)
