import inspect
import logging
import pathlib
import sys
from collections.abc import Callable
from typing import Literal, TypeIs


def is_part(n: int) -> TypeIs[Literal[1, 2]]:
    return n in (1, 2)


def get_logger() -> logging.Logger:
    filename = pathlib.Path(inspect.stack()[1].filename).name
    return logging.getLogger(filename)


def run(p1: Callable[[str], int], p2: Callable[[str], int]) -> None:
    verbosity, part = map(int, sys.argv[1:])
    level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[verbosity]
    logging.basicConfig(level=level)
    assert is_part(part)
    input_str = sys.stdin.read().strip()

    match part:
        case 1:
            answer = p1(input_str)
        case 2:
            answer = p2(input_str)
    print(answer)  # noqa: T201
    sys.exit(0)
