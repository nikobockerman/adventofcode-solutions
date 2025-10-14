import itertools
from typing import TYPE_CHECKING, Literal

from attrs import frozen

from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


@frozen
class _Data:
    records: str
    group_lengths: list[int]

    def __str__(self) -> str:
        return f"{self.records} {self.group_lengths}"


def _parse_input(lines: Iterable[str]) -> Iterable[_Data]:
    for line in lines:
        records, group_lengths = line.split()
        yield _Data(records, [int(length) for length in group_lengths.split(",")])


@frozen
class _ClassificationState:
    known_damaged_lengths: list[int]
    index_of_first_unknown: int
    previous_was_damaged: bool
    possible_unknown_symbols: str


class _Classifier:
    def __init__(
        self, data: _Data, prev_state: _ClassificationState | None = None
    ) -> None:
        self._data = data
        self._completion_classification: bool | None = None
        self._completion_classification_done: bool = False
        self._first_unknown_index: int | None = None
        self._first_unknown_index_resolved: bool = False
        self._first_unknown_index_next_search_index: int = 0
        self._classification_state: _ClassificationState | None = None
        self._prev_classification_state: _ClassificationState | None = prev_state

    @property
    def classification_state(self) -> _ClassificationState | None:
        return self._classification_state

    def _process_for_classification(
        self,
    ) -> Literal[False] | tuple[list[int], int, bool]:
        if self._prev_classification_state is not None:
            known_damaged_lengths = (
                self._prev_classification_state.known_damaged_lengths[:]
            )
            known_damaged_index = len(known_damaged_lengths) - 1
            min_remaining_length = (
                sum(self._data.group_lengths[known_damaged_index + 1 :])
                + len(self._data.group_lengths)
                - len(known_damaged_lengths)
                - 1
            ) + (
                0
                if not known_damaged_lengths
                else (
                    self._data.group_lengths[known_damaged_index]
                    - known_damaged_lengths[known_damaged_index]
                )
            )
            prev_is_damaged = self._prev_classification_state.previous_was_damaged
            count = self._prev_classification_state.index_of_first_unknown
        else:
            known_damaged_lengths = []
            min_remaining_length = (
                sum(self._data.group_lengths) + len(self._data.group_lengths) - 1
            )
            prev_is_damaged = False
            known_damaged_index = -1
            count = 0

        for symbol, sym_iter in itertools.groupby(
            itertools.islice(self._data.records, count, None)
        ):
            if symbol == "?":
                self._first_unknown_index = count
                self._first_unknown_index_resolved = True
                break
            length = sum(1 for _ in sym_iter)
            count += length
            self._first_unknown_index_next_search_index = count
            if symbol == "#":
                if not prev_is_damaged:
                    known_damaged_index += 1
                    if (
                        known_damaged_index >= len(self._data.group_lengths)
                        or length > self._data.group_lengths[known_damaged_index]
                    ):
                        return False
                    known_damaged_lengths.append(length)
                    prev_is_damaged = True
                    min_remaining_length -= length + 1
                else:
                    assert known_damaged_index < len(self._data.group_lengths)
                    min_remaining_length -= length
                    length += known_damaged_lengths[known_damaged_index]
                    if length > self._data.group_lengths[known_damaged_index]:
                        return False
                    known_damaged_lengths[known_damaged_index] = length
                    prev_is_damaged = True
            else:
                if (
                    prev_is_damaged
                    and known_damaged_lengths[known_damaged_index]
                    != self._data.group_lengths[known_damaged_index]
                ):
                    return False
                prev_is_damaged = False

            if min_remaining_length > len(self._data.records) - count:
                return False

        return known_damaged_lengths, known_damaged_index, prev_is_damaged

    def _classify_completion(self) -> bool | None:
        result = self._process_for_classification()
        if isinstance(result, bool):
            return result

        known_damaged_lengths, known_damaged_index, prev_is_damaged = result

        if known_damaged_lengths == self._data.group_lengths:
            if not self._first_unknown_index_resolved:
                return True
            return all(
                symbol != "#"
                for symbol in self._data.records[self._first_unknown_index :]
            )

        if self._first_unknown_index is None:
            # No unknowns found -> records processed exhaustively
            return known_damaged_lengths == self._data.group_lengths

        def possible_next_symbols() -> str:
            if prev_is_damaged:
                if (
                    known_damaged_lengths[known_damaged_index]
                    == self._data.group_lengths[known_damaged_index]
                ):
                    return "."
                return "#"
            return ".#"

        self._classification_state = _ClassificationState(
            known_damaged_lengths,
            self._first_unknown_index,
            prev_is_damaged,
            possible_next_symbols(),
        )
        return None

    def completion(self) -> bool | None:
        if self._completion_classification_done:
            return self._completion_classification

        self._completion_classification = self._classify_completion()
        self._completion_classification_done = True
        return self._completion_classification

    def _find_first_unknown_index(self) -> int | None:
        for ind, symbol in enumerate(
            self._data.records[self._first_unknown_index_next_search_index :]
        ):
            if symbol == "?":
                return ind + self._first_unknown_index_next_search_index
        return None

    def first_unknown_index(self) -> int | None:
        if self._first_unknown_index_resolved:
            return self._first_unknown_index

        self._first_unknown_index = self._find_first_unknown_index()
        self._first_unknown_index_resolved = True
        return self._first_unknown_index


