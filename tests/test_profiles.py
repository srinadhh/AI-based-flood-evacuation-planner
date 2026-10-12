"""Tests for profile building and network separation."""
import networkx as nx
import pytest
from src.config import AppConfig
from src.graph.profiles import ProfileBuilder


@pytest.fixture
def base_multidigraph():
    """Constructs a small synthetic MultiDiGraph with diverse highway types and oneways."""
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    # Add nodes
    G.add_node(1, x=80.22, y=13.01)
    G.add_node(2, x=80.23, y=13.01)
    G.add_node(3, x=80.24, y=13.01)
    G.add_node(4, x=80.25, y=13.01)

    # Edge 1->2: Motorway, oneway=True, length=1000m
    G.add_edge(1, 2, key=0, highway="motorway", oneway=True, length=1000.0, maxspeed="60")

    # Edge 2->3: Footway, oneway=False, length=200m
    G.add_edge(2, 3, key=0, highway="footway", oneway=False, length=200.0)

    # Edge 3->4: Primary road, oneway=True, length=500m
    G.add_edge(3, 4, key=0, highway="primary", oneway=True, length=500.0, maxspeed="40")

    return G


def test_walking_profile_filtering_and_bidirectionality(base_multidigraph):
    builder = ProfileBuilder()
    G_walk = builder.build_profile_graph(base_multidigraph, "walking")

    # Motorway should be excluded for walking
    assert not G_walk.has_edge(1, 2)
    assert not G_walk.has_edge(2, 1)

    # Footway should be included and bidirectional
    assert G_walk.has_edge(2, 3)
    assert G_walk.has_edge(3, 2)

    # Primary road should be included and bidirectional for pedestrians (ignores oneway)
    assert G_walk.has_edge(3, 4)
    assert G_walk.has_edge(4, 3)

    # Safe depth limit should be 0.15m
    assert G_walk.graph["max_safe_depth"] == 0.15

    # Check walking travel time: 500m / (4.5 km/h / 3.6 = 1.25 m/s) = 400.0s
    assert pytest.approx(G_walk[3][4]["travel_time"], rel=1e-2) == 400.0


def test_driving_profile_filtering_and_oneway(base_multidigraph):
    builder = ProfileBuilder()
    G_drive = builder.build_profile_graph(base_multidigraph, "driving")

    # Motorway should be included, strictly one-way
    assert G_drive.has_edge(1, 2)
    assert not G_drive.has_edge(2, 1)

    # Footway must be excluded for driving
    assert not G_drive.has_edge(2, 3)
    assert not G_drive.has_edge(3, 2)

    # Primary road included, strictly one-way
    assert G_drive.has_edge(3, 4)
    assert not G_drive.has_edge(4, 3)

    # Safe depth limit should be 0.20m
    assert G_drive.graph["max_safe_depth"] == 0.20

    # Driving travel time on primary: 500m / (40 / 3.6 m/s) = 45.0s
    assert pytest.approx(G_drive[3][4]["travel_time"], rel=1e-2) == 45.0
