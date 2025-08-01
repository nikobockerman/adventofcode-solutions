from aoc_main._solvers import Solver, SolverId
from aoc_main._types import Day, Year


def test_solver_id() -> None:
    assert str(SolverId(Year(2022), Day(1), 1, Solver.Python)) == "2022-1-1-python"
