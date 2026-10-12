# Project: Accurate flood evacuation route planner (MVP)

## Goal
Given a flood scenario, return walking and driving routes from any start point to the
nearest reachable shelter that were actually safe in reality. Accuracy comes first.
Speed, live updates, congestion/capacity modelling, offline mode and UI polish are
OUT OF SCOPE for this MVP.

## Study area and validation event
- Region: Adyar river basin, Chennai, India. Start with a compact area of a few
  neighbourhoods around the lower Adyar floodplain, not the whole city.
- Validation event: the December 2015 Chennai flood.

## Data (free sources only for now)
- Roads: OpenStreetMap
- Elevation: Copernicus GLO-30 DEM (30 m), downloaded from OpenTopography
- Observed flood extent: Sentinel-1 SAR flood mapping for the 2015 event
- Rainfall: IMD gridded rainfall (and/or GPM IMERG)
- I will download any data that needs an account or login and place it in /data.
  Never invent, simulate or fabricate data unless a task explicitly says "synthetic".
  Record every dataset's source, date, licence and known limitations in DATA_LOG.md.

## Flood model
- Do NOT use a simple bathtub model as the final model. Start with a physically
  motivated approach such as HAND (Height Above Nearest Drainage) derived from the DEM
  and a stream network, then propose improvements.
- State clearly in the docs that a 30 m DEM is coarse for flat urban terrain and
  explain how that limits accuracy.

## Routing
- Build a road graph from OSM with separate walking and driving profiles.
- Passability depends on flood depth and mode. Find published guidance on safe flood
  depths for walking and driving, cite the sources, keep thresholds configurable, and
  ask me to approve them before use. Do not guess numbers.
- Routes must be time-aware: check that each segment is still passable when it would
  actually be reached, not only at departure time.
- Handle the case where no safe route exists and say so clearly.

## Definition of accuracy (the evaluation deliverable)
Against the observed 2015 flood extent, report:
1. False-safe rate: share of segments the planner called safe that were actually flooded
   (the most serious error).
2. Over-block rate: share of segments it blocked that were actually dry.
3. Flood extent agreement: IoU and F1 between modelled and observed flooding.
Report results honestly, including poor results. Never tune the model on the same data
used for the final reported numbers without saying so.

## Working rules
- Work in milestones. After each one, stop, summarise what was done, show the results
  and wait for my approval before starting the next.
- Before each milestone, write a short plan and wait for my approval.
- Ask me before: installing large dependencies, downloading large files, deleting
  files, or making any assumption about thresholds, data or flood physics.
- Never put credentials or API keys in code. Only touch files inside this project folder.
- Add tests for routing and evaluation logic. If you are unsure something is physically
  correct, say so instead of presenting it as fact.
- Keep a CHANGELOG.md and update DATA_LOG.md as data is added.

## Milestones
1. Project setup, road graph from OSM, and routing on a hand-made test scenario
   (so the software can be tested before real flood data is in).
2. Data ingestion: DEM, rainfall and Sentinel-1 flood extent loaded and checked.
3. Flood model (HAND-based) producing depth per road segment.
4. Evaluation script and first accuracy report against the 2015 event.
5. Improve the model based on the report, then re-evaluate.
