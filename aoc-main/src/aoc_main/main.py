import asyncio
import logging
import sys
import time
import typing
from collections import defaultdict
from dataclasses import dataclass
from typing import NewType

from aoc_main import (
    _answers,
    _exec_solver,
    _logging,
    _solver_cpp,
    _solver_python,
    _solver_rust,
    _solvers,
    _types,
)

if typing.TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

_logger = _logging.logger


def async_main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    mode, verbosity_arg, dry_run_arg, solver_arg, *argv = sys.argv[1:]
    behavior = _Behavior(
        _parse_verbosity_arg(verbosity_arg),
        _parse_dry_run_arg(dry_run_arg),
        _parse_solver_arg(solver_arg),
    )
    level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[behavior.verbosity]
    logging.basicConfig(level=level)
    try:
        match mode:
            case "one":
                exit_code = await single(argv, behavior)
            case "day":
                exit_code = await day_(argv, behavior)
            case "all":
                exit_code = await all_(behavior)
            case _:
                print("Unknown mode", file=sys.stderr)
                exit_code = _ExitCode(1)
    except _solvers.SolverError as e:
        print(e, file=sys.stderr)
        exit_code = _ExitCode(1)

    sys.exit(exit_code)


_ExitCode = NewType("_ExitCode", int)


@dataclass
class _Behavior:
    verbosity: _types.Verbosity
    dry_run: bool
    solver: _solvers.Solver | None


def _parse_verbosity_arg(verbosity_arg: str) -> _types.Verbosity:
    verbosity_num = int(verbosity_arg)
    assert _types.is_verbosity(verbosity_num)
    return verbosity_num


def _parse_dry_run_arg(dry_run_arg: str) -> bool:
    assert dry_run_arg in ("true", "false")
    return dry_run_arg == "true"


def _parse_solver_arg(solver_arg: str) -> _solvers.Solver | None:
    if solver_arg:
        return _solvers.Solver(solver_arg)
    return None


async def all_(behavior: _Behavior) -> _ExitCode:
    return await _solve_many_parts(
        _answers.get_part_ids_for_all_known_answers(), behavior
    )


async def day_(argv: list[str], behavior: _Behavior) -> _ExitCode:
    year, day = map(int, argv)
    return await _solve_many_parts(
        _answers.get_part_ids_for_known_answers_for_one_day(
            _types.Year(year), _types.Day(day)
        ),
        behavior,
    )


async def single(argv: list[str], behavior: _Behavior) -> _ExitCode:
    year, day, part = map(int, argv)
    assert _types.is_part(part)
    id_ = _types.PartId(_types.Year(year), _types.Day(day), part)
    solver_ids = get_solver_ids([id_], behavior.solver)
    if len(solver_ids) > 1:
        return await _solve_many_parts([id_], behavior)

    return await _solve_one_solver(solver_ids[0], behavior)


def get_solver_ids(
    part_ids: Iterable[_types.PartId], solver: _solvers.Solver | None
) -> list[_solvers.SolverId]:
    return [
        solver_id
        for part_id in part_ids
        for solver_id in _solvers.get_solvers(part_id)
        if solver is None or solver_id.solver == solver
    ]


async def _solve_one_solver(id_: _solvers.SolverId, behavior: _Behavior) -> _ExitCode:
    solvers = _Solvers([id_])
    results = [
        result
        async for result in solvers.process_solvers(behavior, capture_stderr=False)
    ]
    assert len(results) == 1
    result = results[0]

    print(f"Duration: {result.duration:.3f}s")
    if result.incorrect:
        print(
            f"Incorrect answer: {result.answer}. Correct is: {result.correct_answer}",
            file=sys.stderr,
        )
        return _ExitCode(2)
    if result.correct:
        print(f"Answer is still correct: {result.answer}")
    else:
        print(result.answer)
    return _ExitCode(0)


async def _solve_many_parts(
    part_ids: Iterable[_types.PartId],
    behavior: _Behavior,
) -> _ExitCode:
    all_passed = None
    slowest = None
    start = time.perf_counter()

    solvers = _Solvers(get_solver_ids(part_ids, behavior.solver))

    async for result in solvers.process_solvers(behavior, capture_stderr=True):
        passed = _report_one_of_many_results(result)
        if all_passed is None:
            all_passed = passed
        all_passed &= passed
        assert result.duration is not None
        if slowest is None:
            slowest = result
        else:
            assert slowest.duration is not None
            if result.duration > slowest.duration:
                slowest = result

    duration = time.perf_counter() - start

    if slowest is not None:
        print(
            f"Slowest: {slowest.id.year} {slowest.id.day:2} {slowest.id.part}: "
            f"{slowest.duration:.3f}s"
        )

    if all_passed is None:
        print(f"No answers known. Duration {duration:.3f}s")
        return _ExitCode(0)

    if all_passed:
        print(f"Finished with all passing. Duration {duration:.3f}s")
        return _ExitCode(0)

    print(f"Finished with failures. Duration {duration:.3f}s")
    return _ExitCode(1)