def _calculate_alternatives(
    data: _Data,
    prev_state: _ClassificationState | None = None,
    result_cache: dict[tuple[str, str], int] | None = None,
    recursion_depth: int = 0,
) -> int:
    classifier = _Classifier(data, prev_state)
    if classifier.completion() is True:
        result = 1
        _logger.debug("CA %02d: %s -> Impossible -> %d", recursion_depth, data, result)
        return result

    if classifier.completion() is False:
        result = 0
        _logger.debug("CA %02d: %s -> Impossible -> %d", recursion_depth, data, result)
        return result

    first_unknown_index = classifier.first_unknown_index()
    assert first_unknown_index is not None
    assert data.records[first_unknown_index] == "?"
    records_begin = data.records[:first_unknown_index]
    records_end = data.records[first_unknown_index + 1 :]
    classification_state = classifier.classification_state
    assert classification_state is not None

    if result_cache is None:
        result_cache = {}

    result = 0
    for symbol in classification_state.possible_unknown_symbols:
        records_ending = f"{symbol}{records_end}"
        if (
            classification_state.known_damaged_lengths
            == data.group_lengths[: len(classification_state.known_damaged_lengths)]
        ):
            remaining_groups = data.group_lengths[
                len(classification_state.known_damaged_lengths) :
            ]
            groups_str = " ".join(str(group) for group in remaining_groups)
            cache_key: tuple[str, str] | None = (records_ending, groups_str)
            assert cache_key is not None
            cached_result = result_cache.get(cache_key)
            if cached_result is not None:
                result += cached_result
                continue
        else:
            cache_key = None

        alternative_result = _calculate_alternatives(
            _Data(f"{records_begin}{records_ending}", data.group_lengths),
            classification_state,
            result_cache,
            recursion_depth + 1,
        )
        if cache_key is not None:
            result_cache[cache_key] = alternative_result
        result += alternative_result

    _logger.debug("CA %02d: %s -> Guessed    -> %d", recursion_depth, data, result)
    return result


def p1(input_str: str) -> int:
    def p1_calc(ind: int, input_data: _Data) -> int:
        res = _calculate_alternatives(input_data)
        _logger.info("%d: %s -> %s", ind, input_data, res)
        return res

    return sum(
        p1_calc(ind, input_data)
        for ind, input_data in enumerate(_parse_input(input_str.splitlines()))
    )


def p2(input_str: str) -> int:
    def input_line_data_mapper(input_line_data: _Data) -> _Data:
        return _Data(
            "?".join(input_line_data.records for _ in range(5)),
            input_line_data.group_lengths * 5,
        )

    def p2_calc(ind: int, input_data: _Data) -> int:
        res = _calculate_alternatives(input_data)
        _logger.info("%d: %s -> %s", ind, input_data, res)
        return res

    return sum(
        p2_calc(ind, input_data)
        for ind, input_data in enumerate(
            map(input_line_data_mapper, _parse_input(input_str.splitlines()))
        )
    )


if __name__ == "__main__":
    run(p1, p2)
