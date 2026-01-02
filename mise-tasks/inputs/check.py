#!/usr/bin/env python3
# [MISE] description="Check local inputs/ directory contains recorded files"
# [USAGE] flag "-v --verbose" count=#true help="Enable verbose mode"
import json
import logging
import os
import pathlib
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_logger = logging.getLogger(os.environ.get("MISE_TASK_NAME", __name__))


def log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case _:
            return logging.DEBUG


class FileRecords:
    def __init__(self, repo_root: pathlib.Path) -> None:
        self._inputs_db_file = repo_root / "inputs.json"
        if self._inputs_db_file.exists():
            with self._inputs_db_file.open("r") as f:
                self._inputs_db = json.load(f)
        else:
            self._inputs_db = []

    def iter(self) -> Iterator[str]:
        yield from self._inputs_db


def get_local_inputs(repo_root: pathlib.Path) -> Iterator[str]:
    for file in repo_root.glob("inputs/*"):
        yield file.name


def main() -> bool:
    logging.basicConfig(level=log_level(int(os.environ.get("usage_verbose", "0"))))  # noqa: SIM112

    repo_root = pathlib.Path(__file__).parent.parent.parent

    file_records = FileRecords(repo_root)

    _logger.debug("Repo root: %s", repo_root)

    recorded_files = set(file_records.iter())
    local_files = set(get_local_inputs(repo_root))

    # Check for mismatches
    missing_files = recorded_files - local_files
    extra_files = local_files - recorded_files

    ret = True
    if missing_files:
        _logger.error("Missing files: %s", ", ".join(missing_files))
        ret = False
    if extra_files:
        _logger.error("Extra files: %s", ", ".join(extra_files))
        ret = False

    return ret


if __name__ == "__main__":
    if not main():
        sys.exit(1)
