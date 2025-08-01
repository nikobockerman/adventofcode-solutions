import pathlib

from aoc_main import _types, _utils


def get_input_file_path(year: _types.Year, day: _types.Day) -> pathlib.Path:
    return _utils.get_repo_root() / "inputs" / f"{year}-{day:02}.txt"
