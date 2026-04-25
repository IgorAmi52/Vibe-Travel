from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from core.graph.engine import load_langgraph_components
from core.state import TripPlannerGraphState

StateDict = TripPlannerGraphState
NodeHandler = Callable[[StateDict], StateDict]


@dataclass
class TripPlannerGraphBuilder:
    _parts: List[Tuple[str, NodeHandler]] = field(default_factory=list)
    _compiled_graph: Optional[Any] = None

    def append_part(self, name: str, handler: NodeHandler) -> None:
        self._parts.append((name, handler))
        self._compiled_graph = None

    def compile(self) -> Any:
        components = load_langgraph_components()
        graph = components.StateGraph(TripPlannerGraphState)
        previous = components.START
        for name, handler in self._parts:
            graph.add_node(name, handler)
            graph.add_edge(previous, name)
            previous = name
        graph.add_edge(previous, components.END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

    def invoke(self, state: StateDict) -> StateDict:
        if self._compiled_graph is None:
            self.compile()
        return self._compiled_graph.invoke(state)
