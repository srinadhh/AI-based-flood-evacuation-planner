"""OpenStreetMap road graph loader with caching and coordinate projection."""
from pathlib import Path
from typing import Optional, Tuple
import logging
import networkx as nx
import osmnx as ox

from ..config import AppConfig, BBoxConfig

logger = logging.getLogger(__name__)


class OSMLoader:
    """Loads and caches OpenStreetMap road networks for the study area."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load_from_yaml()
        self.cache_dir = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "osm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_cache_file = self.cache_dir / "adyar_road_graph.graphml"

    def load_graph(
        self,
        bbox: Optional[BBoxConfig] = None,
        cache_path: Optional[Path] = None,
        use_cache: bool = True,
        force_reload: bool = False,
    ) -> nx.MultiDiGraph:
        """Loads an OSM MultiDiGraph, downloading or loading from local cache."""
        target_bbox = bbox or self.config.bbox
        target_cache = cache_path or self.default_cache_file

        if use_cache and not force_reload and target_cache.exists():
            logger.info("Loading OSM graph from cache: %s", target_cache)
            try:
                G = ox.load_graphml(target_cache)
                # Ensure CRS is set
                if G.graph.get("crs") is None:
                    G.graph["crs"] = self.config.crs.geographic
                return G
            except Exception as e:
                logger.warning("Failed to load cached graph from %s: %s. Fetching fresh data.", target_cache, e)

        logger.info(
            "Fetching OSM graph for bbox: S=%.4f, N=%.4f, W=%.4f, E=%.4f",
            target_bbox.south,
            target_bbox.north,
            target_bbox.west,
            target_bbox.east,
        )

        G = self._download_graph_from_bbox(target_bbox)

        if use_cache:
            try:
                logger.info("Saving OSM graph to cache: %s", target_cache)
                ox.save_graphml(G, target_cache)
            except Exception as e:
                logger.warning("Could not cache graph to %s: %s", target_cache, e)

        return G

    def _download_graph_from_bbox(self, bbox: BBoxConfig) -> nx.MultiDiGraph:
        """Calls OSMnx to download all road and pedestrian ways in the bounding box."""
        # Handles both OSMnx >= 2.0 (bbox tuple or keyword) and older versions
        try:
            # osmnx 2.0+ format: bbox=(north, south, east, west) or (west, south, east, north)
            # In osmnx 2.0: bbox = (left, bottom, right, top) i.e. (west, south, east, north)
            G = ox.graph_from_bbox(
                bbox=(bbox.west, bbox.south, bbox.east, bbox.north),
                network_type="all",
                simplify=True,
                retain_all=True,
            )
        except TypeError:
            try:
                # osmnx 1.9 format: bbox=(north, south, east, west)
                G = ox.graph_from_bbox(
                    bbox=(bbox.north, bbox.south, bbox.east, bbox.west),
                    network_type="all",
                    simplify=True,
                    retain_all=True,
                )
            except TypeError:
                # older osmnx format: positional north, south, east, west
                G = ox.graph_from_bbox(
                    bbox.north,
                    bbox.south,
                    bbox.east,
                    bbox.west,
                    network_type="all",
                    simplify=True,
                    retain_all=True,
                )

        return G

    def project_graph(self, G: nx.MultiDiGraph, to_crs: Optional[str] = None) -> nx.MultiDiGraph:
        """Projects the graph to a local metric coordinate reference system (e.g. UTM 44N)."""
        target_crs = to_crs or self.config.crs.projected
        logger.info("Projecting graph to CRS: %s", target_crs)
        G_proj = ox.project_graph(G, to_crs=target_crs)
        return G_proj
