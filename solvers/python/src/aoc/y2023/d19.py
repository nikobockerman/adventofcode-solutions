import itertools
import logging
import math
import re
from collections.abc import Iterable, Mapping
from enum import Enum
from queue import Queue
from typing import Literal, NewType, TypeIs, cast

from attrs import define, frozen

from aoc.tooling.run import get_logger, run

_logger = get_logger()


type _Category = Literal["x", "m", "a", "s"]
_categories: frozenset[_Category] = frozenset(("x", "m", "a", "s"))

_Part = NewType("_Part", Mapping[_Category, int])


def is_category(category: str) -> TypeIs[_Category]:
    return category in _categories


class _Comparison(Enum):
    LT = "<"
    GT = ">"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.name}"


@frozen
class _Rule:
    category: _Category
    comparison: _Comparison
    value: int
    action: str


@frozen
class _Workflow:
    name: str
    rules: list[_Rule]
    default: str


_rule_regex = re.compile(
    r"(?P<category>[xmas])(?P<comparison>[<>])(?P<value>\d+):(?P<action>\w+)"
)


def _parse_rule(statement: str) -> _Rule:
    match = _rule_regex.match(statement)
    assert match is not None
    category = match.group("category")
    assert is_category(category)
    return _Rule(
        category,
        _Comparison(match.group("comparison")),
        int(match.group("value")),
        match.group("action"),
    )


_workflow_regex = re.compile(r"(?P<name>\w+)\{(?P<rules>.*?)\}")


def _parse_workflow(line: str) -> _Workflow:
    match = _workflow_regex.match(line)
    assert match is not None
    name = match.group("name")
    assert isinstance(name, str)
    rules_str = match.group("rules")
    assert isinstance(rules_str, str)
    *rule_statements, default = rules_str.split(",")
    rules = list(map(_parse_rule, rule_statements))
    return _Workflow(name, rules, default)


_part_regex = re.compile(r"\{x=(?P<x>\d+),m=(?P<m>\d+),a=(?P<a>\d+),s=(?P<s>\d+)\}")


def _parse_part(line: str) -> _Part:
    match = _part_regex.match(line)
    assert match is not None

    def key_to_category(key: str) -> _Category:
        assert is_category(key)
        return key

    return _Part({key_to_category(k): int(v) for k, v in match.groupdict().items()})


def _parse_input(input_str: str) -> tuple[dict[str, _Workflow], Iterable[_Part]]:
    input_line_iter = iter(input_str.splitlines())
    workflows = {
        workflow.name: workflow
        for workflow in map(
            _parse_workflow, itertools.takewhile(lambda line: line, input_line_iter)
        )
    }
    allowed_action_names = frozenset(itertools.chain(workflows.keys(), "AR"))
    assert all(
        workflow.default in allowed_action_names
        and all(rule.action in allowed_action_names for rule in workflow.rules)
        for workflow in workflows.values()
    )

    return workflows, map(_parse_part, input_line_iter)


def _process_part(
    in_workflow: _Workflow, workflows: dict[str, _Workflow], part: _Part
) -> bool:
    def _lt(left: int, right: int) -> bool:
        return left < right

    def _gt(left: int, right: int) -> bool:
        return left > right

    workflow = in_workflow
    while True:
        action = None
        for rule in workflow.rules:
            match rule.comparison:
                case _Comparison.LT:
                    compare = _lt
                case _Comparison.GT:
                    compare = _gt

            if compare(part[rule.category], rule.value):
                action = rule.action
                break
        else:
            action = workflow.default

        assert action is not None

        match action:
            case "A":
                return True
            case "R":
                return False
            case _:
                workflow = workflows[action]


def p1(input_str: str) -> int:
    workflows, parts_iter = _parse_input(input_str)
    in_workflow = workflows["in"]
    result = 0
    for part in parts_iter:
        if not _process_part(in_workflow, workflows, part):
            _logger.debug("Part %s rejected", part)
            continue

        total = sum(part.values())
        result += total
        _logger.debug(
            "Part %s accepted: total=%d, result so far=%d", part, total, result
        )

    return result


@define
class _WorkflowStep:
    category_value_ranges: dict[_Category, list[range] | None]
    next_workflow: str


def _merge_two_value_ranges(left: list[range], right: list[range]) -> list[range]:
    right_iter = iter(right)
    try:
        r2: range | None = next(right_iter)
    except StopIteration:
        return []

    result = list[range]()
    for r in left:
        assert r2 is not None
        while r2.stop < r.start:
            r2 = next(right_iter, None)
            if r2 is None:
                break

        if r2 is None:
            break

        assert r2.stop >= r.start
        if r2.start > r.stop:
            continue

        start = max(r.start, r2.start)
        stop = min(r.stop, r2.stop)
        assert start < stop
        result.append(range(start, stop))

        while r2.start < r.stop:
            r2 = next(right_iter, None)
            if r2 is None:
                break

            if r2.start > r.stop:
                break

            start = max(r.start, r2.start)
            assert start == r2.start
            stop = min(r.stop, r2.stop)
            result.append(range(start, stop))

    return result


