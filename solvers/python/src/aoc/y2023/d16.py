from aoc.tooling.coordinates import Coord2d, X, Y
from aoc.tooling.directions import CardinalDirection as Dir
from aoc.tooling.map import Map2d
from aoc.tooling.run import get_logger, run

_logger = get_logger()


class _SplitterExitCache:
    __slots__ = ("_cache",)

    def __init__(self) -> None:
        self._cache: dict[
            tuple[Coord2d, Dir], tuple[set[Coord2d], list[tuple[Coord2d, Dir]]]
        ] = {}

    def get(
        self, coord: Coord2d, dir_: Dir
    ) -> tuple[set[Coord2d], list[tuple[Coord2d, Dir]]] | None:
        return self._cache.get((coord, dir_))

    def add(
        self,
        coord: Coord2d,
        dir_: Dir,
        visited: set[Coord2d],
        next_splitter_exits: list[tuple[Coord2d, Dir]],
    ) -> None:
        assert (coord, dir_) not in self._cache
        self._cache[(coord, dir_)] = (visited, next_splitter_exits)


def _process_splitter_exit(
    coord: Coord2d, dir_: Dir, map_: Map2d
) -> tuple[set[Coord2d], list[tuple[Coord2d, Dir]]]:
    visited: set[Coord2d] = set()
    next_splitter_exits: list[tuple[Coord2d, Dir]] = []
    while True:
        if (
            coord.x < map_.tl_x
            or coord.x > map_.br_x
            or coord.y < map_.tl_y
            or coord.y > map_.br_y
        ):
            _logger.debug("Out of map")
            break
        visited.add(coord)

        symbol = map_.get(coord.y, coord.x)
        _logger.debug("Coord: %s Dir: %s Symbol: %s", coord, dir_, symbol)

        if symbol == ".":
            coord = coord.adjoin(dir_)
            continue

        if symbol == "/":
            dir_ = (
                dir_.rotate_clockwise()
                if dir_ in (Dir.N, Dir.S)
                else dir_.rotate_counterclockwise()
            )
            coord = coord.adjoin(dir_)
            continue

        if symbol == "\\":
            dir_ = (
                dir_.rotate_counterclockwise()
                if dir_ in (Dir.N, Dir.S)
                else dir_.rotate_clockwise()
            )
            coord = coord.adjoin(dir_)
            continue

        if symbol == "-":
            if dir_ in (Dir.N, Dir.S):
                next_splitter_exits.extend(
                    [(coord.adjoin(Dir.E), Dir.E), (coord.adjoin(Dir.W), Dir.W)]
                )
            else:
                next_splitter_exits.append((coord.adjoin(dir_), dir_))
            break

        if symbol == "|":
            if dir_ in (Dir.E, Dir.W):
                next_splitter_exits.extend(
                    [(coord.adjoin(Dir.N), Dir.N), (coord.adjoin(Dir.S), Dir.S)]
                )
            else:
                next_splitter_exits.append((coord.adjoin(dir_), dir_))
            break
    return visited, next_splitter_exits


def _try_one_enter(
    enter_coord: Coord2d,
    enter_dir: Dir,
    map_: Map2d,
    exit_cache: _SplitterExitCache,
) -> int:
    visited: set[Coord2d] = set()
    processed_splitter_exits: set[tuple[Coord2d, Dir]] = set()
    processing_queue: list[tuple[Coord2d, Dir]] = [(enter_coord, enter_dir)]

    while processing_queue:
        coord, dir_ = processing_queue.pop(0)
        _logger.debug("Start processing %s -> %s", coord, dir_)
        if (coord, dir_) in processed_splitter_exits:
            _logger.debug("Already processed")
            continue
        processed_splitter_exits.add((coord, dir_))
        _logger.debug("Visited count so far: %d", len(visited))

        cached = exit_cache.get(coord, dir_)
        if cached is not None:
            _logger.debug("Cache hit")
            processed_visited, next_splitter_exits = cached
        else:
            processed_visited, next_splitter_exits = _process_splitter_exit(
                coord, dir_, map_
            )
            exit_cache.add(coord, dir_, processed_visited, next_splitter_exits)
        visited |= processed_visited
        processing_queue.extend(next_splitter_exits)
    return len(visited)


def p1(input_str: str) -> int:
    map_ = Map2d(input_str.splitlines())
    exit_cache = _SplitterExitCache()
    return _try_one_enter(Coord2d(map_.tl_y, map_.tl_x), Dir.E, map_, exit_cache)


def p2(input_str: str) -> int:
    map_ = Map2d(input_str.splitlines())
    exit_cache = _SplitterExitCache()
    results: list[tuple[Coord2d, Dir, int]] = []

    for x1 in range(map_.tl_x, map_.br_x + 1):
        for y1 in (map_.tl_y, map_.br_y):
            coord = Coord2d(y1, X(x1))
            dir_ = Dir.S if y1 == 0 else Dir.N
            _logger.info("Trying %s -> %s", coord, dir_)
            result = _try_one_enter(coord, dir_, map_, exit_cache)
            _logger.info("Result %s -> %s = %d", coord, dir_, result)
            results.append((coord, dir_, result))
    for y2 in range(map_.tl_y, map_.br_y + 1):
        for x2 in (map_.tl_x, map_.br_x):
            coord = Coord2d(Y(y2), x2)
            dir_ = Dir.E if x2 == 0 else Dir.W
            _logger.info("Trying %s -> %s", coord, dir_)
            result = _try_one_enter(coord, dir_, map_, exit_cache)
            _logger.info("Result %s -> %s = %d", coord, dir_, result)
            results.append((coord, dir_, result))

    results.sort(key=lambda r: r[2])
    return results[-1][2]


if __name__ == "__main__":
    run(p1, p2)
