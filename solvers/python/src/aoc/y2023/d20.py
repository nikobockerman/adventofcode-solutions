import logging
import math
from abc import ABCMeta, abstractmethod
from collections import Counter, deque
from typing import TYPE_CHECKING, Never, NewType, override

from attrs import frozen

from aoc.tooling.run import get_logger, run

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

_logger = get_logger()


_PulseValue = NewType("_PulseValue", bool)
_PulseLow = _PulseValue(False)  # noqa: FBT003
_PulseHigh = _PulseValue(True)  # noqa: FBT003

_ModuleName = NewType("_ModuleName", str)


@frozen(kw_only=True)
class _PulseNew:
    value: _PulseValue
    from_: _Module
    to: _Module


@frozen(kw_only=True)
class _Pulse:
    value: _PulseValue
    from_: _Module
    to: _Module
    button_presses: int

    @staticmethod
    def create(new_pulse: _PulseNew, button_presses: int, /) -> _Pulse:
        return _Pulse(
            value=new_pulse.value,
            from_=new_pulse.from_,
            to=new_pulse.to,
            button_presses=button_presses,
        )


class _Module(metaclass=ABCMeta):
    def __init__(self, name: _ModuleName) -> None:
        self._name = name
        self._outputs: list[_Module] = []

    @property
    def name(self) -> _ModuleName:
        return self._name

    def add_receiving_module(self, output: _Module) -> None:
        self._outputs.append(output)

    @abstractmethod
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]: ...

    def _get_output_pulses(self, value: _PulseValue) -> Iterator[_PulseNew]:
        for output in self._outputs:
            yield _PulseNew(value=value, from_=self, to=output)

    if __debug__:

        def _validate_incoming_pulse(self, pulse: _Pulse) -> None:
            assert pulse.to is self


class _Button(_Module):
    def __init__(self) -> None:
        super().__init__(name=_ModuleName(""))
        self._button_presses: int = 0

    @property
    def button_presses(self) -> int:
        return self._button_presses

    def process_button_press(self) -> Iterator[_PulseNew]:
        self._button_presses += 1
        yield from self._get_output_pulses(_PulseLow)

    @override
    def process_pulse(self, pulse: _Pulse) -> Never:
        if __debug__:
            self._validate_incoming_pulse(pulse)
        raise AssertionError


class _Broadcast(_Module):
    @override
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]:
        if __debug__:
            self._validate_incoming_pulse(pulse)
        yield from self._get_output_pulses(pulse.value)


class _Receiver(_Module):
    def __init__(self, name: _ModuleName) -> None:
        super().__init__(name=name)

    @override
    def add_receiving_module(self, output: _Module) -> Never:
        super().add_receiving_module(output)
        raise AssertionError

    @override
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]:
        if __debug__:
            self._validate_incoming_pulse(pulse)
        if pulse.value is _PulseLow:
            _logger.info(
                "Receiver received signal from %s: %s", pulse.from_, pulse.value
            )
            self._received_low = True
        yield from []


class _FlipFlop(_Module):
    def __init__(self, name: _ModuleName) -> None:
        super().__init__(name=name)
        self._state: _PulseValue = _PulseLow

    @override
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]:
        if __debug__:
            self._validate_incoming_pulse(pulse)

        if pulse.value is _PulseHigh:
            return

        self._state = _PulseValue(not self._state)
        yield from self._get_output_pulses(self._state)


class _Conjunction(_Module):
    def __init__(self, name: _ModuleName) -> None:
        super().__init__(name=name)
        self._state: dict[_ModuleName, _PulseValue] = {}

    @override
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]:
        if __debug__:
            self._validate_incoming_pulse(pulse)
        assert pulse.from_.name in self._state

        self._state[pulse.from_.name] = pulse.value

        output_pulse_value = (
            _PulseLow
            if all(value is _PulseHigh for value in self._state.values())
            else _PulseHigh
        )
        yield from self._get_output_pulses(output_pulse_value)

    def set_inputs(self, inputs: Iterable[_ModuleName]) -> None:
        self._state.update(dict.fromkeys(inputs, _PulseLow))


class _GatewayConjuction(_Conjunction):
    def __init__(self, name: _ModuleName) -> None:
        super().__init__(name=name)
        self._periods: dict[_ModuleName, int] = {}

    @property
    def has_pattern_for_all(self) -> bool:
        return all(name in self._periods for name in self._state)

    @property
    def periods(self) -> dict[_ModuleName, int]:
        return self._periods

    @override
    def process_pulse(self, pulse: _Pulse) -> Iterator[_PulseNew]:
        result_iter = super().process_pulse(pulse)

        if pulse.from_.name not in self._periods and pulse.value is _PulseHigh:
            self._periods[pulse.from_.name] = pulse.button_presses
            _logger.info(
                "Conjuction(%s) period for %s: %s",
                self.name,
                pulse.from_.name,
                self._periods[pulse.from_.name],
            )

        yield from result_iter

    # Pattern notes:
    # - Formula: start + n*constant
    # - start is always constant - 1 -> try without taking that into account
    # - Value changes to True and back to False during same button press: try first
    #   without taking this into consideration


