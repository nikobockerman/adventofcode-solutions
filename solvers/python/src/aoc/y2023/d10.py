import enum
import itertools
import logging
from typing import TYPE_CHECKING

from attrs import define, field

from aoc.tooling.coordinates import Coord2d, X, Y
from aoc.tooling.directions import CardinalDirection as Dir
from aoc.tooling.directions import CardinalDirectionsAll
from aoc.tooling.map import Map2d
from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

_logger = get_logger()


class _Inside(enum.Enum):
    Inside = enum.auto()
    Outside = enum.auto()
    InPath = enum.auto()
    Unknown = enum.auto()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


@define
class _Pipe:
    coord: Coord2d
    symbol: str
    inside: _Inside = _Inside.Unknown

    def __hash__(self) -> int:
        return hash(self.coord)


_symbols_open_to_north = "|JLS"
_symbols_open_to_east = "-FLS"
_symbols_open_to_south = "|F7S"
_symbols_open_to_west = "-J7S"


@define(init=False)
class _MapData(Map2d[_Pipe]):
    start: _Pipe

    def __init__(self, input_data: list[str]) -> None:
        data: list[list[_Pipe]] = []
        start: _Pipe | None = None
        for y, row in enumerate(input_data):
            y_pipes: list[_Pipe] = []
            data.append(y_pipes)
            for x, symbol in enumerate(row):
                pipe = _Pipe(Coord2d(Y(y), X(x)), symbol)
                if symbol == "S":
                    assert start is None
                    start = pipe
                y_pipes.append(pipe)
        super().__init__(data)
        assert start is not None
        self.start = start


def _get_adjoin_pipes_on_path(pipe: _Pipe, map_data: _MapData) -> Iterable[_Pipe]:
    east_adjoin = pipe.coord.adjoin(Dir.E)
    east = map_data.get_or_default(east_adjoin.y, east_adjoin.x, None)
    if (
        east
        and pipe.symbol in _symbols_open_to_east
        and east.symbol in _symbols_open_to_west
    ):
        yield east

    south_adjoin = pipe.coord.adjoin(Dir.S)
    south = map_data.get_or_default(south_adjoin.y, south_adjoin.x, None)
    if (
        south
        and pipe.symbol in _symbols_open_to_south
        and south.symbol in _symbols_open_to_north
    ):
        yield south

    west_adjoin = pipe.coord.adjoin(Dir.W)
    west = map_data.get_or_default(west_adjoin.y, west_adjoin.x, None)
    if (
        west
        and pipe.symbol in _symbols_open_to_west
        and west.symbol in _symbols_open_to_east
    ):
        yield west

    north_adjoin = pipe.coord.adjoin(Dir.N)
    north = map_data.get_or_default(north_adjoin.y, north_adjoin.x, None)
    if (
        north
        and pipe.symbol in _symbols_open_to_north
        and north.symbol in _symbols_open_to_south
    ):
        yield north


def p1(input_str: str) -> int:
    map_data = _MapData(list(input_str.splitlines()))

    start = map_data.start
    neighbors_cur = list(_get_adjoin_pipes_on_path(start, map_data))
    assert len(neighbors_cur) == 2

    neighbors_prev = [start, start]

    dist = 1
    while neighbors_cur[0] != neighbors_cur[1]:
        neighbors_new = [
            next(n for n in _get_adjoin_pipes_on_path(cur, map_data) if n != prev)
            for prev, cur in zip(neighbors_prev, neighbors_cur, strict=True)
        ]
        neighbors_prev = neighbors_cur
        neighbors_cur = neighbors_new
        dist += 1

    return dist


def _resolve_start_symbol(start: _Pipe, start_neighbors: Iterable[_Pipe]) -> str:
    north = start.coord.adjoin(Dir.N)
    west = start.coord.adjoin(Dir.W)
    south = start.coord.adjoin(Dir.S)
    east = start.coord.adjoin(Dir.E)
    start_neighbor_coords = frozenset(n.coord for n in start_neighbors)
    return {
        frozenset((north, south)): "|",
        frozenset((east, west)): "-",
        frozenset((north, east)): "J",
        frozenset((north, west)): "L",
        frozenset((south, east)): "7",
        frozenset((south, west)): "F",
    }[start_neighbor_coords]


def _create_path_by_pipes(
    start: _Pipe, next_: _Pipe, map_data: _MapData
) -> list[_Pipe]:
    path_by_pipes: list[_Pipe] = [start, next_]
    while True:
        n = next(
            pipe
            for pipe in _get_adjoin_pipes_on_path(path_by_pipes[-1], map_data)
            if pipe is not path_by_pipes[-2]
        )
        if n == start:
            break
        path_by_pipes.append(n)

    for p in path_by_pipes:
        p.inside = _Inside.InPath
    return path_by_pipes


