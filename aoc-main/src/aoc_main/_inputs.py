from typing import TYPE_CHECKING

from aoc_main import _types, _utils

if TYPE_CHECKING:
    import pathlib


def get_input_file_path(year: _types.Year, day: _types.Day) -> pathlib.Path:
    return _utils.get_repo_root() / "inputs" / f"{year}-{day:02}.txt"
