import logging
from typing import TYPE_CHECKING, Literal, overload, override

from aoc.tooling.coordinates import Coord2d, X, Y
from aoc.tooling.directions import CardinalDirection as Dir
from aoc.tooling.map import IterDirection, Map2d
from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_logger = get_logger()


def _calculate_load(map_: Map2d) -> int:
    max_load = map_.height
    return sum(
        max_load - y
        for y, x_iter in map_.iter_data()
        for _, sym in x_iter
        if sym == "O"
    )


def _coord_rows_first(outer: Y, inner: X) -> Coord2d:
    return Coord2d(outer, inner)


def _coord_columns_first(outer: X, inner: Y) -> Coord2d:
    return Coord2d(inner, outer)


class _Roll[Outer: X | Y, Inner: X | Y]:
    def __init__(
        self,
        map_iter: Iterable[tuple[Outer, Iterable[tuple[Inner, str]]]],
        to_coord: Callable[[Outer, Inner], Coord2d],
    ) -> None:
        self._map_iter = map_iter
        self._to_coord = to_coord

    def _get_new_rock_coords(
        self,
        prev_square: Coord2d | None,
        rock_group_count: int,
        coord: Coord2d,
    ) -> Coord2d:
        raise NotImplementedError

    def set_rocks(self, lines: list[list[str]]) -> None:
        for outer, data_iter in self._map_iter:
            prev_square: Coord2d | None = None
            rock_group_count = 0
            for inner, sym in data_iter:
                if sym == ".":
                    continue
                coord = self._to_coord(outer, inner)
                if sym == "#":
                    lines[coord.y][coord.x] = "#"
                    prev_square = coord
                    rock_group_count = 0
                elif sym == "O":
                    rock_group_count += 1
                    new_rock_coord = self._get_new_rock_coords(
                        prev_square, rock_group_count, coord
                    )
                    lines[new_rock_coord.y][new_rock_coord.x] = "O"


class _RollVertical(_Roll[X, Y]):
    @overload
    def __init__(
        self,
        map_iter: Iterable[tuple[X, Iterable[tuple[Y, str]]]],
        direction: Literal[Dir.N],
    ) -> None: ...

    @overload
    def __init__(
        self,
        map_iter: Iterable[tuple[X, Iterable[tuple[Y, str]]]],
        direction: Literal[Dir.S],
        map_height: int,
    ) -> None: ...

    def __init__(
        self,
        map_iter: Iterable[tuple[X, Iterable[tuple[Y, str]]]],
        direction: Literal[Dir.N, Dir.S],
        map_height: int = 0,
    ) -> None:
        super().__init__(map_iter, _coord_columns_first)
        self._direction: Literal[Dir.N, Dir.S] = direction
        self._map_height = map_height

    @override
    def _get_new_rock_coords(
        self,
        prev_square: Coord2d | None,
        rock_group_count: int,
        coord: Coord2d,
    ) -> Coord2d:
        match self._direction:
            case Dir.N:
                y = Y((-1 if prev_square is None else prev_square.y) + rock_group_count)
            case Dir.S:
                y = Y(
                    (self._map_height if prev_square is None else prev_square.y)
                    - rock_group_count
                )
        return Coord2d(y, coord.x)


class _RollHorizontal(_Roll[Y, X]):
    @overload
    def __init__(
        self,
        map_iter: Iterable[tuple[Y, Iterable[tuple[X, str]]]],
        direction: Literal[Dir.E],
        map_width: int,
    ) -> None: ...

    @overload
    def __init__(
        self,
        map_iter: Iterable[tuple[Y, Iterable[tuple[X, str]]]],
        direction: Literal[Dir.W],
    ) -> None: ...

    def __init__(
        self,
        map_iter: Iterable[tuple[Y, Iterable[tuple[X, str]]]],
        direction: Literal[Dir.E, Dir.W],
        map_width: int = 0,
    ) -> None:
        super().__init__(map_iter, _coord_rows_first)
        self._direction: Literal[Dir.E, Dir.W] = direction
        self._map_width = map_width

    @override
    def _get_new_rock_coords(
        self,
        prev_square: Coord2d | None,
        rock_group_count: int,
        coord: Coord2d,
    ) -> Coord2d:
        match self._direction:
            case Dir.E:
                x = X(
                    (self._map_width if prev_square is None else prev_square.x)
                    - rock_group_count
                )
            case Dir.W:
                x = X((-1 if prev_square is None else prev_square.x) + rock_group_count)
        return Coord2d(coord.y, x)


def _roll_rocks(map_: Map2d, direction: Dir) -> Map2d:
    lines: list[list[str]] = [["."] * map_.width for _ in range(map_.height)]
    roller: _RollVertical | _RollHorizontal
    match direction:
        case Dir.N:
            roller = _RollVertical(
                map_.iter_data(direction=IterDirection.Columns), direction
            )
        case Dir.E:
            roller = _RollHorizontal(
                map_.iter_data_by_lines(map_.tl_y, map_.br_x, map_.br_y, map_.tl_x),
                direction,
                map_.width,
            )
        case Dir.S:
            roller = _RollVertical(
                map_.iter_data_by_columns(map_.br_y, map_.tl_x, map_.tl_y, map_.br_x),
                direction,
                map_.height,
            )
        case Dir.W:
            roller = _RollHorizontal(map_.iter_data(), direction)

    roller.set_rocks(lines)
    return Map2d(lines)


def p1(input_str: str) -> int:
    map_ = Map2d([list(line) for line in input_str.splitlines()])
    return _calculate_load(_roll_rocks(map_, Dir.N))


def _perform_spin(map_: Map2d) -> Map2d:
    for dir_ in (Dir.N, Dir.W, Dir.S, Dir.E):
        map_ = _roll_rocks(map_, dir_)
    return map_


def _get_rock_coords(map_: Map2d) -> frozenset[tuple[int, int]]:
    return frozenset(
        (x, y) for y, x_iter in map_.iter_data() for x, sym in x_iter if sym == "O"
    )


def p2(input_str: str) -> int:
    map_ = Map2d([list(line) for line in input_str.splitlines()])
    _logger.debug("Initial map:\n%s", map_)
    maps_after_spins: list[Map2d] = []
    seen_rock_coords: dict[frozenset[tuple[int, int]], int] = {}
    final_map: Map2d | None = None
    for i in range(1, 1_000_000_000 + 1):
        map_ = _perform_spin(map_)
        _logger.info("Done spinning %d", i)
        _logger.debug("Map after spin %d:\n%s", i, map_)
        rock_coords = _get_rock_coords(map_)
        seen = seen_rock_coords.get(rock_coords)
        if seen is not None:
            final_spin = seen + ((1_000_000_000 - seen) % (i - seen))
            _logger.info(
                "Found loop at %d matching spin %d -> final spin = %d",
                i,
                seen,
                final_spin,
            )
            final_map = maps_after_spins[final_spin - 1]
            break

        seen_rock_coords[rock_coords] = i
        maps_after_spins.append(map_)
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("Load on spin %d: %d", i, _calculate_load(map_))

    assert final_map is not None
    _logger.debug("Final map:\n%s", final_map)
    return _calculate_load(final_map)


if __name__ == "__main__":
    run(p1, p2)