@define
class _PathPipe:
    pipe: _Pipe
    neighbors: dict[Dir, _Inside]


def _create_first_path_pipe(
    map_data: _MapData, coords_in_path: Collection[Coord2d]
) -> _PathPipe:
    # Guessed value for y to hit path on | symbol
    y = Y((map_data.height // 2) + 1)

    for _, x_iter in map_data.iter_data_by_lines(y, X(0), Y(y + 1), map_data.br_x):
        for _, pipe in x_iter:
            coord = pipe.coord
            if coord not in coords_in_path:
                assert pipe.inside is _Inside.Unknown
                pipe.inside = _Inside.Outside
            else:
                assert pipe.symbol not in "J7-S"
                assert pipe.symbol == "|", "Use better value for y"
                adjoin_coord = pipe.coord.adjoin(Dir.E)
                east_neighbor = map_data.get(adjoin_coord.y, adjoin_coord.x)
                if east_neighbor and east_neighbor.coord not in coords_in_path:
                    east_neighbor.inside = _Inside.Inside
                return _PathPipe(pipe, {Dir.E: _Inside.Inside, Dir.W: _Inside.Outside})
    raise AssertionError


@define
class _NeighborCheckGroup:
    prev_neighbor_dirs_to_check: list[Dir]
    neighbor_dirs_to_set: list[Dir] = field(factory=list[Dir])
    inside: _Inside = _Inside.Unknown


def _get_neighbor_check_groups(symbol: str, path_dir: Dir) -> list[_NeighborCheckGroup]:
    check_groups_straight = {
        "|": [
            _NeighborCheckGroup([Dir.W], [Dir.W]),
            _NeighborCheckGroup([Dir.E], [Dir.E]),
        ],
        "-": [
            _NeighborCheckGroup([Dir.N], [Dir.N]),
            _NeighborCheckGroup([Dir.S], [Dir.S]),
        ],
    }
    check_groups_corner = {
        "L": {
            Dir.W: [
                _NeighborCheckGroup([Dir.S], [Dir.S, Dir.W]),
                _NeighborCheckGroup([Dir.N]),
            ],
            Dir.S: [
                _NeighborCheckGroup([Dir.W], [Dir.S, Dir.W]),
                _NeighborCheckGroup([Dir.E]),
            ],
        },
        "F": {
            Dir.N: [
                _NeighborCheckGroup([Dir.W], [Dir.N, Dir.W]),
                _NeighborCheckGroup([Dir.E]),
            ],
            Dir.W: [
                _NeighborCheckGroup([Dir.N], [Dir.N, Dir.W]),
                _NeighborCheckGroup([Dir.S]),
            ],
        },
        "7": {
            Dir.N: [
                _NeighborCheckGroup([Dir.E], [Dir.N, Dir.E]),
                _NeighborCheckGroup([Dir.W]),
            ],
            Dir.E: [
                _NeighborCheckGroup([Dir.N], [Dir.N, Dir.E]),
                _NeighborCheckGroup([Dir.S]),
            ],
        },
        "J": {
            Dir.S: [
                _NeighborCheckGroup([Dir.E], [Dir.S, Dir.E]),
                _NeighborCheckGroup([Dir.W]),
            ],
            Dir.E: [
                _NeighborCheckGroup([Dir.S], [Dir.S, Dir.E]),
                _NeighborCheckGroup([Dir.N]),
            ],
        },
    }
    if symbol in check_groups_straight:
        return check_groups_straight[symbol]
    return check_groups_corner[symbol][path_dir]


def create_path_pipe(prev: _PathPipe, pipe: _Pipe, map_data: _MapData) -> _PathPipe:
    path_dir = prev.pipe.coord.dir_to(pipe.coord)

    neighbor_check_groups = _get_neighbor_check_groups(pipe.symbol, path_dir)
    assert len(neighbor_check_groups) == 2

    # Determine inside/outside for check groups
    for check_group in neighbor_check_groups:
        for check_dir in check_group.prev_neighbor_dirs_to_check:
            prev_inside = prev.neighbors.get(check_dir)
            if prev_inside is None:
                continue
            assert prev_inside in (_Inside.Inside, _Inside.Outside)
            check_group.inside = prev_inside
            break

    # If any check groups are still unknown, set them to the opposite of the known
    unknown_check_groups_with_neighbors_to_set = [
        check_group
        for check_group in neighbor_check_groups
        if check_group.inside is _Inside.Unknown and check_group.neighbor_dirs_to_set
    ]
    assert len(unknown_check_groups_with_neighbors_to_set) <= 1
    if unknown_check_groups_with_neighbors_to_set:
        known_check_groups = [
            check_group
            for check_group in neighbor_check_groups
            if check_group.inside is not _Inside.Unknown
        ]
        assert len(known_check_groups) == 1
        known_inside = known_check_groups[0].inside
        inside_for_unknown = (
            _Inside.Inside if known_inside is _Inside.Outside else _Inside.Outside
        )
        for check_group in unknown_check_groups_with_neighbors_to_set:
            check_group.inside = inside_for_unknown

    # Record neighbors for PathPipe to be used on next iteration
    neighbors = {
        neighbor_dir: check_group.inside
        for check_group in neighbor_check_groups
        for neighbor_dir in check_group.neighbor_dirs_to_set
    }
    assert all(
        value in (_Inside.Inside, _Inside.Outside) for value in neighbors.values()
    )

    # Set inside/outside for direct neighbors already in map as we have the data
    # available
    for neighbor_dir, inside in neighbors.items():
        neighbor_coord = pipe.coord.adjoin(neighbor_dir)
        neighbor = map_data.get_or_default(neighbor_coord.y, neighbor_coord.x, None)
        if neighbor is not None and neighbor.inside is not _Inside.InPath:
            assert neighbor.inside is _Inside.Unknown or neighbor.inside is inside
            neighbor.inside = inside

    return _PathPipe(pipe, neighbors)


def mark_pipes(map_data: _MapData) -> None:
    def mark_pipe(
        pipe: _Pipe, visited_recursive_coords: set[Coord2d] | None = None
    ) -> None:
        if pipe.inside is not _Inside.Unknown:
            return

        if visited_recursive_coords is None:
            visited_recursive_coords = set()
        visited_recursive_coords.add(pipe.coord)

        for neighbor in (
            map_data.get_or_default(
                (neighbor_coord := pipe.coord.adjoin(direction)).y,
                neighbor_coord.x,
                None,
            )
            for direction in CardinalDirectionsAll
        ):
            if not neighbor:
                continue
            if neighbor.coord in visited_recursive_coords:
                continue
            mark_pipe(neighbor, visited_recursive_coords)
            if neighbor.inside in (_Inside.Inside, _Inside.Outside):
                pipe.inside = neighbor.inside
                return
        raise AssertionError

    for _, pipe_iter in map_data.iter_data():
        for _, pipe in pipe_iter:
            mark_pipe(pipe)


def p2(input_str: str) -> int:
    map_data = _MapData(list(input_str.splitlines()))

    start = map_data.start
    start_neighbors = list(_get_adjoin_pipes_on_path(start, map_data))

    fixed_start_symbol = _resolve_start_symbol(start, start_neighbors)
    _logger.debug("fixed_start_symbol=%s", fixed_start_symbol)
    start.symbol = fixed_start_symbol

    path_by_pipes = _create_path_by_pipes(start, start_neighbors[0], map_data)

    coords_in_path = {pipe.coord for pipe in path_by_pipes}
    first_path_pipe = _create_first_path_pipe(map_data, coords_in_path)
    _logger.debug("first_path_pipe=%s", first_path_pipe)

    _logger.info("Detecting inside/outside neighbors along path")
    index_in_path_for_first_path_pipe = path_by_pipes.index(first_path_pipe.pipe)
    prev_path_pipe: _PathPipe = first_path_pipe
    for pipe in itertools.chain(
        path_by_pipes[index_in_path_for_first_path_pipe + 1 :],
        path_by_pipes[:index_in_path_for_first_path_pipe],
    ):
        prev_path_pipe = create_path_pipe(prev_path_pipe, pipe, map_data)

    _logger.info("Marking rest of map for inside/outside")

    mark_pipes(map_data)

    def log_map(map_data: _MapData) -> None:
        def get_symbol_for_pipe(pipe: _Pipe) -> str:
            if pipe.inside is _Inside.Inside:
                return " "
            if pipe.inside is _Inside.Outside:
                return "."
            if pipe.inside is _Inside.InPath:
                return pipe.symbol
            return "#"

        if _logger.isEnabledFor(logging.DEBUG):
            for map_line in map_data.str_lines(get_symbol_for_pipe):
                _logger.debug(map_line)

    log_map(map_data)

    _logger.info("Calculating inside locations")

    return sum(
        1
        for _, pipe_iter in map_data.iter_data()
        for _, pipe in pipe_iter
        if pipe.inside is _Inside.Inside
    )


if __name__ == "__main__":
    run(p1, p2)
