from aoc.tooling.run import get_logger, run

_logger = get_logger()


def _calculate_hash(str_: str) -> int:
    h = 0
    for c in str_:
        h += ord(c)
        h = h * 17
        h = h % 256
    return h


def p1(input_str: str) -> int:
    hash_sum = 0
    for step_str in input_str.split(","):
        h = _calculate_hash(step_str)
        _logger.debug("step_str=%s -> h=%s", step_str, h)
        hash_sum += h

    return hash_sum


def p2(input_str: str) -> int:
    boxes: list[list[tuple[str, int]]] = [[] for _ in range(256)]
    for step_str in input_str.split(","):
        if step_str[-1] == "-":
            label = step_str[:-1]
            operation = "-"
            focal_length: int | None = None
        else:
            assert step_str[-2] == "="
            label = step_str[:-2]
            operation = "="
            focal_length = int(step_str[-1])
            assert 1 <= focal_length <= 9

        box = _calculate_hash(label)
        _logger.debug(
            "step_str=%s -> label=%s operation=%s focal_length=%s box=%s",
            step_str,
            label,
            operation,
            focal_length,
            box,
        )
        _logger.debug("Box contents before: %s", boxes[box])

        if operation == "-":
            ind = next(
                (ind for ind, (label_, _) in enumerate(boxes[box]) if label_ == label),
                -1,
            )
            if ind == -1:
                _logger.debug("Label %s not found in box %s", label, box)
            else:
                del boxes[box][ind]
        else:
            assert operation == "="
            assert focal_length is not None
            existing_ind = next(
                (ind for ind, (label_, _) in enumerate(boxes[box]) if label_ == label),
                -1,
            )
            if existing_ind != -1:
                boxes[box][existing_ind] = (label, focal_length)
            else:
                boxes[box].append((label, focal_length))

        _logger.debug("Box contents after : %s", boxes[box])

    total_focusing_strength = 0
    for box, box_data in enumerate(boxes):
        for ind, (label, fl) in enumerate(box_data):
            focusing_strength = (box + 1) * (ind + 1) * fl
            total_focusing_strength += focusing_strength
            _logger.debug(
                "box=%s ind=%s label=%s fl=%s focusing_strength=%s "
                "-> total_focusing_strength=%s",
                box,
                ind,
                label,
                fl,
                focusing_strength,
                total_focusing_strength,
            )
    return total_focusing_strength


if __name__ == "__main__":
    run(p1, p2)