type _AnyModule = (
    _Button | _Broadcast | _Receiver | _FlipFlop | _Conjunction | _GatewayConjuction
)


def _parse_module(
    line: str,
) -> (
    tuple[_Broadcast, list[_ModuleName]]
    | tuple[_FlipFlop, list[_ModuleName]]
    | tuple[_Conjunction, list[_ModuleName]]
):
    name, outputs_str = map(str.strip, line.split("->"))
    outputs = [_ModuleName(x.strip()) for x in outputs_str.split(",")]
    if name == "broadcaster":
        return _Broadcast(_ModuleName(name)), outputs

    assert name[0] in "%&"
    module_type = name[0]
    name = _ModuleName(name[1:])

    if module_type == "%":
        return _FlipFlop(name), outputs
    return _Conjunction(name), outputs


def _find_gateway(
    modules_with_output_names: Sequence[tuple[_AnyModule, list[_ModuleName]]],
    receiver: _Receiver,
) -> _GatewayConjuction | None:
    gateways_to_receiver = [
        module
        for module, outputs in modules_with_output_names
        if receiver.name in outputs
    ]
    assert len(gateways_to_receiver) <= 1, "Safety check: only 0-1 gateways are known"
    if not gateways_to_receiver:
        return None

    gateway_to_receiver = gateways_to_receiver[0]
    assert isinstance(gateway_to_receiver, _Conjunction), (
        "Safety check: only conjunctions are known"
    )
    return _GatewayConjuction(gateway_to_receiver.name)


def _resolve_receiver_names(
    modules_with_output_names: Sequence[tuple[_AnyModule, list[_ModuleName]]],
) -> set[_ModuleName]:
    all_names_with_outputs = {module.name for module, _ in modules_with_output_names}

    all_output_names = {
        output for _, outputs in modules_with_output_names for output in outputs
    }
    return all_output_names - all_names_with_outputs


def _parse_modules(
    lines: Iterable[str], *, use_gateway: bool = False
) -> tuple[_Receiver | None, _Button, _GatewayConjuction | None]:
    button = _Button()
    modules_with_output_names: list[tuple[_AnyModule, list[_ModuleName]]] = [
        (button, [_ModuleName("broadcaster")])
    ]
    modules_with_output_names += [_parse_module(line) for line in lines]

    receiver_names = _resolve_receiver_names(modules_with_output_names)
    assert len(receiver_names) <= 1, (
        "Safety check: only inputs with 0-1 receivers are known"
    )

    receiver: _Receiver | None = None
    if receiver_names:
        receiver = _Receiver(receiver_names.pop())

    gateway: _GatewayConjuction | None = None
    if receiver:
        modules_with_output_names = [
            *modules_with_output_names,
            (receiver, list[_ModuleName]()),
        ]
        if use_gateway:
            gateway = _find_gateway(modules_with_output_names, receiver)
            if gateway:
                modules_with_output_names = [
                    (gateway if module.name == gateway.name else module, outputs)
                    for module, outputs in modules_with_output_names
                ]

    modules_by_name = {module.name: module for module, _ in modules_with_output_names}

    for module, outputs in modules_with_output_names:
        for output in outputs:
            output_module = modules_by_name[output]
            module.add_receiving_module(output_module)

    for conjunction in modules_by_name.values():
        if not isinstance(conjunction, _Conjunction):
            continue
        inputs = (
            module.name
            for module, outputs in modules_with_output_names
            if conjunction.name in outputs
        )
        conjunction.set_inputs(inputs)

    return receiver, button, gateway


def _extend_pulses(
    queue: deque[_Pulse], button: _Button, pulses: Iterable[_PulseNew]
) -> None:
    queue.extend(_Pulse.create(new, button.button_presses) for new in pulses)


def p1(input_str: str) -> int:
    _, button, _ = _parse_modules(input_str.splitlines())

    counts = Counter[_PulseValue]()
    queue = deque[_Pulse]()

    for _ in range(1000):
        _extend_pulses(queue, button, button.process_button_press())

        while queue:
            pulse = queue.popleft()
            counts.update((pulse.value,))
            _extend_pulses(queue, button, pulse.to.process_pulse(pulse))

    _logger.info("Counts: %s", counts)

    return math.prod(counts.values())


def p2(input_str: str) -> int:
    receiver_name = _ModuleName("rx")
    receiver, button, gateway = _parse_modules(input_str.splitlines(), use_gateway=True)
    assert receiver is not None
    assert receiver.name == receiver_name
    assert gateway is not None

    queue = deque[_Pulse]()

    while True:
        _extend_pulses(queue, button, button.process_button_press())
        if button.button_presses % 100_000 == 0 and _logger.isEnabledFor(logging.INFO):
            _logger.info(f"Button presses: {button.button_presses:_}")  # noqa: G004

        while queue:
            pulse = queue.popleft()
            _extend_pulses(queue, button, pulse.to.process_pulse(pulse))

        if gateway.has_pattern_for_all:
            _logger.info(
                "All patterns found for gateway after %d button presses",
                button.button_presses,
            )
            break

    return math.lcm(*(pattern for pattern in gateway.periods.values()))


if __name__ == "__main__":
    run(p1, p2)
