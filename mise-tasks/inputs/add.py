#!/usr/bin/env python3
# ruff: noqa: E501
# [MISE] description="Move input file for new solution to local directory and to encrypted tarball for CI use"
# [USAGE] arg "<year>" help="Problem year of the input file"
# [USAGE] arg "<day>" help "Problem day of the input file" {
# [USAGE]     choices "1" "2" "3" "4" "5" "6" "7" "8" "9" "10" "11" "12" "13" "14" "15" "16" "17" "18" "19" "20" "21" "22" "23" "24" "25"
# [USAGE] }
# [USAGE] arg "<file>" help="Input file to add"
# [USAGE] flag "-v --verbose" count=#true help="Enable verbose mode"
import json
import logging
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_logger = logging.getLogger(os.environ.get("MISE_TASK_NAME", __name__))


def log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case _:
            return logging.DEBUG


def move_file_to_local_directory(
    file: pathlib.Path, repo_root: pathlib.Path, target_file_name: str
) -> bool:
    inputs_dir = repo_root / "inputs"
    target_file = inputs_dir / target_file_name
    if target_file.exists():
        _logger.error("File %s already exists", target_file)
        return False

    _logger.debug("Moving file to local directory: %s -> %s", file, target_file)
    inputs_dir.mkdir(exist_ok=True)
    file.rename(target_file)

    return True


class FileRecords:
    def __init__(self, repo_root: pathlib.Path) -> None:
        self._inputs_db_file = repo_root / "inputs.json"
        if self._inputs_db_file.exists():
            with self._inputs_db_file.open("r") as f:
                self._inputs_db = json.load(f)
        else:
            self._inputs_db = []

    def contains(self, target_file_name: str) -> bool:
        return target_file_name in self._inputs_db

    def add(self, target_file_name: str) -> None:
        assert not self.contains(target_file_name), (
            f"File {target_file_name} already exists"
        )

        _logger.debug("Recording new file: %s", target_file_name)
        self._inputs_db.append(target_file_name)
        self._inputs_db.sort()

    def flush(self) -> None:
        self._write()

    def iter(self) -> Iterator[str]:
        yield from self._inputs_db

    def _write(self) -> None:
        with self._inputs_db_file.open("w") as f:
            json.dump(self._inputs_db, f, indent=2)
            f.write("\n")


class EncryptedInputFiles:
    def __init__(self, repo_root: pathlib.Path) -> None:
        self._encrypted_file = repo_root / "inputs.tar.gpg"

    def create(self, input_file_names: Iterable[str], encryption_key: str) -> bool:
        with tempfile.NamedTemporaryFile("wb", suffix=".tar") as tmp:
            _logger.debug("Creating tarball: %s", tmp.name)
            with tarfile.open(fileobj=tmp, mode="w") as tar:
                for file_name in input_file_names:
                    tar.add(f"inputs/{file_name}", recursive=False)
            tmp.flush()

            backup_file: pathlib.Path | None = None
            try:
                if self._encrypted_file.exists():
                    backup_file = self._encrypted_file.parent / (
                        self._encrypted_file.name + ".bak"
                    )
                    self._encrypted_file.rename(backup_file)

                subprocess.run(  # noqa: S603
                    [  # noqa: S607
                        "gpg",
                        "--symmetric",
                        "--cipher-algo",
                        "AES256",
                        "--batch",
                        "--passphrase-fd",
                        "0",
                        "--output",
                        str(self._encrypted_file),
                        tmp.name,
                    ],
                    check=True,
                    input=encryption_key,
                    text=True,
                )

                if backup_file:
                    backup_file.unlink()
            except subprocess.CalledProcessError:
                _logger.exception("Encryption error: %s")
                if backup_file:
                    backup_file.rename(self._encrypted_file)
                return False
        return True


def main() -> bool:
    logging.basicConfig(level=log_level(int(os.environ.get("usage_verbose", "0"))))  # noqa: SIM112

    encryption_key = os.environ.get("ENCRYPTION_KEY")
    if not encryption_key:
        _logger.error(
            "Encryption key not specified in ENCRYPTION_KEY environment variable"
        )
        return False

    year = int(os.environ["usage_year"])  # noqa: SIM112
    day = int(os.environ["usage_day"])  # noqa: SIM112
    file = pathlib.Path(os.environ["usage_file"])  # noqa: SIM112

    if not file.exists():
        _logger.error("File %s does not exist", file)
        return False

    repo_root = pathlib.Path(__file__).parent.parent.parent
    target_file_name = f"{year}-{day:02}.txt"

    file_records = FileRecords(repo_root)
    if file_records.contains(target_file_name):
        _logger.error("File %s already recorded", target_file_name)
        return False

    _logger.debug("Input file: %s", file)
    _logger.debug("Year: %s", year)
    _logger.debug("Day: %s", day)
    _logger.debug("Repo root: %s", repo_root)
    _logger.debug("Target file name: %s", target_file_name)

    if not move_file_to_local_directory(file, repo_root, target_file_name):
        return False

    file_records.add(target_file_name)

    encrypted_input_files = EncryptedInputFiles(repo_root)
    if encrypted_input_files.create(file_records.iter(), encryption_key):
        file_records.flush()

    return True


if __name__ == "__main__":
    if not main():
        sys.exit(1)
