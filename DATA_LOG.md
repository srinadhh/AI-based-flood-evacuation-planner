# Data Log

This document records every dataset used in the project, including its source, date obtained, license, geographical/temporal coverage, and known limitations.

---

## 1. OpenStreetMap (OSM) Road Graph (Milestone 1)
- **Source**: OpenStreetMap via Overpass API / OSMnx
- **Date Retrieved**: 2026-10-12
- **License**: [Open Data Commons Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/)
- **Geographic Coverage**: Lower Adyar Floodplain, Chennai, India
  - South: 13.000° N
  - North: 13.030° N
  - West: 80.215° E
  - East: 80.265° E
  - Projected Coordinate System: EPSG:32644 (WGS 84 / UTM Zone 44N)
- **Local Storage**: `data/processed/osm_cache/adyar_road_graph.graphml`
- **Known Limitations**:
  - Speed limits (`maxspeed`) may be missing for some secondary and residential roads, requiring hierarchical fallbacks.
  - Sidewalk and pedestrian attributes (`sidewalk`, `footway`) may be incomplete on minor roads.
  - Temporary local barricades or unmapped road construction in Chennai are not reflected in static OSM.

---

## 2. Synthetic Flood Scenario (Milestone 1 - Validation)
- **Source**: Deterministic synthetic test generation (`src/scenarios/synthetic.py`)
- **Date Created**: 2026-10-12
- **License**: Internal / MIT Project License
- **Purpose**: Unit and regression testing of time-dependent Dijkstra route finding and dynamic bottleneck evasion prior to ingestion of real Sentinel-1 / DEM flood data in Milestone 2.
- **Known Limitations**:
  - Synthetic spatial and temporal depth curves do not reflect hydrodynamic flow equations; designed solely for routing logic correctness verification.
