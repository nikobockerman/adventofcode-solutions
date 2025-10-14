import itertools
import logging
from typing import TYPE_CHECKING

from attrs import define, field

from aoc.tooling.coordinates import Coord2d, X, Y
from aoc.tooling.directions import CardinalDirection as Dir
from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


@define(eq=False)
class _Path:
    corners: list[Coord2d] = field(factory=lambda: [Coord2d(Y(0), X(0))])
    _last_position: Coord2d = Coord2d(Y(0), X(0))  # noqa: RUF009
    _north_west_corner: Coord2d = Coord2d(Y(0), X(0))  # noqa: RUF009
    _south_east_corner: Coord2d = Coord2d(Y(0), X(0))  # noqa: RUF009

    @property
    def height(self) -> int:
        assert self._north_west_corner == Coord2d(Y(0), X(0))
        return self._south_east_corner.y + 1

    @property
    def width(self) -> int:
        assert self._north_west_corner == Coord2d(Y(0), X(0))
        return self._south_east_corner.x + 1

    def process(self, dir_counts: Iterable[tuple[Dir, int]]) -> None:
        for direction, count in dir_counts:
            self.add(direction, count)

    def add(self, direction: Dir, count: int) -> None:
        self._last_position = self._last_position.get_relative(direction, count)
        self.corners.append(self._last_position)

        self._north_west_corner = Coord2d(
            min(self._north_west_corner.y, self._last_position.y),
            min(self._north_west_corner.x, self._last_position.x),
        )
        self._south_east_corner = Coord2d(
            max(self._south_east_corner.y, self._last_position.y),
            max(self._south_east_corner.x, self._last_position.x),
        )
        _logger.debug("Adding %s, %s -> %s", direction, count, self._last_position)

    def normalize(self) -> None:
        assert self.corners
        assert self.corners[0] == self.corners[-1]
        del self.corners[-1]
        x_adjustment = -self._north_west_corner.x
        y_adjustment = -self._north_west_corner.y
        self.corners = [
            Coord2d(Y(coord.y + y_adjustment), X(coord.x + x_adjustment))
            for coord in self.corners
        ]
        self._north_west_corner = Coord2d(Y(0), X(0))
        self._south_east_corner = Coord2d(
            Y(self._south_east_corner.y + y_adjustment),
            X(self._south_east_corner.x + x_adjustment),
        )
        if _logger.isEnabledFor(logging.DEBUG):
            path = " -> ".join(str(coord) for coord in self.corners)
            _logger.debug("Normalized path: %s", path)


@define
class _Line:
    c1: Coord2d
    c2: Coord2d


def _find_at_row_from_sorted(line_list: Iterable[_Line], row: int) -> Iterable[_Line]:
    for line in line_list:
        if line.c1.y > row:
            break
        if row == line.c1.y:
            yield line


