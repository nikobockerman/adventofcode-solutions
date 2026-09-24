#!/usr/bin/env python3
"""Generate the Rust CI build matrix."""

import argparse
import functools
import json
import sys
from dataclasses import dataclass
from typing import Literal, get_args

type _OS = Literal["macos", "ubuntu"]
type _Profile = Literal["dev", "release", "test"]


# Runner image hosting each operating system.
@functools.cache
def _runners() -> dict[_OS, str]:
    return {"macos": "macos-15", "ubuntu": "ubuntu-24.04"}


# Every scenario CI runs.
@functools.cache
def _matrix() -> tuple[_MatrixEntry, ...]:
    return tuple(
        _MatrixEntry(os_, profile)
        for os_ in get_args(_OS.evaluate_value())
        for profile in get_args(_Profile.evaluate_value())
    )


@dataclass(frozen=True)
class _MatrixEntry:
    os: _OS
    profile: _Profile

    @property
    def clippy(self) -> bool:
        return self.profile == "dev"

    @property
    def run(self) -> bool:
        return self.profile != "test"

    @property
    def test(self) -> bool:
        return self.profile == "test"

    @property
    def run_id(self) -> str:
        return f"{self.os}-{self.profile}"


def _github_include(entry: _MatrixEntry) -> dict[str, bool | str]:
    return {
        "os": entry.os,
        "profile": entry.profile,
        "clippy": entry.clippy,
        "run": entry.run,
        "test": entry.test,
        "runId": entry.run_id,
        "runsOn": _runners()[entry.os],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("matrix", help="Print the workflow build matrix as JSON")

    return parser.parse_args()


def _emit_matrix() -> None:
    include = [_github_include(entry) for entry in _matrix()]

    # Ensure that each matrix entry has a unique runId.
    run_ids = {entry["runId"] for entry in include}
    if len(run_ids) != len(include):
        msg = "runId values are not unique"
        raise ValueError(msg)

    # Output in one line for easy consumption in GitHub Actions.
    print(json.dumps({"include": include}))


def main() -> int:
    args = _parse_args()
    if args.command == "matrix":
        _emit_matrix()
    return 0


if __name__ == "__main__":
    sys.exit(main())
