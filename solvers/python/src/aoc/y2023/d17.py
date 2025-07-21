from __future__ import annotations

import heapq

from attrs import define, field, frozen

from aoc.tooling.coordinates import Coord2d
from aoc.tooling.directions import CardinalDirection as Dir
from aoc.tooling.map import Map2d
from aoc.tooling.run import get_logger, run

_logger = get_logger()


@frozen
class _PathPosition:
    coord: Coord2d
    direction: Dir
    next_coord: Coord2d
    moves_straight: int
    heat_loss: int
    estimated_total_heat_loss: int

    def __lt__(self, other: _PathPosition) -> bool:
        return self.estimated_total_heat_loss < other.estimated_total_heat_loss


def _estimate_remaining_heat_loss(start: Coord2d, destination: Coord2d) -> int:
    return start.distance_to_int(destination)


class _PriorityQueue:
    def __init__(self) -> None:
        self._queue = list[_PathPosition]()

    def put(self, item: _PathPosition) -> None:
        heapq.heappush(self._queue, item)

    def pop(self) -> _PathPosition:
        return heapq.heappop(self._queue)


def _create_prio_queue(start_pos: Coord2d, destination: Coord2d) -> _PriorityQueue:
    queue = _PriorityQueue()
    for start_dir in (Dir.S, Dir.E):
        new_next_coord = start_pos.adjoin(start_dir)
        pos = _PathPosition(
            start_pos,
            start_dir,
            new_next_coord,
            1,
            0,
            _estimate_remaining_heat_loss(new_next_coord, destination),
        )
        _logger.debug("Adding %s to queue", pos)
        queue.put(pos)
    return queue


type _VisitedMinCacheKey = tuple[Coord2d, Dir]
type _VisitedMinCacheValue = tuple[list[tuple[int, int]], list[tuple[int, int]]]


@define
class _ResolutionData:
    min_straight_moves: int
    max_straight_moves: int
    map_: Map2d[int]
    visited_min_cache: dict[_VisitedMinCacheKey, _VisitedMinCacheValue] = field(
        factory=dict[_VisitedMinCacheKey, _VisitedMinCacheValue]
    )


def _get_next_position_in_direction(
    pos: _PathPosition,
    new_dir: Dir,
    new_heat_loss: int,
    destination: Coord2d,
    data: _ResolutionData,
) -> _PathPosition | None:
    if new_dir != pos.direction and pos.moves_straight < data.min_straight_moves:
        return None
    if new_dir == pos.direction:
        if pos.moves_straight >= data.max_straight_moves:
            return None
        new_moves_straight = pos.moves_straight + 1
    else:
        new_moves_straight = 1

    _logger.debug("Processing move %s -> %s", pos.next_coord, new_dir)

    cached_pos = data.visited_min_cache.get((pos.next_coord, new_dir))
    if cached_pos is None:
        if new_moves_straight >= data.min_straight_moves:
            data.visited_min_cache[(pos.next_coord, new_dir)] = (
                [(new_moves_straight, new_heat_loss)],
                [],
            )
        else:
            data.visited_min_cache[(pos.next_coord, new_dir)] = (
                [],
                [(new_moves_straight, new_heat_loss)],
            )
    else:
        if new_moves_straight >= data.min_straight_moves:
            cache_list = cached_pos[0]
            cached_min = next(
                (
                    heat_loss
                    for straight_so_far, heat_loss in cache_list
                    if new_moves_straight >= straight_so_far
                ),
                None,
            )
        else:
            cache_list = cached_pos[1]
            cached_min = next(
                (
                    heat_loss
                    for straight_so_far, heat_loss in cache_list
                    if new_moves_straight == straight_so_far
                ),
                None,
            )
        if cached_min is not None and cached_min <= new_heat_loss:
            _logger.debug(
                "Already seen with better or equal heat loss: %d",
                cached_min,
            )
            return None
        cache_list.append((new_moves_straight, new_heat_loss))
        cache_list.sort(key=lambda x: x[1])
        _logger.debug(
            "Cached before but with worse heat loss. New entries: %s",
            cached_pos,
        )

    new_next_coord = pos.next_coord.adjoin(new_dir)

    if (
        new_next_coord.x < data.map_.tl_x
        or new_next_coord.x > data.map_.br_x
        or new_next_coord.y < data.map_.tl_y
        or new_next_coord.y > data.map_.br_y
    ):
        _logger.debug("Outside of map")
        return None

    return _PathPosition(
        pos.next_coord,
        new_dir,
        new_next_coord,
        new_moves_straight,
        new_heat_loss,
        new_heat_loss + _estimate_remaining_heat_loss(new_next_coord, destination),
    )


def _resolve(input_str: str, min_straight_moves: int, max_straight_moves: int) -> int:
    map_ = Map2d((int(c) for c in line) for line in input_str.splitlines())
    start_pos = Coord2d(map_.tl_y, map_.tl_x)
    destination = Coord2d(map_.br_y, map_.br_x)

    queue = _create_prio_queue(start_pos, destination)

    data = _ResolutionData(min_straight_moves, max_straight_moves, map_)

    result: int | None = None
    while True:
        pos = queue.pop()

        _logger.debug("Processing cheapest: %s", pos)

        new_heat_loss = pos.heat_loss + map_.get(pos.next_coord.y, pos.next_coord.x)

        if pos.next_coord == destination:
            if result is None or new_heat_loss < result:
                _logger.debug(
                    "Found new shortest path: new_heat_loss=%s", new_heat_loss
                )
                result = new_heat_loss
            elif new_heat_loss > result:
                break
            continue

        for new_dir in (
            pos.direction,
            pos.direction.rotate_counterclockwise(),
            pos.direction.rotate_clockwise(),
        ):
            new_pos = _get_next_position_in_direction(
                pos, new_dir, new_heat_loss, destination, data
            )
            if new_pos is None:
                continue

            _logger.debug("Adding %s to queue", new_pos)
            queue.put(new_pos)

    assert result is not None
    return result


def p1(input_str: str) -> int:
    return _resolve(input_str, 0, 3)


def p2(input_str: str) -> int:
    return _resolve(input_str, 4, 10)


if __name__ == "__main__":
    run(p1, p2)
