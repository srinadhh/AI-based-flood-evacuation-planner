from pathlib import Path
import sys
import logging

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import osmnx as ox
import networkx as nx

from src.config import AppConfig
from src.graph.osm_loader import OSMLoader
from src.graph.profiles import ProfileBuilder
from src.routing.safety import SafetyEvaluator
from src.routing.router import EvacuationRouter
from src.scenarios.synthetic import SyntheticFloodScenario
from src.visualization.plot_route import plot_route_folium
from src.utils.geo import find_nearest_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo")


def main():
    config = AppConfig.load_from_yaml()
    loader = OSMLoader(config)

    logger.info("=== Step 1: Loading OSM Road Graph for Adyar ===")
    G_raw = loader.load_graph(use_cache=True)
    logger.info("Raw graph loaded: %d nodes, %d edges", G_raw.number_of_nodes(), G_raw.number_of_edges())

    logger.info("=== Step 2: Projecting Graph to Metric CRS (%s) ===", config.crs.projected)
    G_proj = loader.project_graph(G_raw)

    logger.info("=== Step 3: Building Walking and Driving Profile Graphs ===")
    profile_builder = ProfileBuilder(config)
    G_walk = profile_builder.build_profile_graph(G_proj, "walking")
    G_drive = profile_builder.build_profile_graph(G_proj, "driving")

    logger.info("Walking graph: %d nodes, %d edges", G_walk.number_of_nodes(), G_walk.number_of_edges())
    logger.info("Driving graph: %d nodes, %d edges", G_drive.number_of_nodes(), G_drive.number_of_edges())

    logger.info("=== Step 4: Setting up Candidate Shelters and Origin ===")
    # Shelters from config
    shelter_nodes = []
    shelters_info = []
    for s in config.default_shelters:
        node = find_nearest_node(G_proj, lat=s.lat, lon=s.lon)
        shelter_nodes.append(node)
        shelters_info.append({"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon, "node": node})
        logger.info("Shelter '%s' matched to node %s", s.name, node)

    # Pick an origin near low-lying Kotturpuram (lat: 13.0185, lon: 80.2410)
    origin_lat, origin_lon = 13.0185, 80.2410
    origin_node = find_nearest_node(G_proj, lat=origin_lat, lon=origin_lon)
    logger.info("Origin (Kotturpuram area) matched to node %s", origin_node)

    logger.info("=== Step 5: Constructing Flood Scenario ===")
    # Hand-made scenario: simulated flood along Kotturpuram low-lying riverbank links
    scenario = SyntheticFloodScenario("Adyar Riverbank Spatio-Temporal Flood")

    # Identify edges near the river or origin to simulate dynamic rising water
    test_flooded_count = 0
    for u, v in list(G_drive.edges())[:20]:  # select a subset of nearby corridors
        scenario.set_dynamic_edge_curve(
            u=u,
            v=v,
            start_time_seconds=300.0,
            peak_time_seconds=900.0,
            peak_depth_m=0.55,
            base_depth_m=0.0,
        )
        test_flooded_count += 1
    logger.info("Configured dynamic flood curve for %d test segments", test_flooded_count)

    evaluator = SafetyEvaluator(scenario)
    router = EvacuationRouter(evaluator)

    logger.info("=== Step 6: Planning Evacuation Routes ===")
    # Plan driving route
    drive_result = router.find_route(
        G=G_drive,
        origin_node=origin_node,
        destination_nodes=shelter_nodes,
        departure_time_seconds=0.0,
    )
    logger.info(
        "Driving Route Result: %s | Distance: %.1fm | Time: %.1fs (%.1f min) | Destination Node: %s",
        drive_result.status,
        drive_result.total_distance_meters,
        drive_result.total_time_seconds,
        drive_result.total_time_seconds / 60.0,
        drive_result.destination_node,
    )

    # Plan walking route
    walk_result = router.find_route(
        G=G_walk,
        origin_node=origin_node,
        destination_nodes=shelter_nodes,
        departure_time_seconds=0.0,
    )
    logger.info(
        "Walking Route Result: %s | Distance: %.1fm | Time: %.1fs (%.1f min) | Destination Node: %s",
        walk_result.status,
        walk_result.total_distance_meters,
        walk_result.total_time_seconds,
        walk_result.total_time_seconds / 60.0,
        walk_result.destination_node,
    )

    logger.info("=== Step 7: Generating Map Artifact ===")
    output_html = Path(__file__).resolve().parent.parent / "data" / "processed" / "route_visualization.html"
    plot_route_folium(
        G=G_raw,
        result=drive_result,
        shelters=shelters_info,
        flood_scenario=scenario,
        output_html_path=output_html,
    )
    logger.info("Saved interactive route visualization to: %s", output_html)


if __name__ == "__main__":
    main()