@define(slots=True, init=False)
class _ColumnsInsideCounter:
    flats: list[_Line]
    flats_firsts: set[X]
    flats_lasts: set[X]
    horizontals: list[_Line]
    horizontals_firsts: set[X]
    horizontals_lasts: set[X]
    crossing_vertice_columns_set: set[X]
    _columns_to_check: list[X]

    def __init__(self, segments: _PathLines, row: int) -> None:
        self.flats = list(
            _find_at_row_from_sorted(segments.flats_within_verticals, row)
        )
        self.flats_firsts = {line.c1.x for line in self.flats}
        self.flats_lasts = {line.c2.x for line in self.flats}
        self.horizontals = list(_find_at_row_from_sorted(segments.horizontals, row))
        self.horizontals_firsts = {line.c1.x for line in self.horizontals}
        self.horizontals_lasts = {line.c2.x for line in self.horizontals}

        self.crossing_vertice_columns_set = segments.get_crossing_vertice_columns_set(
            row
        )

        self._columns_to_check = list(self.crossing_vertice_columns_set)
        self._columns_to_check.extend(
            x for line in self.flats for x in (line.c1.x, line.c2.x)
        )
        self._columns_to_check.extend(
            x for line in self.horizontals for x in (line.c1.x, line.c2.x)
        )
        self._columns_to_check.sort()

    @define(slots=True)
    class _CountState:
        count: int = 0
        _x_inside_first: int | None = None
        _line_in_progress: _Line | None = None

        def _process_not_x_inside_first(
            self, info: _ColumnsInsideCounter, x: X
        ) -> None:
            assert x not in info.flats_lasts
            assert x not in info.horizontals_lasts
            self._x_inside_first = x
            if x in info.crossing_vertice_columns_set:
                pass
            elif x in info.flats_firsts:
                self._line_in_progress = next(
                    line for line in info.flats if line.c1.x == x
                )
            elif x in info.horizontals_firsts:
                self._line_in_progress = next(
                    line for line in info.horizontals if line.c1.x == x
                )

        def process_column(self, info: _ColumnsInsideCounter, x: X) -> None:
            if self._x_inside_first is None:
                self._process_not_x_inside_first(info, x)

            elif x in info.crossing_vertice_columns_set:
                assert self._line_in_progress is None
                self.count += x - self._x_inside_first + 1
                self._x_inside_first = None

            elif x in info.horizontals_firsts:
                assert self._line_in_progress is None
                self._line_in_progress = next(
                    line for line in info.horizontals if line.c1.x == x
                )

            elif x in info.horizontals_lasts:
                assert self._line_in_progress is not None
                assert self._line_in_progress.c2.x == x

                if self._line_in_progress.c1.x == self._x_inside_first:
                    self.count += x - self._x_inside_first + 1
                    self._x_inside_first = None
                self._line_in_progress = None

            elif x in info.flats_firsts:
                assert self._line_in_progress is None
                self._line_in_progress = next(
                    line for line in info.flats if line.c1.x == x
                )

            elif x in info.flats_lasts:
                assert self._line_in_progress is not None
                assert self._line_in_progress.c2.x == x

                if self._line_in_progress.c1.x != self._x_inside_first:
                    self.count += x - self._x_inside_first + 1
                    self._x_inside_first = None
                self._line_in_progress = None

    def count(self) -> int:
        state = self._CountState()
        for x in self._columns_to_check:
            state.process_column(self, x)
        return state.count


@define(init=False)
class _PathLines:
    verticals: list[_Line]
    horizontals: list[_Line]
    flats_within_verticals: list[_Line]
    height: int
    width: int

    def __init__(self, path: _Path) -> None:
        self.flats_within_verticals = []
        self.horizontals = []
        self.verticals = []
        self.height = path.height
        self.width = path.width

        prevs: list[Coord2d] = path.corners[-3:]
        for corner in path.corners:
            direction = prevs[-1].dir_to(corner)
            if direction in (Dir.N, Dir.S):
                self.verticals.append(_Line(prevs[-1], corner))
                assert len(prevs) >= 3
                prev_dir = prevs[-2].dir_to(prevs[-1])
                assert prev_dir in (Dir.E, Dir.W)
                prev2_dir = prevs[-3].dir_to(prevs[-2])
                if prev2_dir == direction:
                    self.flats_within_verticals.append(_Line(prevs[-2], prevs[-1]))
                else:
                    assert direction in (Dir.N, Dir.S)
                    assert prev2_dir == direction.opposite()
                    self.horizontals.append(_Line(prevs[-2], prevs[-1]))
            else:
                assert direction in (Dir.E, Dir.W)
            prevs = prevs[-2:]
            prevs.append(corner)

        self.optimize()

    def optimize(self) -> None:
        def _smaller_x_first(flat_list: Iterable[_Line]) -> Iterable[_Line]:
            for line in flat_list:
                if line.c1.x < line.c2.x:
                    yield line
                else:
                    yield _Line(line.c2, line.c1)

        self.flats_within_verticals = list(
            _smaller_x_first(self.flats_within_verticals)
        )
        self.flats_within_verticals.sort(key=lambda line: line.c1.y)

        self.horizontals = list(_smaller_x_first(self.horizontals))
        self.horizontals.sort(key=lambda line: line.c1.y)

        self.verticals = [
            line if line.c1.y < line.c2.y else _Line(line.c2, line.c1)
            for line in self.verticals
        ]
        self.verticals.sort(key=lambda line: line.c1.y)

    def get_crossing_vertice_columns_set(self, row: int) -> set[X]:
        crossing_vertice_columns_set = set[X]()
        for line in self.verticals:
            assert line.c1.x == line.c2.x
            if line.c1.y >= row:
                break
            if row <= line.c1.y or line.c2.y <= row:
                continue
            crossing_vertice_columns_set.add(line.c1.x)
        return crossing_vertice_columns_set


