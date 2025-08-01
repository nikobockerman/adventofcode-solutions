from collections.abc import Iterable

from aoc.tooling.run import get_logger, run

_logger = get_logger()

_STR_DIGITS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def _find_first_and_last_int(input_str: str, *, use_texts: bool) -> tuple[str, str]:
    first: str | None = None
    last: str | None = None
    for ind, c in enumerate(input_str):
        val = None
        if c.isdigit():
            val = c
        elif use_texts:
            for digit_ind, str_digit in enumerate(_STR_DIGITS):
                if input_str.find(str_digit, ind, ind + len(str_digit)) >= 0:
                    val = str(digit_ind + 1)
                    break

        if val is not None:
            if first is None:
                first = val
                last = val
            else:
                last = val

    assert first is not None
    assert last is not None
    return first, last


def _int_chars_to_int(s1: str, s2: str) -> int:
    return int(s1 + s2)


def _p1_ints(lines: Iterable[str], *, use_texts: bool) -> Iterable[int]:
    for line in lines:
        _logger.debug("line=%s", line)
        value = _int_chars_to_int(*_find_first_and_last_int(line, use_texts=use_texts))
        _logger.debug("value=%s", value)
        yield value


def p1(input_str: str) -> int:
    return sum(_p1_ints(input_str.splitlines(), use_texts=False))


def p2(input_str: str) -> int:
    return sum(_p1_ints(input_str.splitlines(), use_texts=True))


if __name__ == "__main__":
    run(p1, p2)
