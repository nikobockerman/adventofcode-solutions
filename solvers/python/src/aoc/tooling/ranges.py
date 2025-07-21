def partition_range(range_: range, separator: range) -> tuple[range, range, range]:
    before = range(0)
    if range_.start < separator.start:
        before = range(range_.start, min(range_.stop, separator.start))

    overlap = range(0)
    if range_.start < separator.stop and range_.stop > separator.start:
        overlap = range(
            max(range_.start, separator.start), min(range_.stop, separator.stop)
        )

    after = range(0)
    if range_.stop > separator.stop:
        after = range(max(range_.start, separator.stop), range_.stop)

    return before, overlap, after


def are_ranges_overlapping(left: range, right: range) -> bool:
    _, overlap, _ = partition_range(left, right)
    return bool(overlap)