@define(init=False)
class _InsideCountGroups:
    unique_rows: dict[int, int]
    row_ranges: list[tuple[int, int, int]]

    def __init__(self, segments: _PathLines) -> None:
        self.unique_rows = {}
        self.row_ranges = []

        rows_with_flats = set[int]()
        for line in itertools.chain(
            segments.flats_within_verticals, segments.horizontals
        ):
            rows_with_flats.add(line.c1.y)
            rows_with_flats.add(line.c2.y)
        rows_with_unique_counts = set[int](
            y for line in segments.verticals for y in (line.c1.y, line.c2.y)
        )
        assert rows_with_unique_counts == rows_with_flats

        rows_to_check = list[int](rows_with_unique_counts)
        rows_to_check.sort()
        assert rows_to_check[0] == 0
        assert rows_to_check[-1] == segments.height - 1

        _logger.debug("Rows to check: %s", rows_to_check)

        prev_line_with_vertices_only: tuple[int, int] | None = None
        for y in rows_to_check:
            self.unique_rows[y] = _ColumnsInsideCounter(segments, y).count()
            if prev_line_with_vertices_only is not None:
                assert prev_line_with_vertices_only[0] < y
                assert y - 1 not in rows_with_unique_counts
                self.row_ranges.append(
                    (
                        prev_line_with_vertices_only[0],
                        y - 1,
                        prev_line_with_vertices_only[1],
                    )
                )
                prev_line_with_vertices_only = None

            if y + 1 == segments.height or y + 1 in rows_with_unique_counts:
                continue

            assert prev_line_with_vertices_only is None
            prev_line_with_vertices_only = (
                y + 1,
                _ColumnsInsideCounter(segments, y + 1).count(),
            )

        assert prev_line_with_vertices_only is None

    def total_inside_positions(self) -> int:
        return sum(self.unique_rows.values()) + sum(
            count * (y_last - y_first + 1) for y_first, y_last, count in self.row_ranges
        )


def _resolve(dir_counts: Iterable[tuple[Dir, int]]) -> int:
    path = _Path()
    path.process(dir_counts)
    path.normalize()

    segments = _PathLines(path)
    segment_groups = _InsideCountGroups(segments)
    return segment_groups.total_inside_positions()


def p1(input_str: str) -> int:
    def _direction_to_dir(direction: str) -> Dir:
        return {"U": Dir.N, "R": Dir.E, "D": Dir.S, "L": Dir.W}[direction]

    def _parse_input(lines: Iterable[str]) -> Iterable[tuple[Dir, int]]:
        for line in lines:
            direction, count, _ = line.split()
            yield _direction_to_dir(direction), int(count)

    return _resolve(_parse_input(input_str.splitlines()))


def p2(input_str: str) -> int:
    def _direction_to_dir(direction: str) -> Dir:
        return {"0": Dir.E, "1": Dir.S, "2": Dir.W, "3": Dir.N}[direction]

    def _parse_input(lines: Iterable[str]) -> Iterable[tuple[Dir, int]]:
        for line in lines:
            _, _, hex_part = line.split()
            count = int(hex_part[2:-2], base=16)
            direction = _direction_to_dir(hex_part[-2])
            yield direction, count

    return _resolve(_parse_input(input_str.splitlines()))


if __name__ == "__main__":
    run(p1, p2)
