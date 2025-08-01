from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Literal, assert_never, overload

from aoc.tooling.coordinates import X, Y
from aoc.tooling.directions import RotationDirection

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence


class Map2dEmptyDataError(ValueError):
    def __init__(self) -> None:
        super().__init__("data must not be empty")


class Map2dRectangularDataError(ValueError):
    def __init__(self) -> None:
        super().__init__("data must be rectangular")


class IterDirection(enum.Enum):
    Rows = enum.auto()
    Columns = enum.auto()


class Map2d[Map2dDataType = str]:
    __slots__ = ("_br_x", "_br_y", "_height", "_sequence_data", "_width")

    def __init__(
        self,
        data: Iterable[Iterable[Map2dDataType]] | Iterable[Sequence[Map2dDataType]],
    ) -> None:
        self._sequence_data = tuple(tuple(row) for row in data)
        if len(self._sequence_data) == 0:
            raise Map2dEmptyDataError

        self._height = len(self._sequence_data)
        assert self._height > 0
        self._width = len(self._sequence_data[0])
        self._br_y = Y(self._height - 1)
        self._br_x = X(self._width - 1)

        if not all(len(row) == self._width for row in self._sequence_data):
            raise Map2dRectangularDataError

        if self._width == 0:
            raise Map2dEmptyDataError

    @property
    def height(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        return self._width

    @property
    def tl_y(self) -> Y:
        return Y(0)

    @property
    def tl_x(self) -> X:
        return X(0)

    @property
    def br_y(self) -> Y:
        return self._br_y

    @property
    def br_x(self) -> X:
        return self._br_x

    def contains(self, y: Y, x: X) -> bool:
        return y >= 0 and y <= self._br_y and x >= 0 and x <= self._br_x

    def get_bounded(self, y: Y, x: X) -> Map2dDataType:
        if not self.contains(y, x):
            raise IndexError((y, x))
        return self._sequence_data[y][x]

    def get(self, y: Y, x: X) -> Map2dDataType:
        return self._sequence_data[y][x]

    def get_or_default(
        self, y: Y, x: X, default: Map2dDataType | None = None
    ) -> Map2dDataType | None:
        if not self.contains(y, x):
            return default
        return self._sequence_data[y][x]

    def iter_data_by_lines(  # noqa: C901, PLR0912
        # optimized for performance so can't reduce branching here which is done for
        # sanitizing input values
        self,
        first_y: Y,
        first_x: X,
        last_y: Y,
        last_x: X,
    ) -> Iterable[tuple[Y, Iterable[tuple[X, Map2dDataType]]]]:
        step_y = 1 if first_y <= last_y else -1
        step_x = 1 if first_x <= last_x else -1
        if first_y < 0:
            first_y = Y(0)
        elif first_y > self._br_y:
            first_y = self._br_y
        if first_x < 0:
            first_x = X(0)
        elif first_x > self._br_x:
            first_x = self._br_x
        if last_x < 0:
            last_x = X(0)
        elif last_x > self._br_x:
            last_x = self._br_x

        if last_y <= 0:
            slice_rows = self._sequence_data[first_y::step_y]
        else:
            if last_y < 0:
                last_y = Y(0)
            elif last_y > self._br_y:
                last_y = self._br_y
            slice_rows = self._sequence_data[first_y : last_y + step_y : step_y]

        for row_ind, row in enumerate(slice_rows):
            y = Y(row_ind * step_y + first_y)
            if last_x <= 0:
                slice_row_datas = row[first_x::step_x]
            else:
                slice_row_datas = row[first_x : last_x + step_x : step_x]

            yield (
                y,
                (
                    (X(x_ind * step_x + first_x), data)
                    for x_ind, data in enumerate(slice_row_datas)
                ),
            )

    def iter_data_by_columns(
        self, first_y: Y, first_x: X, last_y: Y, last_x: X
    ) -> Iterable[tuple[X, Iterable[tuple[Y, Map2dDataType]]]]:
        step_y = 1 if first_y <= last_y else -1
        step_x = 1 if first_x <= last_x else -1
        if first_y < 0:
            first_y = Y(0)
        elif first_y > self._br_y:
            first_y = self._br_y
        if last_y < 0:
            last_y = Y(0)
        elif last_y > self._br_y:
            last_y = self._br_y
        for x in range(first_x, last_x + step_x, step_x):
            if x < 0 or x >= self._width:
                continue

            yield (
                X(x),
                (
                    (Y(y), self._sequence_data[y][x])
                    for y in range(first_y, last_y + step_y, step_y)
                ),
            )

    @overload
    def iter_data(
        self, *, direction: IterDirection
    ) -> Iterable[tuple[X, Iterable[tuple[Y, Map2dDataType]]]]: ...
    @overload
    def iter_data(
        self, *, direction: Literal[IterDirection.Rows] = IterDirection.Rows
    ) -> Iterable[tuple[Y, Iterable[tuple[X, Map2dDataType]]]]: ...
    @overload
    def iter_data(
        self, first_y: Y, first_x: X, *, direction: IterDirection
    ) -> Iterable[tuple[X, Iterable[tuple[Y, Map2dDataType]]]]: ...
    @overload
    def iter_data(
        self,
        first_y: Y,
        first_x: X,
        *,
        direction: Literal[IterDirection.Rows] = IterDirection.Rows,
    ) -> Iterable[tuple[Y, Iterable[tuple[X, Map2dDataType]]]]: ...
    @overload
    def iter_data(
        self,
        first_y: Y,
        first_x: X,
        last_y: Y,
        last_x: X,
        *,
        direction: IterDirection,
    ) -> Iterable[tuple[X, Iterable[tuple[Y, Map2dDataType]]]]: ...
    @overload
    def iter_data(
        self,
        first_y: Y,
        first_x: X,
        last_y: Y,
        last_x: X,
        *,
        direction: Literal[IterDirection.Rows] = IterDirection.Rows,
    ) -> Iterable[tuple[Y, Iterable[tuple[X, Map2dDataType]]]]: ...

    def iter_data(
        self,
        first_y: Y | None = None,
        first_x: X | None = None,
        last_y: Y | None = None,
        last_x: X | None = None,
        *,
        direction: IterDirection = IterDirection.Rows,
    ) -> (
        Iterable[tuple[Y, Iterable[tuple[X, Map2dDataType]]]]
        | Iterable[tuple[X, Iterable[tuple[Y, Map2dDataType]]]]
    ):
        if first_x is None:
            assert first_y is None
            first_x = X(-1)
            first_y = Y(-1)
        else:
            assert first_y is not None

        if last_x is None:
            assert last_y is None
            last_x = X(self._width)
            last_y = Y(self._height)
        else:
            assert last_y is not None

        if first_x < 0 and last_x < 0:
            return
        if first_x > self._br_x and last_x >= self._br_x:
            return
        if first_y < 0 and last_y < 0:
            return
        if first_y > self._br_y and last_y >= self._br_y:
            return

        match direction:
            case IterDirection.Rows:
                yield from self.iter_data_by_lines(first_y, first_x, last_y, last_x)
            case IterDirection.Columns:
                yield from self.iter_data_by_columns(first_y, first_x, last_y, last_x)

    def str_lines(
        self, get_symbol: Callable[[Map2dDataType], str] | None = None
    ) -> Iterable[str]:
        def default_get_symbol(x: Map2dDataType) -> str:
            return str(x)

        if get_symbol is None:
            get_symbol = default_get_symbol

        def row_symbols(row: Sequence[Map2dDataType]) -> Iterable[str]:
            for elem in row:
                sym = get_symbol(elem)
                assert len(sym) == 1
                yield sym

        for row in self._sequence_data:
            yield "".join(row_symbols(row))

    def __str__(self) -> str:
        return "\n".join(self.str_lines())

    def transpose(self) -> Map2d[Map2dDataType]:
        return Map2d(list(zip(*self._sequence_data, strict=True)))

    def __rotate_once_clockwise(self) -> Map2d[Map2dDataType]:
        return Map2d(
            (data for _, data in items)
            for _, items in self.iter_data_by_columns(
                self._br_y, X(0), Y(0), self._br_x
            )
        )

    def __rotate_once_counterclockwise(self) -> Map2d[Map2dDataType]:
        return Map2d(
            (data for _, data in items)
            for _, items in self.iter_data_by_columns(
                Y(0), self._br_x, self._br_y, X(0)
            )
        )

    def rotate(
        self, direction: RotationDirection, count: int = 1
    ) -> Map2d[Map2dDataType]:
        if count <= 0:
            raise ValueError(count)
        map_ = self
        for _ in range(count):
            if direction is RotationDirection.Clockwise:
                map_ = map_.__rotate_once_clockwise()  # noqa: SLF001
            elif direction is RotationDirection.Counterclockwise:
                map_ = map_.__rotate_once_counterclockwise()  # noqa: SLF001
            else:
                assert_never(direction)
        return map_

    def __hash__(self) -> int:
        return hash(self._sequence_data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self._sequence_data == other._sequence_data
        return NotImplemented
