import pathlib


def get_repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent.parent.parent
