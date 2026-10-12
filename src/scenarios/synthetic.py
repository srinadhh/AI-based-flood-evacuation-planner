"""Synthetic spatio-temporal flood depth scenarios for testing routing logic."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple
import math


@dataclass
class DynamicFloodCurve:
    """Models flood depth rising linearly or piecewise over time."""
    start_time_seconds: float
    peak_time_seconds: float
    peak_depth_m: float
    base_depth_m: float = 0.0

    def depth_at(self, t: float) -> float:
        if t <= self.start_time_seconds:
            return self.base_depth_m
        if t >= self.peak_time_seconds:
            return self.peak_depth_m
        # Linear ramp between start and peak
        ratio = (t - self.start_time_seconds) / (self.peak_time_seconds - self.start_time_seconds)
        return self.base_depth_m + ratio * (self.peak_depth_m - self.base_depth_m)

    def max_depth_in_interval(self, t_start: float, t_end: float) -> float:
        # Since this curve is monotonically non-decreasing, the max is at min(t_end, peak_time)
        return max(self.depth_at(t_start), self.depth_at(t_end))


class SyntheticFloodScenario:
    """
    Spatio-temporal flood depth scenario.
    Provides depth queries per edge at arbitrary timestamps.
    """

    def __init__(self, name: str = "Synthetic Scenario"):
        self.name = name
        # Static edge depths: (u, v) -> depth_m
        self.static_edge_depths: Dict[Tuple[int, int], float] = {}
        # Dynamic edge curves: (u, v) -> DynamicFloodCurve
        self.dynamic_edge_curves: Dict[Tuple[int, int], DynamicFloodCurve] = {}
        # Custom edge functions: (u, v) -> callable(t) -> depth_m
        self.custom_edge_funcs: Dict[Tuple[int, int], Callable[[float], float]] = {}

    def set_static_edge_depth(self, u: int, v: int, depth_m: float, bidirectional: bool = True) -> None:
        """Sets a constant depth for edge (u, v)."""
        self.static_edge_depths[(u, v)] = depth_m
        if bidirectional:
            self.static_edge_depths[(v, u)] = depth_m

    def set_dynamic_edge_curve(
        self,
        u: int,
        v: int,
        start_time_seconds: float,
        peak_time_seconds: float,
        peak_depth_m: float,
        base_depth_m: float = 0.0,
        bidirectional: bool = True,
    ) -> None:
        """Sets a time-varying rising flood curve for edge (u, v)."""
        curve = DynamicFloodCurve(
            start_time_seconds=start_time_seconds,
            peak_time_seconds=peak_time_seconds,
            peak_depth_m=peak_depth_m,
            base_depth_m=base_depth_m,
        )
        self.dynamic_edge_curves[(u, v)] = curve
        if bidirectional:
            self.dynamic_edge_curves[(v, u)] = curve

    def set_custom_edge_func(
        self,
        u: int,
        v: int,
        func: Callable[[float], float],
        bidirectional: bool = True,
    ) -> None:
        """Sets a custom time-to-depth function for edge (u, v)."""
        self.custom_edge_funcs[(u, v)] = func
        if bidirectional:
            self.custom_edge_funcs[(v, u)] = func

    def get_edge_depth(self, u: int, v: int, t_seconds: float) -> float:
        """Returns the flood water depth in meters on edge (u, v) at time t_seconds."""
        edge = (u, v)
        if edge in self.custom_edge_funcs:
            return max(0.0, float(self.custom_edge_funcs[edge](t_seconds)))
        if edge in self.dynamic_edge_curves:
            return max(0.0, float(self.dynamic_edge_curves[edge].depth_at(t_seconds)))
        if edge in self.static_edge_depths:
            return max(0.0, float(self.static_edge_depths[edge]))
        return 0.0  # Dry by default

    def get_max_edge_depth_in_interval(
        self, u: int, v: int, t_start: float, t_end: float
    ) -> float:
        """Returns the peak flood water depth on edge (u, v) during the window [t_start, t_end]."""
        edge = (u, v)
        if edge in self.custom_edge_funcs:
            # Sample across interval (5 samples)
            samples = [
                self.custom_edge_funcs[edge](t_start + i * (t_end - t_start) / 4.0)
                for i in range(5)
            ]
            return max(0.0, max(samples))
        if edge in self.dynamic_edge_curves:
            return self.dynamic_edge_curves[edge].max_depth_in_interval(t_start, t_end)
        if edge in self.static_edge_depths:
            return self.static_edge_depths[edge]
        return 0.0
