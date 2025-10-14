import itertools
from typing import TYPE_CHECKING

from aoc.tooling.run import run

if TYPE_CHECKING:
    from collections.abc import Iterable


def _parse_input(lines: Iterable[str]) -> Iterable[list[int]]:
    for line in lines:
        yield [int(x) for x in line.strip().split()]


def _construct_tree_with_diffs(seq: list[int]) -> list[list[int]]:
    tree: list[list[int]] = [seq]
    seq_to_check = seq
    while True:
        diff = [b - a for a, b in itertools.pairwise(seq_to_check)]
        if all(x == 0 for x in diff):
            break

        tree.append(diff)
        seq_to_check = diff
    return tree


def p1(input_str: str) -> int:
    input_data = _parse_input(input_str.splitlines())

    def solve(seq: list[int]) -> int:
        tree = _construct_tree_with_diffs(seq)

        tree[-1].append(tree[-1][-1])
        for i in reversed(range(len(tree) - 1)):
            tree[i].append(tree[i + 1][-1] + tree[i][-1])

        return tree[0][-1]

    return sum(solve(seq) for seq in input_data)


def p2(input_str: str) -> int:
    input_data = _parse_input(input_str.splitlines())

    def solve(seq: list[int]) -> int:
        tree = _construct_tree_with_diffs(seq)

        tree[-1].insert(0, tree[-1][0])
        for i in reversed(range(len(tree) - 1)):
            tree[i].insert(0, tree[i][0] - tree[i + 1][0])

        return tree[0][0]

    return sum(solve(seq) for seq in input_data)


if __name__ == "__main__":
    run(p1, p2)
