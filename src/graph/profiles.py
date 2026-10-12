"""Profiles for walking and driving evacuation modes."""
from typing import Any, Dict, List, Optional, Union
import logging
import re
import networkx as nx
from shapely.geometry import LineString

from ..config import AppConfig

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """Builds mode-specific directed routing graphs for walking and driving."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load_from_yaml()

    def build_profile_graph(
        self,
        base_graph: nx.MultiDiGraph,
        profile_mode: str,
    ) -> nx.DiGraph:
        """
        Extracts a single-directed routing graph for the specified profile mode ('walking' or 'driving').
        Converts MultiDiGraph to DiGraph by selecting the minimum travel-time edge between any pair of nodes.
        """
        mode = profile_mode.lower()
        if mode not in self.config.profiles:
            raise ValueError(f"Unknown profile mode: '{mode}'. Must be one of {list(self.config.profiles.keys())}")

        prof_cfg = self.config.profiles[mode]
        allowed_highways = set(prof_cfg.allowed_highways)
        ignore_oneway = prof_cfg.ignore_oneway

        if mode == "walking":
            max_safe_depth = self.config.thresholds.walking_safe_depth_m
            speed_kmh = self.config.speeds.walking_speed_kmh
            speed_mps = speed_kmh / 3.6
        else:
            max_safe_depth = self.config.thresholds.driving_safe_depth_m
            speed_mps = None  # Variable per edge

        G_mode = nx.DiGraph()
        # Copy graph-level attributes
        G_mode.graph.update(base_graph.graph)
        G_mode.graph["profile_mode"] = mode
        G_mode.graph["max_safe_depth"] = max_safe_depth

        # Add nodes with their coordinates and attributes
        for node, data in base_graph.nodes(data=True):
            G_mode.add_node(node, **data)

        # Inspect and filter edges
        for u, v, key, data in base_graph.edges(keys=True, data=True):
            if not self._is_highway_allowed(data.get("highway"), allowed_highways):
                continue

            if not self._is_access_allowed(data, mode):
                continue

            length = float(data.get("length", 10.0))

            if mode == "walking":
                travel_time = length / speed_mps
            else:
                driving_speed_mps = self._get_driving_speed_mps(data)
                travel_time = length / driving_speed_mps

            edge_attrs = {
                "length": length,
                "travel_time": travel_time,
                "highway": data.get("highway"),
                "name": data.get("name", ""),
                "max_safe_depth": max_safe_depth,
                "geometry": data.get("geometry"),
            }

            # Forward edge
            self._add_or_update_edge(G_mode, u, v, edge_attrs)

            # Reverse edge if walking (or if way is not oneway for driving)
            is_oneway = self._parse_oneway(data.get("oneway", False))
            if ignore_oneway or not is_oneway:
                rev_attrs = dict(edge_attrs)
                if rev_attrs.get("geometry") is not None:
                    geom = rev_attrs["geometry"]
                    if isinstance(geom, LineString):
                        rev_attrs["geometry"] = LineString(list(geom.coords)[::-1])
                self._add_or_update_edge(G_mode, v, u, rev_attrs)

        logger.info(
            "Built profile '%s' graph: %d nodes, %d edges (safe depth limit: %.2fm)",
            mode,
            G_mode.number_of_nodes(),
            G_mode.number_of_edges(),
            max_safe_depth,
        )
        return G_mode

    def _is_highway_allowed(self, highway_val: Any, allowed: set) -> bool:
        if highway_val is None:
            return False
        if isinstance(highway_val, list):
            return any(h in allowed for h in highway_val)
        return str(highway_val) in allowed

    def _is_access_allowed(self, edge_data: dict, mode: str) -> bool:
        access = edge_data.get("access")
        if access in ["no", "private"]:
            return False

        if mode == "walking":
            foot = edge_data.get("foot")
            if foot in ["no", "private"]:
                return False
        elif mode == "driving":
            motor_vehicle = edge_data.get("motor_vehicle")
            motorcar = edge_data.get("motorcar")
            if motor_vehicle in ["no", "private"] or motorcar in ["no", "private"]:
                return False
        return True

    def _parse_oneway(self, oneway_val: Any) -> bool:
        if isinstance(oneway_val, bool):
            return oneway_val
        if isinstance(oneway_val, (int, float)):
            return oneway_val == 1
        if isinstance(oneway_val, str):
            return oneway_val.lower() in ["yes", "true", "1", "-1"]
        if isinstance(oneway_val, list):
            return any(self._parse_oneway(x) for x in oneway_val)
        return False

    def _get_driving_speed_mps(self, edge_data: dict) -> float:
        # Check maxspeed tag
        maxspeed_tag = edge_data.get("maxspeed")
        if maxspeed_tag:
            speed_kmh = self._parse_maxspeed(maxspeed_tag)
            if speed_kmh and speed_kmh > 0:
                return speed_kmh / 3.6

        # Fallback to defaults by highway type
        highway = edge_data.get("highway")
        if isinstance(highway, list):
            highway = highway[0]
        highway_str = str(highway) if highway else "default"

        defaults = self.config.speeds.driving_defaults_kmh
        speed_kmh = defaults.get(highway_str, defaults.get("default", 25.0))
        return speed_kmh / 3.6

    def _parse_maxspeed(self, maxspeed_val: Any) -> Optional[float]:
        if isinstance(maxspeed_val, (int, float)):
            return float(maxspeed_val)
        if isinstance(maxspeed_val, list):
            for v in maxspeed_val:
                parsed = self._parse_maxspeed(v)
                if parsed:
                    return parsed
            return None

        val_str = str(maxspeed_val).strip().lower()
        # Look for numbers
        match = re.search(r"(\d+(\.\d+)?)", val_str)
        if not match:
            return None

        num = float(match.group(1))
        if "mph" in val_str:
            return num * 1.60934
        if "knots" in val_str:
            return num * 1.852
        return num  # Default km/h

    def _add_or_update_edge(self, G: nx.DiGraph, u: Any, v: Any, attrs: dict) -> None:
        if G.has_edge(u, v):
            existing_time = G[u][v].get("travel_time", float("inf"))
            if attrs["travel_time"] < existing_time:
                G[u][v].update(attrs)
        else:
            G.add_edge(u, v, **attrs)
