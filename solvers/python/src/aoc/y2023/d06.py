import enum
from collections.abc import Iterable
from functools import reduce

from aoc.tooling.run import run


def _parse_input(lines: list[str]) -> list[tuple[int, int]]:
    times = map(int, lines[0][5:].strip().split())
    distances = map(int, lines[1][9:].strip().split())
    return list(zip(times, distances, strict=True))


def _is_winning_scenario(
    button_press_time: int, max_time: int, distance_to_beat: int
) -> bool:
    distance = (max_time - button_press_time) * (button_press_time)
    return distance > distance_to_beat


def p1(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    def possible_button_press_times(
        max_time: int, distance_to_beat: int
    ) -> Iterable[int]:
        for button_press_time in range(1, max_time):
            if _is_winning_scenario(button_press_time, max_time, distance_to_beat):
                yield button_press_time

    possible_scenarios = [
        len(list(possible_button_press_times(race_time, record_distance)))
        for race_time, record_distance in d
    ]

    return reduce(lambda r1, r2: r1 * r2, possible_scenarios)


def p2(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())
    time = int(reduce(lambda t1, t2: t1 + t2, (str(t) for t, _ in d)))
    distance = int(reduce(lambda d1, d2: d1 + d2, (str(d) for _, d in d)))

    class ScenarioOrdering(enum.Enum):
        FASTEST = enum.auto()
        SLOWEST = enum.auto()

    def first_possible_button_press_time(
        max_time: int, distance_to_beat: int, ordering: ScenarioOrdering
    ) -> int:
        match ordering:
            case ScenarioOrdering.FASTEST:
                r = range(1, max_time)
            case ScenarioOrdering.SLOWEST:
                r = range(max_time - 1, 0, -1)
        for button_press_time in r:
            if _is_winning_scenario(button_press_time, max_time, distance_to_beat):
                return button_press_time
        raise AssertionError

    first_button_press_time = first_possible_button_press_time(
        time, distance, ScenarioOrdering.FASTEST
    )
    last_button_press_time = first_possible_button_press_time(
        time, distance, ScenarioOrdering.SLOWEST
    )
    return len(range(first_button_press_time, last_button_press_time)) + 1


if __name__ == "__main__":
    run(p1, p2)
