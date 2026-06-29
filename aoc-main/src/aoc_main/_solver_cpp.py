import asyncio
import os
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from aoc_main import _cmake_presets, _logging, _solvers, _types

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

_logger = _logging.logger

_CPP_NEEDS_LIBRARY_BUILD = False

_ENV_SKIP_PREPARE = "AOC_CPP_SKIP_PREPARE"

_ENV_PRESET_CONFIGURE = "AOC_CPP_PRESET"
_ENV_PRESET_WORKFLOW = "AOC_CPP_WORKFLOW_PRESET"

_DEFAULT_CONFIGURE_PRESET = "aoc"


@dataclass(frozen=True, eq=True)
class _CppBinaryId:
    year: _types.Year
    day: _types.Day

    def cmake_target_name(self) -> str:
        return f"y{self.year}_d{self.day:02}"

    def __str__(self) -> str:
        return f"{self.year}-{self.day:02}"


class _CppSolverConfigureError(_solvers.SolverPrepareError):
    def __init__(self, message: str) -> None:
        super().__init__(_solvers.Solver.Cpp, message)


class _CMakeConfigureError(_solvers.SolverPrepareError):
    def __init__(self, returncode: int) -> None:
        super().__init__(
            _solvers.Solver.Cpp,
            f"CMake configure failed. Return code: {returncode}",
        )


class _CMakeBuildError(_solvers.SolverPrepareError):
    def __init__(self, target: str, returncode: int) -> None:
        super().__init__(
            _solvers.Solver.Cpp,
            f"CMake build failed. Target: {target}; Return code: {returncode}",
        )


class _CMakeConfigResolver:
    """Selects which CMake presets to use, then defers parsing to ``CMakePresets``.

    The *selection* (which configure or workflow preset to use, read from
    environment variables) lives here; the *parsing* of the preset files lives
    in :mod:`aoc_main._cmake_presets`.
    """

    @cached_property
    def solver_root_dir(self) -> pathlib.Path:
        return _solvers.get_solver_root_dir(_solvers.Solver.Cpp)

    @cached_property
    def _presets(self) -> _cmake_presets.CMakePresets:
        return _cmake_presets.CMakePresets(self.solver_root_dir)

    @cached_property
    def configure_preset_name(self) -> str:
        return self._resolve_configure_preset()

    @cached_property
    def binary_dir(self) -> pathlib.Path:
        try:
            return self._presets.binary_dir(self.configure_preset_name)
        except _cmake_presets.CMakePresetError as e:
            raise _CppSolverConfigureError(str(e)) from e

    def _resolve_configure_preset(self) -> str:
        configure_preset_name = os.environ.get(_ENV_PRESET_CONFIGURE)
        if configure_preset_name is not None:
            _logger.debug("Using specified configure preset: %s", configure_preset_name)
            return configure_preset_name

        workflow_preset_name = os.environ.get(_ENV_PRESET_WORKFLOW)
        if workflow_preset_name is None:
            _logger.debug(
                "Using default configure preset: %s", _DEFAULT_CONFIGURE_PRESET
            )
            return _DEFAULT_CONFIGURE_PRESET

        _logger.debug("Using workflow preset: %s", workflow_preset_name)
        try:
            configure_preset_name = self._presets.workflow_configure_preset_name(
                workflow_preset_name
            )
        except _cmake_presets.CMakePresetError as e:
            raise _CppSolverConfigureError(str(e)) from e

        _logger.debug("Using configure preset: %s", configure_preset_name)
        return configure_preset_name


class SolverCpp:
    def __init__(self, solver_ids: Iterable[_solvers.SolverId]) -> None:
        assert next(iter(solver_ids), None) is not None
        assert all(solver.solver == _solvers.Solver.Cpp for solver in solver_ids)

        self._cmake_config_resolver = _CMakeConfigResolver()
        self._binary_ids = {_CppBinaryId(id_.year, id_.day): id_ for id_ in solver_ids}
        self._skip_prepare = os.environ.get(_ENV_SKIP_PREPARE, "0") != "0"

    @cached_property
    def _binary_dir(self) -> pathlib.Path:
        return self._cmake_config_resolver.binary_dir

    @cached_property
    def _solver_root_dir(self) -> pathlib.Path:
        return self._cmake_config_resolver.solver_root_dir

    @cached_property
    def _configure_preset_name(self) -> str:
        return self._cmake_config_resolver.configure_preset_name

    @cached_property
    def _cmake_env(self) -> dict[str, str]:
        cmake_env = os.environ.copy()
        cmake_env["CLICOLOR_FORCE"] = "1"
        return cmake_env

    async def prepare(self, *, dry_run: bool) -> None:
        if self._skip_prepare:
            return
        await self._cmake_configure(dry_run=dry_run)
        await self._build_library(dry_run=dry_run)
        await self._build_binaries(dry_run=dry_run)

    def get_exec_info(self, id_: _solvers.SolverId) -> _SolverExecInfoCpp:
        executable_dir = self._binary_dir
        executable_name = _CppBinaryId(id_.year, id_.day).cmake_target_name()
        executable_path = (
            self._solver_root_dir / executable_dir / executable_name
        ).resolve()

        return _SolverExecInfoCpp(executable_path)

    async def _cmake_configure(self, *, dry_run: bool) -> None:
        _logger.info("CMake configure")
        args = [
            "mise",
            "exec",
            "--",
            "cmake",
            "--log-level=ERROR",
            "--preset",
            self._configure_preset_name,
        ]
        if dry_run:
            args.insert(0, "echo")

        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=self._solver_root_dir,
            env=self._cmake_env,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode is not None
        if proc.returncode != 0:
            _logger.error("CMake configure failed: %s", stdout.decode())
            raise _CMakeConfigureError(proc.returncode)

    async def _build_library(self, *, dry_run: bool) -> None:
        if not _CPP_NEEDS_LIBRARY_BUILD:
            return

        target_name = "lib"
        _logger.info("CMake library build")
        args = [
            "mise",
            "exec",
            "--",
            "cmake",
            "--build",
            str(self._binary_dir),
            "--target",
            target_name,
        ]
        if dry_run:
            args.insert(0, "echo")
        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=self._solver_root_dir,
            env=self._cmake_env,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode is not None
        if proc.returncode != 0:
            _logger.error("CMake library build failed: %s", stdout.decode())
            raise _CMakeBuildError(target_name, proc.returncode)

    async def _build_binaries(self, *, dry_run: bool) -> None:
        await asyncio.gather(
            *(
                asyncio.create_task(self._build_binary(id_, dry_run=dry_run))
                for id_ in self._binary_ids
            )
        )

    async def _build_binary(self, id_: _CppBinaryId, *, dry_run: bool) -> None:
        target_name = id_.cmake_target_name()
        _logger.info("Building cpp solver: %s", target_name)
        args = [
            "mise",
            "exec",
            "--",
            "cmake",
            "--build",
            str(self._binary_dir),
            "--target",
            target_name,
            "--",
            "--quiet",
        ]
        if dry_run:
            args.insert(0, "echo")
        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=self._solver_root_dir,
            env=self._cmake_env,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode is not None
        if proc.returncode != 0:
            _logger.error("CMake build failed: %s: %s", target_name, stdout.decode())
            raise _CMakeBuildError(target_name, proc.returncode)


class _SolverExecInfoCpp:
    def __init__(self, executable: pathlib.Path) -> None:
        self._executable = executable

    @property
    def run_args(self) -> list[str]:
        return [str(self._executable)]

    def adjust_run_environment(self, env: dict[str, str]) -> None:
        pass