def _report_one_of_many_results(result: _SolverResult) -> bool:
    msg = f"{result.id.year} {result.id.day:2} {result.id.part} {result.id.solver}: "
    logs = result.logs
    assert logs is not None
    if logs:
        print(f"{msg} LOGS:")
        for log in logs:
            print(f"    {log}")
    msg += f"{result.duration:.3f}s: "
    if result.incorrect:
        msg += (
            f"FAIL: Incorrect answer: {result.answer}. "
            f"Correct is: {result.correct_answer}"
        )
    else:
        msg += "PASS"
    print(msg)
    return not result.incorrect


class _Solvers:
    def __init__(self, solver_ids: list[_solvers.SolverId]) -> None:
        assert len(solver_ids) == len(set(solver_ids))

        _logger.debug("Solver IDs: %s", solver_ids)

        solver_types_by_id: dict[_solvers.SolverId, _solvers.Solver] = {}
        solver_ids_by_type: dict[_solvers.Solver, list[_solvers.SolverId]] = (
            defaultdict(list)
        )
        for id_ in solver_ids:
            solver_ids_by_type[id_.solver].append(id_)
            solver_types_by_id[id_] = id_.solver

        solvers_by_type: dict[
            _solvers.Solver,
            _solver_cpp.SolverCpp
            | _solver_python.SolverPython
            | _solver_rust.SolverRust,
        ] = {}
        for type_ in _solvers.Solver:
            solver_ids_for_type = solver_ids_by_type.get(type_)
            if not solver_ids_for_type:
                continue

            match type_:
                case _solvers.Solver.Cpp:
                    solvers_by_type[type_] = _solver_cpp.SolverCpp(solver_ids_for_type)
                case _solvers.Solver.Python:
                    solvers_by_type[type_] = _solver_python.SolverPython()
                case _solvers.Solver.Rust:
                    solvers_by_type[type_] = _solver_rust.SolverRust(
                        solver_ids_for_type
                    )

        self._solvers_for_ids: dict[
            _solvers.SolverId,
            _solver_cpp.SolverCpp
            | _solver_python.SolverPython
            | _solver_rust.SolverRust,
        ] = {
            id_: solvers_by_type[solver_type]
            for id_, solver_type in solver_types_by_id.items()
        }
        assert len(self._solvers_for_ids.keys()) == len(solver_ids)
        assert set(self._solvers_for_ids.keys()) == set(solver_ids)

        self._solvers = set(solvers_by_type.values())

    async def process_solvers(
        self,
        behavior: _Behavior,
        *,
        capture_stderr: bool,
    ) -> AsyncIterator[_SolverResult]:
        await asyncio.gather(
            *(
                asyncio.create_task(solver.prepare(dry_run=behavior.dry_run))
                for solver in self._solvers
            )
        )

        tasks = [
            asyncio.create_task(
                _exec_solver.exec_solver(
                    id_,
                    solver.get_exec_info(id_),
                    behavior.verbosity,
                    dry_run=behavior.dry_run,
                    capture_stderr=capture_stderr,
                )
            )
            for id_, solver in self._solvers_for_ids.items()
        ]

        async for task in asyncio.as_completed(tasks):
            exec_result = await task
            yield _create_solver_result(exec_result, behavior)


@dataclass(frozen=True)
class _SolverResult:
    id: _solvers.SolverId
    answer: _answers.AnswerType
    duration: float
    correct_answer: _answers.AnswerType | None
    logs: list[str] | None = None

    @property
    def correct(self) -> bool:
        return self.correct_answer is not None and self.correct_answer == self.answer

    @property
    def incorrect(self) -> bool:
        return self.correct_answer is not None and self.answer != self.correct_answer


def _create_solver_result(
    result: _exec_solver.SolverExecResult, behavior: _Behavior
) -> _SolverResult:
    correct_answer = _answers.get_correct_answer(result.id_)
    if behavior.dry_run:
        correct_answer = result.answer
    return _SolverResult(
        result.id_,
        result.answer,
        result.duration,
        correct_answer,
        result.logs,
    )
