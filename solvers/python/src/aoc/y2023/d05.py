from typing import TYPE_CHECKING

from attrs import Factory, define, field

from aoc.tooling.ranges import are_ranges_overlapping, partition_range
from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


@define
class _RangeMap:
    destination_start: int
    source_start: int
    length: int


@define
class _InputMaps:
    seed_to_soil_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    soil_to_fertilizer_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    fertilizer_to_water_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    water_to_light_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    light_to_temperature_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    temperature_to_humidity_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )
    humidity_to_location_map: list[_RangeMap] = field(
        default=Factory(list[_RangeMap]), init=False
    )


def _parse_input(lines: list[str]) -> tuple[list[int], _InputMaps]:
    seeds = list(map(int, lines[0].strip().split(":")[1].strip().split()))

    maps = _InputMaps()

    def save_mappings(mappings: list[_RangeMap], mapping_name: str) -> None:
        prop_name = mapping_name.replace("-", "_").replace(" ", "_")
        setattr(maps, prop_name, mappings)

    def parse_mapping(line: str) -> _RangeMap:
        return _RangeMap(*map(int, line.strip().split()))

    mapping_name: str | None = None
    mappings: list[_RangeMap] | None = None
    for line in lines[2:]:
        if not line:
            assert mappings is not None
            assert mapping_name is not None
            save_mappings(mappings, mapping_name)
            mapping_name = None
            mappings = None
            continue
        if line[-1] == ":":
            mapping_name = line[:-1]
            mappings = []
            continue

        assert mappings is not None
        mappings.append(parse_mapping(line))

    if mapping_name:
        assert mappings is not None
        save_mappings(mappings, mapping_name)

    return seeds, maps


def _get_location(maps: _InputMaps, seed: int) -> int:
    def get_destination(mappings: list[_RangeMap], source: int) -> int:
        for mapping in mappings:
            if source < mapping.source_start or source >= (
                mapping.source_start + mapping.length
            ):
                continue

            offset = source - mapping.source_start
            return mapping.destination_start + offset

        return source

    return get_destination(
        maps.humidity_to_location_map,
        get_destination(
            maps.temperature_to_humidity_map,
            get_destination(
                maps.light_to_temperature_map,
                get_destination(
                    maps.water_to_light_map,
                    get_destination(
                        maps.fertilizer_to_water_map,
                        get_destination(
                            maps.soil_to_fertilizer_map,
                            get_destination(maps.seed_to_soil_map, seed),
                        ),
                    ),
                ),
            ),
        ),
    )


def p1(input_str: str) -> int:
    seeds, maps = _parse_input(input_str.splitlines())
    _logger.debug("seeds=%s", seeds)
    _logger.debug("maps=%s", maps)

    return min(_get_location(maps, seed) for seed in seeds)


def _resolve_overlap(
    overlap_source: range,
    dest_overlap: range,
    next_ind: int,
    max_ind: int,
    mapping_ranges: list[list[tuple[range, range]]],
) -> Iterable[tuple[range, range]]:
    for resolved_source, top_level_source in _resolve_ranges(
        overlap_source, next_ind, max_ind, mapping_ranges
    ):
        resolved_offset_start = resolved_source.start - overlap_source.start
        resolved_offset_stop = overlap_source.stop - resolved_source.stop
        resolved_dest_start = dest_overlap.start + resolved_offset_start
        resolved_dest_stop = dest_overlap.stop - resolved_offset_stop
        assert resolved_dest_start < resolved_dest_stop

        yield range(resolved_dest_start, resolved_dest_stop), top_level_source


def _resolve_ranges(
    dest_range_for_ind: range,
    ind: int,
    max_ind: int,
    mapping_ranges: list[list[tuple[range, range]]],
    mapping_start_index: int | None = None,
) -> Iterable[tuple[range, range]]:
    assert ind <= max_ind

    if mapping_start_index is None:
        mapping_start_index = 0

    for mapping_range_ind, ranges in enumerate(
        mapping_ranges[ind], mapping_start_index
    ):
        mapping_dest_range, mapping_source_range = ranges

        (
            dest_before,
            dest_overlap,
            dest_after,
        ) = partition_range(dest_range_for_ind, mapping_dest_range)

        if not dest_overlap:
            assert bool(dest_before) != bool(dest_after)
            continue

        if dest_before:
            yield from _resolve_ranges(
                dest_before, ind, max_ind, mapping_ranges, mapping_range_ind + 1
            )

        overlap_offset_start = dest_overlap.start - mapping_dest_range.start
        overlap_offset_stop = mapping_dest_range.stop - dest_overlap.stop
        overlap_source_start = mapping_source_range.start + overlap_offset_start
        overlap_source_stop = mapping_source_range.stop - overlap_offset_stop
        assert overlap_source_start < overlap_source_stop

        overlap_source = range(overlap_source_start, overlap_source_stop)

        if ind == max_ind:
            yield dest_overlap, overlap_source
        else:
            yield from _resolve_overlap(
                overlap_source, dest_overlap, ind + 1, max_ind, mapping_ranges
            )

        if dest_after:
            yield from _resolve_ranges(
                dest_after, ind, max_ind, mapping_ranges, mapping_range_ind + 1
            )

        return

    if ind == max_ind:
        yield dest_range_for_ind, dest_range_for_ind
    else:
        yield from _resolve_ranges(dest_range_for_ind, ind + 1, max_ind, mapping_ranges)


def p2(input_str: str) -> int:
    seed_data, maps = _parse_input(input_str.splitlines())

    seed_starts = seed_data[0::2]
    seed_lengths = seed_data[1::2]
    seed_ranges = [
        range(start, start + length)
        for start, length in zip(seed_starts, seed_lengths, strict=True)
    ]

    maps.humidity_to_location_map.sort(key=lambda m: m.destination_start)

    mapping_ranges = [
        [
            (
                range(
                    mapping.destination_start,
                    mapping.destination_start + mapping.length,
                ),
                range(mapping.source_start, mapping.source_start + mapping.length),
            )
            for mapping in mappings
        ]
        for mappings in [
            maps.humidity_to_location_map,
            maps.temperature_to_humidity_map,
            maps.light_to_temperature_map,
            maps.water_to_light_map,
            maps.fertilizer_to_water_map,
            maps.soil_to_fertilizer_map,
            maps.seed_to_soil_map,
        ]
    ]
    max_ind = len(mapping_ranges) - 1

    location_dest_ranges = [dest_range for dest_range, _ in mapping_ranges[0]]
    if location_dest_ranges[0].start > 0:
        location_dest_ranges.insert(0, range(location_dest_ranges[0].start))

    for initial_dest_range in location_dest_ranges:
        for resolved_location_range, resolved_seed_range in _resolve_ranges(
            initial_dest_range, 0, max_ind, mapping_ranges
        ):
            if any(
                are_ranges_overlapping(resolved_seed_range, seed_range)
                for seed_range in seed_ranges
            ):
                return resolved_location_range.start
    raise AssertionError


if __name__ == "__main__":
    run(p1, p2)
