import asyncio
import json
import os
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aoc_main import _logging, _solvers, _types

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = _logging.logger


@dataclass(frozen=True, eq=True)
class _CargoBinaryId:
    year: _types.Year
    day: _types.Day

    def cargo_bin_name(self) -> str:
        return f"y{self.year}_d{self.day:02}"

    def __str__(self) -> str:
        return f"{self.year}-{self.day:02}"


class _CargoBuildLibError(_solvers.SolverPrepareError):
    def __init__(self, returncode: int) -> None:
        super().__init__(
            _solvers.Solver.Rust,
            f"Rust library build failed. Return code: {returncode}",
        )


class _CargoBuildBinaryError(_solvers.SolverPrepareError):
    def __init__(self, id_: _CargoBinaryId, returncode: int) -> None:
        super().__init__(
            _solvers.Solver.Rust,
            f"Rust binary build failed. Binary: {id_}; Return code: {returncode}",
        )


class SolverRust:
    def __init__(self, solver_ids: Iterable[_solvers.SolverId]) -> None:
        self._build_args = os.getenv("AOC_RUST_BUILD_ARGS", "--release --quiet").split()
        self._executables_by_id: dict[_CargoBinaryId, pathlib.Path | None] = {
            _CargoBinaryId(id_.year, id_.day): None for id_ in solver_ids
        }

    async def prepare(self, *, dry_run: bool) -> None:
        await self._build_library(dry_run=dry_run)
        await self._build_binaries(dry_run=dry_run)

    def get_exec_info(self, id_: _solvers.SolverId) -> _SolverExecInfoRust:
        executable = self._executables_by_id[_CargoBinaryId(id_.year, id_.day)]
        assert executable is not None
        return _SolverExecInfoRust(executable)

    async def _build_library(self, *, dry_run: bool) -> None:
        args = [
            "mise",
            "exec",
            "--",
            "cargo",
            "build",
            "--lib",
            *self._build_args,
        ]
        if dry_run:
            args.insert(0, "echo")
        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=_solvers.get_solver_root_dir(_solvers.Solver.Rust),
        )
        returncode = await proc.wait()
        if returncode != 0:
            raise _CargoBuildLibError(returncode)

    async def _build_binaries(self, *, dry_run: bool) -> None:
        assert all(
            executable is None for executable in self._executables_by_id.values()
        )
        results = await asyncio.gather(
            *(
                asyncio.create_task(self._build_binary(id_, dry_run=dry_run))
                for id_ in self._executables_by_id
            )
        )
        for id_, executable in results:
            self._executables_by_id[id_] = executable

    async def _build_binary(
        self, id_: _CargoBinaryId, *, dry_run: bool
    ) -> tuple[_CargoBinaryId, pathlib.Path]:
        args = [
            "mise",
            "exec",
            "--",
            "cargo",
            "build",
            f"--bin={id_.cargo_bin_name()}",
            *self._build_args,
        ]
        _logger.info("Building rust binary for %s", id_)
        _logger.debug("Cargo build: %s", args)
        if dry_run:
            args.insert(0, "echo")
        cwd = _solvers.get_solver_root_dir(_solvers.Solver.Rust)
        proc = await asyncio.subprocess.create_subprocess_exec(*args, cwd=cwd)
        returncode = await proc.wait()
        if returncode != 0:
            raise _CargoBuildBinaryError(id_, returncode)

        if dry_run:
            return id_, cwd / "dry-run-executable"

        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            "--message-format=json",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode == 0

        executable = None
        for line in stdout.splitlines():
            item = json.loads(line)
            _logger.debug("item=%s", item)
            target = item.get("target")
            if target is None:
                continue
            if target["kind"][0] == "bin":
                executable = item["executable"]
                assert isinstance(executable, str)
                break
        assert executable is not None
        executable_path = pathlib.Path(executable)
        _logger.info("Built rust binary for %s", id_)
        _logger.debug("Buidl Rust binary: %s: %s", id_, executable_path)
        return id_, executable_path


class _SolverExecInfoRust:
    def __init__(self, executable: pathlib.Path) -> None:
        self._executable = executable

    @property
    def run_args(self) -> list[str]:
        return [str(self._executable)]

    def adjust_run_environment(self, env: dict[str, str]) -> None:
        env["RUST_BACKTRACE"] = "1"
