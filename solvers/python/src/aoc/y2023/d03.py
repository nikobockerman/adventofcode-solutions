from typing import TYPE_CHECKING

from attrs import Factory, define, field

from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = get_logger()


@define
class _InputNumber:
    value: str
    begin_index: int


@define
class _InputSymbol:
    symbol: str
    index: int


@define
class _InputRow:
    numbers: list[_InputNumber] = field(default=Factory(list[_InputNumber]), init=False)
    symbols: list[_InputSymbol] = field(default=Factory(list[_InputSymbol]), init=False)


def _parse_input(lines: Iterable[str]) -> list[_InputRow]:
    rows: list[_InputRow] = []
    for row_ind, line in enumerate(lines):
        _logger.debug("%s: line=%s", row_ind, line)
        row = _InputRow()

        number: str | None = None
        for ind, symbol in enumerate(line):
            if symbol.isdigit():
                if number is None:
                    number = symbol
                else:
                    number += symbol
                continue

            if number is not None:
                row.numbers.append(_InputNumber(number, ind - len(number)))
                number = None

            if symbol == ".":
                continue

            row.symbols.append(_InputSymbol(symbol, ind))

        if number is not None:
            row.numbers.append(_InputNumber(number, len(line) - 1 - len(number)))
            number = None

        _logger.debug("%s: row=%s", row_ind, row)
        rows.append(row)
    return rows


def p1(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    symbol_indexes = [[symbol.index for symbol in row.symbols] for row in d]

    @define
    class Number:
        number: int
        adjacent_ind_range_begin: int
        adjacent_ind_range_end: int
        adjacent_row_range_begin: int
        adjacent_row_range_end: int

    def is_adjacent(number: Number) -> bool:
        for row_ind in range(
            number.adjacent_row_range_begin, number.adjacent_row_range_end
        ):
            for ind in range(
                number.adjacent_ind_range_begin, number.adjacent_ind_range_end
            ):
                if ind in symbol_indexes[row_ind]:
                    return True
        return False

    result = 0
    for row_ind, row in enumerate(d):
        for input_number in row.numbers:
            number = Number(
                int(input_number.value),
                input_number.begin_index - 1,
                input_number.begin_index + len(input_number.value) + 1,
                max(0, row_ind - 1),
                min(len(d), row_ind + 2),
            )
            if is_adjacent(number):
                _logger.debug("input_number=%s. Adjacent", input_number)
                result += number.number
            else:
                _logger.debug("input_number=%s. NOT adjacent", input_number)

    return result


def p2(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    @define
    class Number:
        number: int
        adjacent_ind_range_begin: int
        adjacent_ind_range_end: int
        adjacent_row_range_begin: int
        adjacent_row_range_end: int

    @define
    class GearSymbol:
        row_ind: int
        ind: int

    gear_symbols = [
        GearSymbol(row_ind, symbol.index)
        for row_ind, row in enumerate(d)
        for symbol in row.symbols
        if symbol.symbol == "*"
    ]

    numbers: list[Number] = [
        Number(
            int(input_number.value),
            input_number.begin_index - 1,
            input_number.begin_index + len(input_number.value) + 1,
            max(0, row_ind - 1),
            min(len(d), row_ind + 2),
        )
        for row_ind, row in enumerate(d)
        for input_number in row.numbers
    ]

    def is_adjacent(number: Number, gear_symbol: GearSymbol) -> bool:
        if gear_symbol.row_ind not in range(
            number.adjacent_row_range_begin, number.adjacent_row_range_end
        ):
            return False

        return gear_symbol.ind in range(
            number.adjacent_ind_range_begin, number.adjacent_ind_range_end
        )

    result = 0
    for gear_symbol in gear_symbols:
        adjacent_numbers: list[Number] = []
        for number in numbers:
            if is_adjacent(number, gear_symbol):
                adjacent_numbers.append(number)
                if len(adjacent_numbers) > 2:
                    break
        if len(adjacent_numbers) == 2:
            result += adjacent_numbers[0].number * adjacent_numbers[1].number
    return result


if __name__ == "__main__":
    run(p1, p2)