def _merge_value_range(
    left: list[range] | None, right: list[range] | None
) -> list[range] | None:
    if left is None:
        return None if right is None else list(right)
    if right is None:
        return list(left)
    return _merge_two_value_ranges(left, right)


def _merge_category_value_ranges(
    left: Mapping[_Category, list[range] | None],
    right: Mapping[_Category, list[range] | None],
) -> dict[_Category, list[range] | None]:
    return {
        category: _merge_value_range(left[category], right[category])
        for category in left
    }


def _negated_value_range(value_range: list[range] | None) -> list[range] | None:
    if value_range is None:
        return None

    if not value_range:
        return [range(1, 4_000 + 1)]

    result = list[range]()
    prev_stop = 1
    for r in value_range:
        if r.start > prev_stop:
            result.append(range(prev_stop, r.start))
        prev_stop = r.stop
    if prev_stop < 4_000 + 1:
        result.append(range(prev_stop, 4_000 + 1))
    return result


def _negated_category_value_ranges(
    category_value_ranges: Mapping[_Category, list[range] | None],
) -> dict[_Category, list[range] | None]:
    return {
        category: _negated_value_range(category_value_ranges[category])
        for category in category_value_ranges
    }


def _category_value_ranges_from_rule(
    rule: _Rule,
) -> dict[_Category, list[range] | None]:
    return {
        category: (
            None
            if category != rule.category
            else (
                [range(1, rule.value)]
                if rule.comparison == _Comparison.LT
                else [range(rule.value + 1, 4_000 + 1)]
            )
        )
        for category in _categories
    }


def _possible_category_value_ranges(
    category_value_ranges: dict[_Category, list[range] | None],
) -> bool:
    return all(
        value_ranges is None or value_ranges
        for value_ranges in category_value_ranges.values()
    )


def _construct_workflow_steps(workflow: _Workflow) -> list[_WorkflowStep]:
    result = list[_WorkflowStep]()
    failure_limits: dict[_Category, list[range] | None] = dict.fromkeys(_categories)
    for rule in workflow.rules:
        category_value_ranges = _category_value_ranges_from_rule(rule)
        applicable_category_value_ranges = _merge_category_value_ranges(
            failure_limits, category_value_ranges
        )
        assert _possible_category_value_ranges(applicable_category_value_ranges)
        result.append(_WorkflowStep(applicable_category_value_ranges, rule.action))
        negated_category_value_ranges = _negated_category_value_ranges(
            category_value_ranges
        )
        failure_limits = _merge_category_value_ranges(
            failure_limits, negated_category_value_ranges
        )

    result.append(_WorkflowStep(failure_limits, workflow.default))
    return result


def p2(input_str: str) -> int:
    workflows, _ = _parse_input(input_str)

    queue = Queue[_WorkflowStep]()
    queue.put_nowait(
        _WorkflowStep({cat: [range(1, 4_000 + 1)] for cat in _categories}, "in")
    )

    workflow_step_cache = dict[str, list[_WorkflowStep]]()

    accepted_category_value_ranges = list[dict[_Category, list[range]]]()
    while not queue.empty():
        step = queue.get_nowait()
        _logger.debug("Processing step: %s", step)
        if step.next_workflow == "R":
            _logger.debug("Rejected step")
            continue
        if step.next_workflow == "A":
            _logger.debug("Accepted step")
            assert all(
                ranges is not None for ranges in step.category_value_ranges.values()
            )
            ranges = cast("dict[_Category, list[range]]", step.category_value_ranges)
            accepted_category_value_ranges.append(ranges)
            continue

        workflow = workflows[step.next_workflow]
        workflow_steps = workflow_step_cache.get(workflow.name)
        if workflow_steps is None:
            _logger.debug("Constructing workflow steps for %s", workflow)
            workflow_steps = _construct_workflow_steps(workflow)
            _logger.debug("Constructed workflow steps: %s", workflow_steps)
            workflow_step_cache[workflow.name] = workflow_steps

        for workflow_step in workflow_steps:
            new_category_value_ranges = _merge_category_value_ranges(
                step.category_value_ranges, workflow_step.category_value_ranges
            )
            if not _possible_category_value_ranges(new_category_value_ranges):
                _logger.debug(
                    "Skipping step -> workflow as ranges are impossible: %s -> %s",
                    step,
                    workflow_step,
                )
                continue

            queue.put_nowait(
                _WorkflowStep(new_category_value_ranges, workflow_step.next_workflow)
            )

    assert all(
        ranges is not None and len(ranges) == 1
        for cat_value_ranges in accepted_category_value_ranges
        for ranges in cat_value_ranges.values()
    )

    if _logger.isEnabledFor(logging.DEBUG):
        for i, cat_value_ranges in enumerate(accepted_category_value_ranges):
            _logger.debug("i=%d, cat_value_ranges=%s", i, cat_value_ranges)
            lenghts: dict[_Category, int] = {
                cat: len(ranges[0]) for cat, ranges in cat_value_ranges.items()
            }
            _logger.debug("i=%d, range_lengths=%s", i, lenghts)

    return sum(
        math.prod(len(ranges[0]) for ranges in cat_value_ranges.values())
        for cat_value_ranges in accepted_category_value_ranges
    )


if __name__ == "__main__":
    run(p1, p2)
