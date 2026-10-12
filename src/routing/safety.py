"""Time-aware route safety and flood passability evaluation."""
from typing import Callable, Optional, Protocol, Tuple
import logging

logger = logging.getLogger(__name__)


class FloodScenarioProtocol(Protocol):
    """Protocol for flood scenarios providing spatio-temporal depth queries."""

    def get_edge_depth(self, u: int, v: int, t_seconds: float) -> float:
        """Returns the flood water depth in meters on edge (u, v) at time t_seconds."""
        ...

    def get_max_edge_depth_in_interval(
        self, u: int, v: int, t_start: float, t_end: float
    ) -> float:
        """Returns the maximum flood water depth in meters on edge (u, v) between t_start and t_end."""
        ...


class SafetyEvaluator:
    """Evaluates whether an edge or route segment is passable given time and vehicle/pedestrian mode."""

    def __init__(self, flood_scenario: FloodScenarioProtocol):
        self.scenario = flood_scenario

    def is_edge_passable(
        self,
        u: int,
        v: int,
        t_entry: float,
        duration: float,
        max_safe_depth: float,
    ) -> Tuple[bool, float]:
        """
        Determines whether edge (u, v) is safe to traverse during time window [t_entry, t_entry + duration].

        Returns:
            Tuple[bool, float]: (is_passable, max_encountered_depth)
        """
        t_exit = t_entry + duration
        max_depth = self.scenario.get_max_edge_depth_in_interval(u, v, t_entry, t_exit)

        # Passable if the peak water depth encountered does not exceed the safe threshold
        is_passable = max_depth <= max_safe_depth
        return is_passable, max_depth
