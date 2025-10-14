from typing import TYPE_CHECKING

from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


def _parse_input(lines: Iterable[str]) -> Iterable[tuple[int, list[dict[str, int]]]]:
    for line in lines:
        g_id, rounds = line[5:].split(":")
        _logger.debug("line=%s", line)

        yield (
            int(g_id),
            [
                {
                    color_count[1]: int(color_count[0])
                    for color_count in (
                        color_count_str.strip().split(" ")
                        for color_count_str in game_round.strip().split(",")
                    )
                }
                for game_round in rounds.strip().split(";")
            ],
        )


def p1(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    def maxes() -> Iterable[tuple[int, dict[str, int]]]:
        for g_id, rounds in d:
            max_counts: dict[str, int] = {}
            for game_round in rounds:
                for color, count in game_round.items():
                    if color not in max_counts or max_counts[color] < count:
                        max_counts[color] = count
            yield g_id, max_counts

    return sum(
        g_id
        for g_id, max_counts in maxes()
        if max_counts["red"] <= 12
        and max_counts["green"] <= 13
        and max_counts["blue"] <= 14
    )


def p2(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    def maxes() -> Iterable[dict[str, int]]:
        for _, rounds in d:
            max_counts: dict[str, int] = {}
            for game_round in rounds:
                for color, count in game_round.items():
                    if color not in max_counts or max_counts[color] < count:
                        max_counts[color] = count
            yield max_counts

    return sum(
        max_counts["red"] * max_counts["green"] * max_counts["blue"]
        for max_counts in maxes()
    )


if __name__ == "__main__":
    run(p1, p2)
