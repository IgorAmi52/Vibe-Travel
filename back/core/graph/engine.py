from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any


LANGGRAPH_AVAILABLE = find_spec("langgraph") is not None


@dataclass(frozen=True)
class LangGraphComponents:
    START: str
    END: str
    StateGraph: Any


def load_langgraph_components() -> LangGraphComponents:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required for this module. Install it with: pip install -U langgraph"
        ) from exc

    return LangGraphComponents(
        START=START,
        END=END,
        StateGraph=StateGraph,
    )
