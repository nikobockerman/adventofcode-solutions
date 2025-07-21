from __future__ import annotations

import asyncio
import json
import os
import pathlib
import platform
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from aoc_main import _logging, _solvers, _types

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = _logging.logger

_CPP_NEEDS_LIBRARY_BUILD = False


@dataclass(frozen=True, eq=True)
class _CppBinaryId:
    year: _types.Year
    day: _types.Day

    def cmake_target_name(self) -> str:
        return f"y{self.year}_d{self.day:02}"

    def __str__(self) -> str:
        return f"{self.year}-{self.day:02}"


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


class SolverCpp:
    def __init__(self, solver_ids: Iterable[_solvers.SolverId]) -> None:
        assert next(iter(solver_ids), None) is not None
        assert all(solver.solver == _solvers.Solver.Cpp for solver in solver_ids)

        workflow_preset_name = os.environ.get("AOC_CPP_WORKFLOW_PRESET")

        self._solver_root_dir = _solvers.get_solver_root_dir(_solvers.Solver.Cpp)
        binary_dir, configuration = self._resolve_binary_dir(
            self._solver_root_dir, workflow_preset_name
        )
        self._binary_dir = binary_dir
        self._configuration = configuration
        self._executable_suffix = ".exe" if platform.system() == "Windows" else ""

        self._binary_ids = {_CppBinaryId(id_.year, id_.day): id_ for id_ in solver_ids}

        self._cmake_env = os.environ.copy()
        self._cmake_env["CLICOLOR_FORCE"] = "1"

        self._skip_prepare = workflow_preset_name is not None

    async def prepare(self, *, dry_run: bool) -> None:
        if self._skip_prepare:
            return
        await self._cmake_configure(dry_run=dry_run)
        await self._build_library(dry_run=dry_run)
        await self._build_binaries(dry_run=dry_run)

    def get_exec_info(self, id_: _solvers.SolverId) -> _SolverExecInfoCpp:
        executable_dir = self._binary_dir
        if self._configuration is not None:
            executable_dir /= self._configuration

        executable_name = _CppBinaryId(id_.year, id_.day).cmake_target_name()
        executable_filename = f"{executable_name}{self._executable_suffix}"
        executable_path = (
            self._solver_root_dir / executable_dir / executable_filename
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
            "aoc",
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
            cwd=_solvers.get_solver_root_dir(_solvers.Solver.Cpp),
            env=self._cmake_env,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        assert proc.returncode is not None
        if proc.returncode != 0:
            _logger.error("CMake build failed: %s: %s", target_name, stdout.decode())
            raise _CMakeBuildError(target_name, proc.returncode)

    @staticmethod
    def _load_cmake_preset_file(preset_file: pathlib.Path) -> dict[str, Any]:
        if not preset_file.exists():
            return {}
        return json.loads(preset_file.read_text())

    @staticmethod
    def _get_preset(
        presets: dict[str, Any],
        preset_type: Literal["build", "configure", "workflow"],
        name: str,
    ) -> Any | None:  # noqa: ANN401
        return next(
            (
                preset
                for preset in presets.get(f"{preset_type}Presets", {})
                if preset["name"] == name
            ),
            None,
        )

    @staticmethod
    def _resolve_binary_dir(
        solver_root_dir: pathlib.Path, workflow_preset_name: str | None
    ) -> tuple[pathlib.Path, pathlib.Path | None]:
        cmake_user_presets = SolverCpp._load_cmake_preset_file(
            solver_root_dir / "CMakeUserPresets.json"
        )
        cmake_presets = SolverCpp._load_cmake_preset_file(
            solver_root_dir / "CMakePresets.json"
        )

        if workflow_preset_name is None:
            configure_preset_name = "aoc-base"
            configuration = None
        else:
            _logger.debug("Using workflow preset: %s", workflow_preset_name)
            workflow_preset = SolverCpp._get_preset(
                cmake_user_presets, "workflow", workflow_preset_name
            ) or SolverCpp._get_preset(cmake_presets, "workflow", workflow_preset_name)
            assert workflow_preset is not None
            configure_preset_name = next(
                step["name"]
                for step in workflow_preset["steps"]
                if step["type"] == "configure"
            )

            def get_build_configuration_name() -> str | None:
                build_preset_name = next(
                    step["name"]
                    for step in workflow_preset["steps"]
                    if step["type"] == "build"
                )
                build_preset = SolverCpp._get_preset(
                    cmake_user_presets, "build", build_preset_name
                ) or SolverCpp._get_preset(cmake_presets, "build", build_preset_name)
                return build_preset.get("configuration") if build_preset else None

            configuration_name = get_build_configuration_name()
            configuration = (
                pathlib.Path(configuration_name) if configuration_name else None
            )
            _logger.debug("Resolved build configuration: %s", configuration)

        _logger.debug("Using configure preset: %s", configure_preset_name)
        configure_preset = SolverCpp._get_preset(
            cmake_user_presets, "configure", configure_preset_name
        ) or SolverCpp._get_preset(cmake_presets, "configure", configure_preset_name)
        assert configure_preset is not None

        def _get_binary_dir(configure_preset: dict[str, Any]) -> str | None:
            binary_dir = configure_preset.get("binaryDir")
            if binary_dir is not None:
                _logger.debug("Found binaryDir: %s", binary_dir)
                return configure_preset["binaryDir"]

            for inherit in configure_preset.get("inherits", []):
                inherit_preset = SolverCpp._get_preset(
                    cmake_user_presets, "configure", inherit
                ) or SolverCpp._get_preset(cmake_presets, "configure", inherit)
                assert inherit_preset is not None
                _logger.debug("Locating binaryDir from inherited preset: %s", inherit)
                binary_dir = _get_binary_dir(inherit_preset)
                if binary_dir is not None:
                    return binary_dir

            return None

        binary_dir = _get_binary_dir(configure_preset)
        if binary_dir:
            return pathlib.Path(binary_dir), configuration
        error = "binaryDir not found"
        raise RuntimeError(error)


class _SolverExecInfoCpp:
    def __init__(self, executable: pathlib.Path) -> None:
        self._executable = executable

    @property
    def run_args(self) -> list[str]:
        return [str(self._executable)]

    def adjust_run_environment(self, env: dict[str, str]) -> None:
        pass
