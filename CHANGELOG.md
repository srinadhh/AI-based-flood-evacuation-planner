# Changelog

All notable changes to the AI-Based Flood Evacuation Planner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.0] - 2026-10-12
### Added
- Milestone 1 completed: Project architecture, OSM road network, and time-aware routing backend.
- Configuration file `config/routing_config.yaml` specifying:
  - Adyar study area bounding box (`13.000°N` to `13.030°N`, `80.215°E` to `80.265°E`).
  - Literature-grounded safe flood depth thresholds: 0.15 m for walking (ARR Book 6 / DEFRA FD2320), 0.20 m for driving (Pregnolato et al. 2017 / FEMA).
  - Modal travel speed assumptions and highway classification access rules.
- OpenStreetMap graph extractor and disk caching (`src/graph/osm_loader.py`):
  - Fetched and cached Adyar floodplain network (3,350 nodes, 8,001 raw edges) in `data/processed/osm_cache/adyar_road_graph.graphml`.
  - Metric coordinate projection to UTM Zone 44N (`EPSG:32644`).
- Modal profile builder (`src/graph/profiles.py`):
  - Walking profile: bidirectional traversal, pedestrian way inclusion, constant 4.5 km/h walking speed (6,333 directed edges).
  - Driving profile: strict one-way rule enforcement, vehicle-accessible hierarchy, speed-limit and hierarchy traversal times (5,381 directed edges).
- Time-aware safety evaluator and router (`src/routing/safety.py`, `src/routing/router.py`):
  - Dynamic depth interval verification during segment traversal.
  - Modified time-dependent Dijkstra solver finding earliest-arrival reachable shelter.
  - Explicit diagnostic reporting when no safe route exists (`NO_SAFE_ROUTE`).
- Synthetic spatio-temporal flood test scenario generator (`src/scenarios/synthetic.py`).
- Automated pytest test suite across 9 test cases covering config parsing, modal profiles, depth safety checks, dynamic flood wave avoidance, and trapped island scenarios.
- Folium interactive route visualizer (`src/visualization/plot_route.py`) and demo script (`scripts/run_demo.py`).
- Provenance and limitation records in `DATA_LOG.md`.
