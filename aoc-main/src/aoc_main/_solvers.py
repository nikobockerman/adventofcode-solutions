import enum
import functools
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from aoc_main import _logging, _types, _utils

if TYPE_CHECKING:
    import pathlib

_logger = _logging.logger


class Solver(enum.StrEnum):
    Cpp = "cpp"
    Python = "python"
    Rust = "rust"


@dataclass(frozen=True)
class SolverId:
    year: _types.Year
    day: _types.Day
    part: _types.Part
    solver: Solver

    def __str__(self) -> str:
        return f"{self.year}-{self.day}-{self.part}-{self.solver}"


def get_solver_root_dir(solver: Solver) -> pathlib.Path:
    return _utils.get_repo_root() / "solvers" / str(solver)


class SolverError(RuntimeError):
    pass


class SolverPrepareError(SolverError):
    def __init__(self, solver: Solver, message: str) -> None:
        super().__init__(f"Solver prepare failed for {solver}: {message}")


@functools.cache
def _read_solvers() -> dict[_types.PartId, list[Solver]]:
    yaml_ = yaml.safe_load((_utils.get_repo_root() / "solvers.yaml").read_text())
    _logger.debug("Read solvers: %s", yaml_)
    data: dict[_types.PartId, list[Solver]] = {}
    for year, days in yaml_.items():
        assert isinstance(year, int)
        for day, parts in days.items():
            assert isinstance(day, int)
            for part, yaml_solvers in parts.items():
                assert isinstance(part, int)
                assert _types.is_part(part)

                solvers: list[Solver]
                if isinstance(yaml_solvers, str):
                    assert yaml_solvers in Solver
                    solvers = [Solver(yaml_solvers)]
                else:
                    assert isinstance(yaml_solvers, list)
                    solvers = []
                    for yaml_solver in yaml_solvers:  # pyright: ignore[reportUnknownVariableType]
                        assert isinstance(yaml_solver, str)
                        assert yaml_solver in Solver
                        solvers.append(Solver(yaml_solver))

                assert solvers
                data[_types.PartId(_types.Year(year), _types.Day(day), part)] = solvers

    return data


def get_solvers(id_: _types.PartId) -> list[SolverId]:
    return [
        SolverId(id_.year, id_.day, id_.part, solver) for solver in _read_solvers()[id_]
    ]
