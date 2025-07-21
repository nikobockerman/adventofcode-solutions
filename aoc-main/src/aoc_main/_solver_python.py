from __future__ import annotations

import asyncio
import os

from aoc_main import _logging, _solvers

_logger = _logging.logger


class _UvSyncError(_solvers.SolverPrepareError):
    def __init__(self, returncode: int) -> None:
        super().__init__(
            _solvers.Solver.Cpp,
            f"uv sync failed. Return code: {returncode}",
        )


class SolverPython:
    def __init__(self) -> None:
        pass

    async def prepare(self, *, dry_run: bool) -> None:
        await self._uv_sync(dry_run=dry_run)

    async def _uv_sync(self, *, dry_run: bool) -> None:
        _logger.info("CMake configure")
        args = ["mise", "exec", "--", "uv", "sync", "--inexact", "--frozen"]
        if dry_run:
            args.insert(0, "echo")

        env = os.environ.copy()
        del env["VIRTUAL_ENV"]

        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=_solvers.get_solver_root_dir(_solvers.Solver.Python),
            env=env,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode is not None
        if proc.returncode != 0:
            _logger.error("uv sync failed: %s", stdout.decode())
            raise _UvSyncError(proc.returncode)

    def get_exec_info(self, id_: _solvers.SolverId) -> _SolverExecInfoPython:
        return _SolverExecInfoPython(f"aoc.y{id_.year}.d{id_.day:02}")


class _SolverExecInfoPython:
    def __init__(self, module_name: str) -> None:
        self._module_name = module_name

    @property
    def run_args(self) -> list[str]:
        return ["mise", "exec", "--", "uv", "run", "python", "-m", self._module_name]

    def adjust_run_environment(self, env: dict[str, str]) -> None:
        del env["VIRTUAL_ENV"]
