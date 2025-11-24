import asyncio
import json
import os
import pathlib
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal

from aoc_main import _logging, _solvers, _types

if TYPE_CHECKING:
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
    @cached_property
    def configure_preset_name(self) -> str:
        return self._resolve_configure_preset()

    @cached_property
    def solver_root_dir(self) -> pathlib.Path:
        return _solvers.get_solver_root_dir(_solvers.Solver.Cpp)

    @cached_property
    def binary_dir(self) -> pathlib.Path:
        return self._resolve_binary_dir()

    @cached_property
    def _cmake_user_presets(self) -> dict[str, Any]:
        return self._load_cmake_preset_file(
            self.solver_root_dir / "CMakeUserPresets.json"
        )

    @cached_property
    def _cmake_presets(self) -> dict[str, Any]:
        return self._load_cmake_preset_file(self.solver_root_dir / "CMakePresets.json")

    @staticmethod
    def _load_cmake_preset_file(preset_file: pathlib.Path) -> dict[str, Any]:
        if not preset_file.exists():
            return {}
        return json.loads(preset_file.read_text())

    def _get_preset(
        self,
        preset_type: Literal["build", "configure", "workflow"],
        name: str,
    ) -> Any | None:  # noqa: ANN401
        for presets in (self._cmake_user_presets, self._cmake_presets):
            preset = next(
                (
                    preset
                    for preset in presets.get(f"{preset_type}Presets", {})
                    if preset["name"] == name
                ),
                None,
            )
            if preset is not None:
                return preset
        return None

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
        workflow_preset = self._get_preset("workflow", workflow_preset_name)
        if workflow_preset is None:
            msg = f"Requested workflow preset not found: {workflow_preset_name}"
            raise _CppSolverConfigureError(msg)

        try:
            configure_preset_name = next(
                step["name"]
                for step in workflow_preset["steps"]
                if step["type"] == "configure"
            )
        except KeyError as e:
            msg = (
                f"Invalid CMake Preset json for workflow preset: {workflow_preset_name}"
            )
            raise _CppSolverConfigureError(msg) from e
        except StopIteration:
            msg = f"No configure step found for workflow: {workflow_preset_name}"
            raise _CppSolverConfigureError(msg) from None

        _logger.debug("Using configure preset: %s", configure_preset_name)
        assert configure_preset_name is not None
        return configure_preset_name

    def _resolve_binary_dir(self) -> pathlib.Path:
        configure_preset_names = [self.configure_preset_name]
        while configure_preset_names:
            configure_preset_name = configure_preset_names.pop(0)
            configure_preset = self._get_preset("configure", configure_preset_name)
            if configure_preset is None:
                msg = f"Configure preset not found: {configure_preset_name}"
                raise _CppSolverConfigureError(msg)

            binary_dir = configure_preset.get("binaryDir")
            if binary_dir is not None:
                _logger.debug(
                    "Found binaryDir from preset %s: %s",
                    configure_preset_name,
                    binary_dir,
                )
                return pathlib.Path(binary_dir)

            _logger.debug(
                "Binary dir not found for preset %s. Checking inherited presets",
                configure_preset_name,
            )
            configure_preset_names.extend(configure_preset.get("inherits", []))

        error = f"binaryDir not found for configure preset {self.configure_preset_name}"
        raise _CppSolverConfigureError(error)


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
