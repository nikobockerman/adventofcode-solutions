import typing
from functools import cache
from typing import Protocol, runtime_checkable

from attrs import Factory, define, field

if typing.TYPE_CHECKING:
    from collections.abc import Iterable


@runtime_checkable
class NodeId(typing.Hashable, Protocol):
    pass


@define(kw_only=True)
class Digraph[Id: NodeId, N]:
    nodes: dict[Id, N]  # TODO: Consider replacing with a frozendict
    arcs: tuple[DigraphArc[Id], ...]

    def get_arcs_to(self, node_id: Id, /) -> list[DigraphArc[Id]]:
        return _get_arcs_to_node(node_id, self.arcs)

    def get_arcs_from(self, node_id: Id, /) -> list[DigraphArc[Id]]:
        return _get_arcs_from_node(node_id, self.arcs)


class DigraphArc[Id: NodeId](Protocol):
    @property
    def from_(self) -> Id: ...
    @property
    def to(self) -> Id: ...


@define(frozen=True)
class Arc[Id: NodeId]:
    from_: Id
    to: Id


@define
class DigraphCreator[Id: NodeId, N]:
    _nodes: dict[Id, N] = field(default=Factory(dict[Id, N]), init=False)
    _arcs: list[DigraphArc[Id]] = field(
        default=Factory(list[DigraphArc[Id]]), init=False
    )

    def add_node(self, node_id: Id, node: N, /) -> None:
        if node_id in self._nodes:
            raise ValueError(node_id)
        self._nodes[node_id] = node

    def add_arc(self, arc: DigraphArc[Id], /) -> None:
        if arc.from_ not in self._nodes:
            raise ValueError(arc.from_)
        if arc.to not in self._nodes:
            raise ValueError(arc.to)
        self._arcs.append(arc)

    def create(self) -> Digraph[Id, N]:
        return Digraph(nodes=self._nodes, arcs=tuple(self._arcs))


@cache
def _get_arcs_to_node[Id: NodeId](
    node_id: Id, arcs: Iterable[DigraphArc[Id]]
) -> list[DigraphArc[Id]]:
    return [arc for arc in arcs if arc.to == node_id]


@cache
def _get_arcs_from_node[Id: NodeId](
    node_id: Id, arcs: Iterable[DigraphArc[Id]]
) -> list[DigraphArc[Id]]:
    return [arc for arc in arcs if arc.from_ == node_id]
