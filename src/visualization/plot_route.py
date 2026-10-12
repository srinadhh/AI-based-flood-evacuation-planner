"""Visualizer for evacuation routes and flooded segments using Folium."""
from pathlib import Path
from typing import List, Optional
import folium
import networkx as nx

from ..routing.router import RouteResult
from ..scenarios.synthetic import SyntheticFloodScenario


def plot_route_folium(
    G: nx.DiGraph,
    result: RouteResult,
    shelters: Optional[List[dict]] = None,
    flood_scenario: Optional[SyntheticFloodScenario] = None,
    output_html_path: Optional[Path] = None,
) -> folium.Map:
    """
    Renders the evacuation route, origin, shelters, and flooded segments onto an interactive Folium map.
    """
    # Center map on origin node if coordinates are available
    orig_node = result.origin_node
    lat_center = G.nodes[orig_node].get("y", 13.010)
    lon_center = G.nodes[orig_node].get("x", 80.240)

    m = folium.Map(location=[lat_center, lon_center], zoom_start=14, tiles="OpenStreetMap")

    # Mark origin
    folium.Marker(
        [lat_center, lon_center],
        popup=f"Origin Node: {orig_node}",
        tooltip="Evacuation Origin",
        icon=folium.Icon(color="green", icon="user", prefix="fa"),
    ).add_to(m)

    # Mark shelters
    if shelters:
        for s in shelters:
            is_destination = (result.destination_node is not None) and (
                s.get("node") == result.destination_node or s.get("id") == str(result.destination_node)
            )
            color = "green" if is_destination else "blue"
            icon = "check-circle" if is_destination else "shield"
            folium.Marker(
                [s["lat"], s["lon"]],
                popup=f"Shelter: {s.get('name', s.get('id'))}",
                tooltip=s.get("name", s.get('id')),
                icon=folium.Icon(color=color, icon=icon, prefix="fa"),
            ).add_to(m)

    # Plot flooded segments in red if scenario provided
    if flood_scenario:
        flooded_fg = folium.FeatureGroup(name="Flooded Segments")
        for u, v in flood_scenario.static_edge_depths.keys():
            if u in G.nodes and v in G.nodes:
                p1 = (G.nodes[u].get("y"), G.nodes[u].get("x"))
                p2 = (G.nodes[v].get("y"), G.nodes[v].get("x"))
                if p1[0] and p1[1] and p2[0] and p2[1]:
                    depth = flood_scenario.get_edge_depth(u, v, 0.0)
                    folium.PolyLine(
                        [p1, p2],
                        color="red",
                        weight=5,
                        opacity=0.8,
                        popup=f"Flooded Edge ({u}->{v}) Depth: {depth:.2f}m",
                    ).add_to(flooded_fg)
        flooded_fg.add_to(m)

    # Plot successful path in blue/indigo
    if result.status == "SUCCESS" and result.path_nodes:
        route_fg = folium.FeatureGroup(name="Evacuation Route")
        coords = []
        for n in result.path_nodes:
            if n in G.nodes:
                lat = G.nodes[n].get("y")
                lon = G.nodes[n].get("x")
                if lat and lon:
                    coords.append((lat, lon))
        if coords:
            folium.PolyLine(
                coords,
                color="#0066cc",
                weight=6,
                opacity=0.9,
                popup=f"Safe Route ({result.mode.capitalize()}): {result.total_distance_meters:.0f}m in {result.total_time_seconds/60:.1f}min",
            ).add_to(route_fg)
        route_fg.add_to(m)

    folium.LayerControl().add_to(m)

    if output_html_path:
        output_html_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_html_path))

    return m
