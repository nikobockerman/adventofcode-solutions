from enum import StrEnum, auto
from typing import assert_never


class CardinalDirection(StrEnum):
    N = auto()
    E = auto()
    S = auto()
    W = auto()

    def rotate_counterclockwise(self) -> CardinalDirection:
        if self is CardinalDirection.N:
            return CardinalDirection.W
        if self is CardinalDirection.E:
            return CardinalDirection.N
        if self is CardinalDirection.S:
            return CardinalDirection.E
        if self is CardinalDirection.W:
            return CardinalDirection.S
        assert_never(self)

    def rotate_clockwise(self) -> CardinalDirection:
        if self is CardinalDirection.N:
            return CardinalDirection.E
        if self is CardinalDirection.E:
            return CardinalDirection.S
        if self is CardinalDirection.S:
            return CardinalDirection.W
        if self is CardinalDirection.W:
            return CardinalDirection.N
        assert_never(self)

    def opposite(self) -> CardinalDirection:
        if self is CardinalDirection.N:
            return CardinalDirection.S
        if self is CardinalDirection.E:
            return CardinalDirection.W
        if self is CardinalDirection.S:
            return CardinalDirection.N
        if self is CardinalDirection.W:
            return CardinalDirection.E
        assert_never(self)

    def rotate(self, direction: RotationDirection) -> CardinalDirection:
        if direction is RotationDirection.Clockwise:
            return self.rotate_clockwise()
        if direction is RotationDirection.Counterclockwise:
            return self.rotate_counterclockwise()
        assert_never(direction)


CardinalDirectionsAll = tuple(d for d in CardinalDirection)


class RotationDirection(StrEnum):
    Clockwise = auto()
    Counterclockwise = auto()
