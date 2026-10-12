"""Time-dependent evacuation route planning using modified Dijkstra."""
from dataclasses import dataclass, field
import heapq
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from .safety import SafetyEvaluator

logger = logging.getLogger(__name__)


@dataclass
class SegmentDetail:
    u: Any
    v: Any
    entry_time_seconds: float
    exit_time_seconds: float
    duration_seconds: float
    length_meters: float
    max_encountered_depth_m: float
    highway: Optional[Any] = None
    name: Optional[str] = None


@dataclass
class RouteResult:
    status: str  # "SUCCESS" or "NO_SAFE_ROUTE"
    mode: str
    origin_node: Any
    destination_node: Optional[Any] = None
    path_nodes: List[Any] = field(default_factory=list)
    total_time_seconds: float = 0.0
    total_distance_meters: float = 0.0
    departure_time_seconds: float = 0.0
    arrival_time_seconds: float = 0.0
    segments: List[SegmentDetail] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)


class EvacuationRouter:
    """Time-aware evacuation route planner."""

    def __init__(self, safety_evaluator: SafetyEvaluator):
        self.safety_evaluator = safety_evaluator

    def find_route(
        self,
        G: nx.DiGraph,
        origin_node: Any,
        destination_nodes: List[Any],
        departure_time_seconds: float = 0.0,
    ) -> RouteResult:
        """
        Finds the earliest-arrival safe route from origin_node to any node in destination_nodes.
        Respects time-dependent flood depth limits on each road segment during traversal.
        """
        mode = G.graph.get("profile_mode", "unknown")
        max_safe_depth = G.graph.get("max_safe_depth", 0.15)
        dest_set: Set[Any] = set(destination_nodes)

        if origin_node not in G:
            return RouteResult(
                status="NO_SAFE_ROUTE",
                mode=mode,
                origin_node=origin_node,
                diagnostics=[f"Origin node {origin_node} not found in road graph."],
            )

        valid_dests = [d for d in dest_set if d in G]
        if not valid_dests:
            return RouteResult(
                status="NO_SAFE_ROUTE",
                mode=mode,
                origin_node=origin_node,
                diagnostics=["None of the destination shelter nodes exist in the road graph."],
            )

        # Priority queue stores tuples: (arrival_time, node_id)
        pq: List[Tuple[float, Any]] = []
        heapq.heappush(pq, (departure_time_seconds, origin_node))

        # min_arrival[node] stores earliest arrival time reached
        min_arrival: Dict[Any, float] = {origin_node: departure_time_seconds}

        # predecessor[v] = (u, edge_data, entry_time, exit_time, max_depth)
        predecessor: Dict[Any, Tuple[Any, dict, float, float, float]] = {}

        flooded_bottlenecks: List[str] = []
        target_reached: Optional[Any] = None

        while pq:
            curr_time, u = heapq.heappop(pq)

            if curr_time > min_arrival[u]:
                continue

            if u in dest_set:
                target_reached = u
                break

            for v in G.neighbors(u):
                edge_data = G[u][v]
                duration = float(edge_data.get("travel_time", 1.0))
                edge_max_safe = float(edge_data.get("max_safe_depth", max_safe_depth))

                # Check passability during the exact arrival time window
                is_passable, max_depth = self.safety_evaluator.is_edge_passable(
                    u, v, curr_time, duration, edge_max_safe
                )

                if not is_passable:
                    flooded_bottlenecks.append(
                        f"Segment ({u} -> {v}) impassable: depth {max_depth:.2f}m > limit {edge_max_safe:.2f}m at t={curr_time:.1f}s"
                    )
                    continue

                arr_time_v = curr_time + duration

                if arr_time_v < min_arrival.get(v, float("inf")):
                    min_arrival[v] = arr_time_v
                    predecessor[v] = (u, edge_data, curr_time, arr_time_v, max_depth)
                    heapq.heappush(pq, (arr_time_v, v))

        if target_reached is None:
            # No safe route was found to any shelter
            return RouteResult(
                status="NO_SAFE_ROUTE",
                mode=mode,
                origin_node=origin_node,
                departure_time_seconds=departure_time_seconds,
                diagnostics=[
                    f"No safe route could reach any candidate shelter from node {origin_node}.",
                    f"Total blocked segment encounters: {len(flooded_bottlenecks)}.",
                ]
                + flooded_bottlenecks[:10],  # sample first 10 bottlenecks
            )

        # Reconstruct path
        path_nodes: List[Any] = []
        segments: List[SegmentDetail] = []
        curr = target_reached
        path_nodes.append(curr)

        total_distance = 0.0

        while curr != origin_node:
            prev_u, edge_data, entry_t, exit_t, max_d = predecessor[curr]
            length_m = float(edge_data.get("length", 0.0))
            total_distance += length_m

            seg = SegmentDetail(
                u=prev_u,
                v=curr,
                entry_time_seconds=entry_t,
                exit_time_seconds=exit_t,
                duration_seconds=exit_t - entry_t,
                length_meters=length_m,
                max_encountered_depth_m=max_d,
                highway=edge_data.get("highway"),
                name=edge_data.get("name"),
            )
            segments.append(seg)
            curr = prev_u
            path_nodes.append(curr)

        path_nodes.reverse()
        segments.reverse()

        arr_time = min_arrival[target_reached]
        total_time = arr_time - departure_time_seconds

        logger.info(
            "Found safe %s route from %s to shelter %s: %.1f meters in %.1f seconds",
            mode,
            origin_node,
            target_reached,
            total_distance,
            total_time,
        )

        return RouteResult(
            status="SUCCESS",
            mode=mode,
            origin_node=origin_node,
            destination_node=target_reached,
            path_nodes=path_nodes,
            total_time_seconds=total_time,
            total_distance_meters=total_distance,
            departure_time_seconds=departure_time_seconds,
            arrival_time_seconds=arr_time,
            segments=segments,
        )
