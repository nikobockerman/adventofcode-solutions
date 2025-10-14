import itertools
import math
from typing import TYPE_CHECKING

from attrs import define

from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


def _parse_input(lines: list[str]) -> tuple[str, list[tuple[str, tuple[str, str]]]]:
    directions = lines[0]

    turns: list[tuple[str, tuple[str, str]]] = []
    for line in lines[2:]:
        location, turns_str = line.split(" = ")
        turns_str = turns_str.strip("()")
        left, right = turns_str.split(", ")
        turns.append((location, (left, right)))
    return directions, turns


def p1(input_str: str) -> int:
    directions, turns_list = _parse_input(input_str.splitlines())

    turns = dict(turns_list)

    turns_to_take = itertools.cycle(directions)
    turn_count = 0
    location = "AAA"
    while location != "ZZZ":
        turn_to_take = next(turns_to_take)
        turn_count += 1
        location = turns[location][0 if turn_to_take == "L" else 1]

    return turn_count


@define
class _MapData:
    map_nodes: dict[int, tuple[int, int]]
    start_locations: list[int]
    first_end_location: int

    def is_end_location(self, location: int) -> bool:
        return location >= self.first_end_location


def _create_map_data(map_nodes_list: list[tuple[str, tuple[str, str]]]) -> _MapData:
    map_nodes_list = sorted(map_nodes_list, key=lambda x: x[0][2])
    locations_mapping = {
        location: index for index, (location, _) in enumerate(map_nodes_list)
    }
    _logger.debug("locations_mapping=%s", locations_mapping)

    def get_start_locations() -> Iterable[int]:
        for location, _ in map_nodes_list:
            if location[2] == "A":
                yield locations_mapping[location]
                continue
            break

    start_locations = list(get_start_locations())

    assert len(start_locations) == len(
        [loc for loc, _ in map_nodes_list if loc[2] == "Z"]
    )
    assert len(start_locations) - 1 == max(start_locations)

    map_nodes = {
        locations_mapping[location]: (
            locations_mapping[left],
            locations_mapping[right],
        )
        for location, (left, right) in map_nodes_list
    }

    def get_first_end_location() -> int:
        prev_location = map_nodes_list[-1][0]
        for location, _ in reversed(map_nodes_list):
            if location[2] == "Z":
                prev_location = location
                continue
            break
        return locations_mapping[prev_location]

    first_end_location = get_first_end_location()

    return _MapData(map_nodes, start_locations, first_end_location)


def _get_verified_loop_length(
    path_before_loop: list[int],
    loop_path: list[int],
    map_data: _MapData,
) -> int:
    def get_index_of_last_end_location(path: list[int]) -> int:
        return next(
            (
                turn_count
                for turn_count, loc in reversed(list(enumerate(path)))
                if map_data.is_end_location(loc)
            )
        )

    assert not any(map_data.is_end_location(loc) for loc in path_before_loop)
    assert len(path_before_loop) + get_index_of_last_end_location(loop_path) == len(
        loop_path
    )

    return len(loop_path)


def _resolve_loop_length(
    start_location: int, directions: str, map_data: _MapData
) -> int:
    directions_len = len(directions)
    turns = itertools.cycle(directions)
    visit_keys: set[tuple[int, int]] = set()
    path: list[int] = [start_location]

    # Find loop: when second time in same location at same direction
    # same direction means index inside directions string, not the direction value (L/R)
    while True:
        visit_key = (path[-1], (len(visit_keys)) % directions_len)
        if visit_key in visit_keys:
            # Loop found
            break

        visit_keys.add(visit_key)

        turn_to_take = next(turns)
        cur_location = map_data.map_nodes[path[-1]][0 if turn_to_take == "L" else 1]
        path.append(cur_location)

    loop_start_ind = path.index(path[-1])

    path_before_loop = path[:loop_start_ind]
    loop_path = path[loop_start_ind:-1]

    return _get_verified_loop_length(path_before_loop, loop_path, map_data)


def p2(input_str: str) -> int:
    directions, map_nodes_list = _parse_input(input_str.splitlines())
    _logger.debug("directions=%s", directions)
    _logger.debug("map_nodes_list=%s", map_nodes_list)

    map_data = _create_map_data(map_nodes_list)
    _logger.debug("map_data=%s", map_data)

    path_lengths = [
        _resolve_loop_length(start_location, directions, map_data)
        for start_location in map_data.start_locations
    ]

    _logger.info("path_lengths=%s", path_lengths)

    return math.lcm(*path_lengths)


if __name__ == "__main__":
    run(p1, p2)
