from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
import typing
from dataclasses import dataclass

from aoc_main import _answers, _inputs, _logging, _solvers, _types

_logger = _logging.logger


@dataclass
class SolverExecResult:
    id_: _solvers.SolverId
    answer: _answers.AnswerType
    duration: float
    logs: list[str] | None


async def exec_solver(
    id_: _solvers.SolverId,
    info: _SolverExecInfo,
    verbosity: _types.Verbosity,
    *,
    dry_run: bool,
    capture_stderr: bool,
) -> SolverExecResult:
    input_file_path = _inputs.get_input_file_path(id_.year, id_.day)

    args = info.run_args[:]
    args.extend([str(verbosity), str(id_.part)])
    if dry_run:
        args.insert(0, "echo")

    working_directory = _solvers.get_solver_root_dir(id_.solver)

    env = os.environ.copy()
    info.adjust_run_environment(env)

    with input_file_path.open() as f:
        _logger.debug("Launching solver: '%s'", " ".join(args))
        _logger.debug("Working directory: %s", working_directory)
        start_time = time.perf_counter()
        proc = await asyncio.subprocess.create_subprocess_exec(
            *args,
            cwd=working_directory,
            env=env,
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if capture_stderr else None,
        )
        stdout_raw, stderr_raw = await proc.communicate()
    duration = time.perf_counter() - start_time

    assert proc.returncode is not None
    _logger.debug("%s: Return code: %d", id_, proc.returncode)
    _logger.debug("%s: Stdout: %s", id_, stdout_raw)
    _logger.debug("%s: Stderr: %s", id_, stderr_raw)
    stdout = stdout_raw.decode().strip()
    stderr = stderr_raw.decode().strip() if stderr_raw else ""

    if proc.returncode != 0:
        raise _SolverExecError(id_, proc.returncode, stdout, stderr)

    if dry_run:
        answer_raw = "0"
    else:
        output_lines = stdout.splitlines()
        assert len(output_lines) == 1
        output_line = output_lines[0]
        (answer_raw,) = output_line.split()

    answer: _answers.AnswerType
    try:
        answer = _answers.AnswerIntType(int(answer_raw))
    except ValueError:
        answer = _answers.AnswerStrType(answer_raw)
    logs = None
    if capture_stderr:
        assert stderr is not None
        logs = stderr.splitlines()
    return SolverExecResult(id_, answer, duration, logs)


class _SolverExecInfo(typing.Protocol):
    @property
    def run_args(self) -> list[str]: ...

    def adjust_run_environment(self, env: dict[str, str]) -> None: ...


class _SolverExecError(_solvers.SolverError):
    def __init__(
        self, id_: _solvers.SolverId, returncode: int, stdout: str, stderr: str | None
    ) -> None:
        self.id = id_
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.max_width = shutil.get_terminal_size().columns

    def __str__(self) -> str:
        ret = f"ERROR: Solver failure - {self.id} - Return code: {self.returncode}"
        max_len = min(
            self.max_width,
            max(
                len(line)
                for line in (self.stderr or "\n").splitlines()
                + (self.stdout or "\n").splitlines()
            ),
        )
        divider = "-" * max_len
        if self.stderr:
            ret += f"\nStderr:\n{divider}\n{self.stderr}\n{divider}"
        if self.stdout:
            ret += f"\nStdout:\n{divider}\n{self.stdout}\n{divider}"
        return ret
