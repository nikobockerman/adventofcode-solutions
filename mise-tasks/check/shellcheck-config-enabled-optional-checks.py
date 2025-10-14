#!/usr/bin/env python3
# MISE description="Check shellcheck config enables all but disabled optional checks"

import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

DISABLED_OPTIONAL_CHECKS = ["check-unassigned-uppercase"]

# ruff: noqa: T201


def get_all_shellcheck_enabled_optional_checks() -> Iterable[str]:
    enabled = list(
        filter(
            lambda x: x.startswith("enable="),
            pathlib.Path(".shellcheckrc").read_text().splitlines(),
        )
    )
    assert len(enabled) == 1
    yield from enabled[0][7:].strip().split(",")


def get_all_shellcheck_optional_checks() -> Iterable[str]:
    result = subprocess.run(
        ["shellcheck", "--list-optional"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    for name in filter(lambda x: x.startswith("name:"), result.stdout.splitlines()):
        yield name[5:].strip()


def main() -> bool:
    disabled_checks = set(DISABLED_OPTIONAL_CHECKS)
    enabled_checks = set(get_all_shellcheck_enabled_optional_checks())
    all_checks = set(get_all_shellcheck_optional_checks())
    expected_checks = all_checks - disabled_checks

    unsupported_disabled_checks = disabled_checks - all_checks
    if unsupported_disabled_checks:
        msg = ", ".join(sorted(unsupported_disabled_checks))
        print(
            f"DISABLED_OPTIONAL_CHECKS has checks that are not supported: {msg}",
            file=sys.stderr,
        )
        return False

    new_checks = expected_checks - enabled_checks
    if new_checks:
        msg = ", ".join(sorted(new_checks))
        print(
            f"Shellcheck config is missing optional checks: {msg}",
            file=sys.stderr,
        )
        return False

    removed_checks = enabled_checks - expected_checks
    if removed_checks:
        msg = ", ".join(sorted(removed_checks))
        print(
            f"Shellcheck config has optional checks that are not supported: {msg}",
            file=sys.stderr,
        )
        return False

    return True


if __name__ == "__main__":
    if not main():
        sys.exit(1)
