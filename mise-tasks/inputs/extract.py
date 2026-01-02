#!/usr/bin/env python3
# [MISE] description="Extract encrypted input files to local directory"
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


class EncryptedInputFiles:
    def __init__(self, repo_root: pathlib.Path, inputs_dir: pathlib.Path) -> None:
        self._encrypted_file = repo_root / "inputs.tar.gpg"
        self._inputs_dir = inputs_dir

    def extract(self, input_file_names: Iterable[str], encryption_key: str) -> bool:
        if not self._encrypted_file.exists():
            _logger.error("Encrypted input file not found: %s", self._encrypted_file)
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            _logger.debug("Decrypting encrypted tarball to %s", tmpdir)
            output_file = pathlib.Path(tmpdir) / "inputs.tar"
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "gpg",
                    "--decrypt",
                    "--batch",
                    "--passphrase-fd",
                    "0",
                    "--output",
                    str(output_file),
                    str(self._encrypted_file),
                ],
                check=True,
                input=encryption_key,
                text=True,
            )

            self._inputs_dir.mkdir(exist_ok=True)
            with tarfile.open(name=output_file, mode="r") as tar:
                for file_name in input_file_names:
                    try:
                        tar.extract(f"{self._inputs_dir.name}/{file_name}")
                    except KeyError as e:
                        _logger.warning("Extraction error: %s", e)

        return True


def main() -> bool:
    logging.basicConfig(level=log_level(int(os.environ.get("usage_verbose", "0"))))  # noqa: SIM112

    encryption_key = os.environ.get("ENCRYPTION_KEY")
    if not encryption_key:
        _logger.error(
            "Encryption key not specified in ENCRYPTION_KEY environment variable"
        )
        return False

    repo_root = pathlib.Path(__file__).parent.parent.parent
    inputs_dir = repo_root / "inputs"
    if inputs_dir.exists() and inputs_dir.is_dir():
        if next(inputs_dir.iterdir(), None) is not None:
            _logger.error("Inputs directory and is not empty. Not overwriting.")
            return False
        _logger.debug("Inputs directory exists but is empty")
    else:
        _logger.debug("Inputs directory does not exist")

    _logger.debug("Repo root: %s", repo_root)

    file_records = FileRecords(repo_root)

    encrypted_input_files = EncryptedInputFiles(repo_root, inputs_dir)
    encrypted_input_files.extract(file_records.iter(), encryption_key)

    return True


if __name__ == "__main__":
    if not main():
        sys.exit(1)
