"""Geospatial helper functions for coordinate transforms and spatial search."""
from typing import Any
import pyproj
import osmnx as ox
import networkx as nx


def find_nearest_node(
    G_proj: nx.MultiDiGraph,
    lat: float,
    lon: float,
    from_crs: str = "EPSG:4326",
) -> Any:
    """
    Finds the nearest node in a projected metric graph given geographic (lat, lon) coordinates.
    Transforms coordinates to match the projected graph's CRS before querying KDTree.
    """
    to_crs = G_proj.graph.get("crs", "EPSG:32644")
    transformer = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True)
    proj_x, proj_y = transformer.transform(lon, lat)
    return ox.distance.nearest_nodes(G_proj, X=proj_x, Y=proj_y)
