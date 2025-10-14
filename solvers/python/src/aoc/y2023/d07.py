import enum
from collections import Counter
from functools import total_ordering
from typing import TYPE_CHECKING

from attrs import define

from aoc.tooling.run import run

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import NotImplementedType


def _parse_input(lines: Iterable[str]) -> Iterable[tuple[str, int]]:
    for line in lines:
        cards, bid = line.split()
        yield cards, int(bid)


@total_ordering
class _HandType(enum.Enum):
    HighCard = 0
    OnePair = 1
    TwoPair = 2
    ThreeOfAKind = 3
    FullHouse = 4
    FourOfAKind = 5
    FiveOfAKind = 6

    def __lt__(self, other: _HandType) -> bool | NotImplementedType:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@define
class _Hand:
    card_values: list[int]
    hand_type: _HandType
    bid: int

    def __lt__(self, other: _Hand) -> bool:
        if self.hand_type != other.hand_type:
            return self.hand_type < other.hand_type

        for i in range(5):
            if self.card_values[i] != other.card_values[i]:
                return self.card_values[i] < other.card_values[i]
        raise AssertionError


_HandTypeByCount: dict[int, _HandType | dict[int, _HandType]] = {
    5: _HandType.FiveOfAKind,
    4: _HandType.FourOfAKind,
    3: {2: _HandType.FullHouse, 1: _HandType.ThreeOfAKind},
    2: {2: _HandType.TwoPair, 1: _HandType.OnePair},
    1: _HandType.HighCard,
}


def p1(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    def classify_hand_type(cards: str) -> _HandType:
        assert len(cards) == 5
        value_counts = Counter[str](cards)
        counts = [x[1] for x in value_counts.most_common(2)]
        count1_type = _HandTypeByCount[counts[0]]
        if isinstance(count1_type, _HandType):
            return count1_type
        return count1_type[counts[1]]

    def card_value(value: str) -> int:
        assert len(value) == 1
        try:
            return int(value)
        except ValueError:
            pass

        return "TJQKA".index(value) + 10

    hands = [
        _Hand(
            [card_value(c) for c in cards],
            classify_hand_type(cards),
            bid,
        )
        for cards, bid in d
    ]

    hands.sort()

    return sum((ind + 1) * hand.bid for ind, hand in enumerate(hands))


def p2(input_str: str) -> int:
    d = _parse_input(input_str.splitlines())

    def classify_hand_type(cards: str) -> _HandType:
        assert len(cards) == 5
        value_counts = Counter[str](cards)

        jokers = value_counts.get("J", 0)
        value_counts.pop("J", None)

        if jokers == 5:
            return _HandType.FiveOfAKind

        counts = [x[1] for x in value_counts.most_common(2)]
        count1_type = _HandTypeByCount[counts[0] + jokers]
        if isinstance(count1_type, _HandType):
            return count1_type
        return count1_type[counts[1]]

    def card_value(value: str) -> int:
        assert len(value) == 1
        try:
            return int(value)
        except ValueError:
            pass
        if value == "J":
            return 1
        return "TQKA".index(value) + 10

    hands = [
        _Hand(
            [card_value(c) for c in cards],
            classify_hand_type(cards),
            bid,
        )
        for cards, bid in d
    ]

    hands.sort()

    return sum((ind + 1) * hand.bid for ind, hand in enumerate(hands))


if __name__ == "__main__":
    run(p1, p2)
