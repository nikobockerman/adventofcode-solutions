from aoc.tooling.coordinates import Coord2d, X, Y


def test_coordinates() -> None:
    assert Coord2d(Y(0), X(0)).distance_to_int(Coord2d(Y(1), X(0))) == 1
