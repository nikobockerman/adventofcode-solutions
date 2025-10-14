import functools
from typing import TYPE_CHECKING, NewType, overload

import yaml

from aoc_main import _solvers, _types, _utils

if TYPE_CHECKING:
    from collections.abc import Iterator

AnswerIntType = NewType("AnswerIntType", int)
AnswerStrType = NewType("AnswerStrType", str)
AnswerType = AnswerIntType | AnswerStrType


@functools.cache
def _read_correct_answers() -> dict[_types.PartId, AnswerType]:
    yaml_ = yaml.safe_load((_utils.get_repo_root() / "answers.yaml").read_text())
    data: dict[_types.PartId, AnswerType] = {}
    for year, days in yaml_.items():
        assert isinstance(year, int)
        for day, parts in days.items():
            assert isinstance(day, int)
            for part, answer_raw in parts.items():
                assert isinstance(part, int)
                assert _types.is_part(part)
                answer: AnswerType
                if isinstance(answer_raw, int):
                    answer = AnswerIntType(answer_raw)
                elif isinstance(answer_raw, str):
                    answer = AnswerStrType(answer_raw)
                else:
                    raise TypeError(answer_raw)
                data[_types.PartId(_types.Year(year), _types.Day(day), part)] = answer
    return data


@overload
def get_correct_answer(id_: _solvers.SolverId) -> AnswerType | None: ...


@overload
def get_correct_answer(id_: _types.PartId) -> AnswerType | None: ...


def get_correct_answer(id_: _types.PartId | _solvers.SolverId) -> AnswerType | None:
    if isinstance(id_, _solvers.SolverId):
        id_ = _types.PartId(id_.year, id_.day, id_.part)
    return _read_correct_answers().get(id_)


def get_part_ids_for_known_answers_for_one_day(
    year: _types.Year, day: _types.Day
) -> Iterator[_types.PartId]:
    yield from (
        id_ for id_ in _read_correct_answers() if id_.year == year and id_.day == day
    )


def get_part_ids_for_all_known_answers() -> Iterator[_types.PartId]:
    yield from _read_correct_answers()
