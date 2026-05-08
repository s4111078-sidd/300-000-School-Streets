# 300,000 Streets of Melbourne — School Streets Safety Analysis

A pedestrian safety assessment and machine learning risk prediction tool for walking routes around secondary schools in Melbourne. Built in collaboration between **Regen Melbourne** and **RMIT University**.

---

## Schools assessed (field observations)

| School | Address | Gate coordinates |
|---|---|---|
| Reservoir High School | 855 Plenty Rd, Reservoir VIC 3073 | -37.7224, 145.0294 |
| William Ruthven Secondary College | 60 Merrilands Rd, Reservoir VIC 3073 | -37.69654, 145.00299 |
| Preston High School | 2-16 Cooma St, Preston VIC 3072 | -37.7417, 145.0071 |

---

## Scoring system

Each assessed location is scored across four dimensions (0 = worst, 10 = best):

| Score | Meaning |
|---|---|
| **FAS** — Footpath Accessibility Score | Footpath presence, width, continuity, and condition |
| **CSS** — Crossing Safety Score | Crossing type, distance, visibility, and signals |
| **EEI** — Environmental Exposure Indicator | Traffic volume, speed, lighting, and school zone |
| **CIS** — Cycling Infrastructure Score | Type of cycling infrastructure present on the school frontage road |

Overall score = average of FAS + CSS + EEI + CIS. A score of **6.0 or above** is considered good.

CIS is derived from the observed cycling infrastructure type, scored against two published frameworks:

- **Level of Traffic Stress (LTS)** — Mekuria, Furth & Nixon (2012), Mineta Transportation Institute, San José State University. LTS 1 = low stress, suitable for children. LTS 4 = high stress, suitable only for experienced adults.
- **VicRoads TEM Vol. 3 Part 218** — facility selection hierarchy for strategically important cycling corridors. Off-road or physically separated facilities are the preferred provision on school routes.

Scores below 6.0 indicate infrastructure not considered appropriate for school-age cyclists.

| Cycling infrastructure | LTS | VicRoads preference | CIS |
|---|---|---|---|
| Separated bike lane (physically protected) | LTS 1 | Tier 1 — preferred | 9.0 |
| Shared path or greenway (off-road) | LTS 1 | Tier 1 — preferred | 8.0 |
| Painted bike lane (on-road, no separation) | LTS 2–3 | Tier 2–3 | 4.5 |
| Advisory lane / shared road marking | LTS 3–4 | Tier 4 | 2.0 |
| No cycling infrastructure | LTS 4 equivalent | Not recommended | 1.0 |

> Note: the commonly cited "Austroads LoS A–F" for cycling does not exist as an Austroads standard — that framing derives from the US Highway Capacity Manual BLOS model. The Austroads cycling tool is a 100-point numeric instrument (AP-R724-25). LTS and VicRoads TEM Part 218 are the appropriate cited standards for this project.

Hazard severity is classified as **Major**, **Moderate**, or **Minor**.

### CYS — how it is computed

CYS is derived automatically from OpenStreetMap cycling network data by `spatial_features.py` and scored inside `poc_pipeline.py`. No manual data entry is required.

| Component | Data source | Points |
|---|---|---|
| Cycling network coverage (`cycle_pct_400m`) | OSM bike network length ÷ walk network length within 400m | 0–4 |
| Protected infrastructure (`protected_cycle_length_400m`) | Length of dedicated cycleways or separated tracks within 400m | 0–3 |
| Crossing safety (`signals_400m` + `crossing_density_400m`) | Traffic signals ≥ 3 → +1 · crossing density ≥ 1/km → +1 | 0–2 |
| Speed environment (`avg_speed_400m`) | Average road speed ≤ 40 km/h within 400m | 0–1 |

**Current scores (computed from OSM):**

| School | CYS | Key reason |
|---|---|---|
| Reservoir HS | 8.0 | 43% cycling coverage + 202m of protected lanes within 400m |
| Preston HS | 6.0 | 45% cycling coverage, good signals and crossings, but no protected lanes |
| William Ruthven SC | 5.0 | 39% cycling coverage, zero protected infrastructure, high average road speed (70 km/h) |

> **To override with field data:** add a column `Cycling Safety Score — CYS (0 to 10)` to `school_data.csv`. `poc_pipeline.py` will use the manual value if present, otherwise falls back to the OSM-computed score.

---

## Project structure

```
300-000-School-Streets/
├── school_data.csv              ← Field observation data (update to refresh outputs)
├── demographics_darebin.csv     ← ABS Census 2021 demographic data for Reservoir & Preston
├── requirements.txt             ← Python dependencies
│
├── crash_analysis.py            ← Downloads Victorian statewide ped/cyc crash data
├── spatial_features.py          ← OSM walking network, roads, crossings per school (optional)
├── feature_engineering.py       ← Builds ML training matrix from crash + spatial data
├── poc_pipeline.py              ← Charts, interactive maps, and recommendations
├── pyqgis_pipeline.py           ← GIS automation: KDE heatmap, buffers, layers, PNG exports
│
└── outputs/
    ├── crash_data_statewide.csv     ← All Victorian ped/cyc crashes (last 5 yrs)
    ├── crash_data_darebin.csv       ← Darebin subset within 400m of 3 school gates
    ├── spatial_features.csv         ← OSM features per school at 200m/400m/800m
    ├── ml_features.csv              ← Feature matrix ready for model training
    │
    ├── chart1_safety_scores.png     ← Produced by poc_pipeline.py
    ├── chart2_hazard_severity.png
    ├── chart3_score_breakdown.png
    ├── chart4_demographics.png
    ├── heatmap.png
    ├── map_interactive.html         ← Interactive map (open in browser)
    ├── map_heatmap.html             ← Interactive heatmap with crash markers
    ├── recommendations.csv
    │
    ├── kde_heatmap.tif              ← Produced by pyqgis_pipeline.py (GeoTIFF raster)
    ├── map_Preston_HS.png           ← Per-school static map exports
    ├── map_Reservoir_HS.png
    ├── map_William_Ruthven_SC.png
    ├── school_streets.gpkg          ← GeoPackage with all vector layers
    └── school_streets.qgz           ← QGIS project file (open directly in QGIS)
```

---

## Input data files

### `school_data.csv`
Field observation data collected at each assessed location. One row per location. Key columns:

| Column | Description |
|---|---|
| School name | One of the three schools |
| Latitude / Longitude | Decimal degrees |
| FAS / CSS / EEI | Scores 0–10 |
| Overall hazard severity | Major / Moderate / Minor |
| Street or location being assessed | Free text |
| Approximate distance from school gate (metres) | Numeric |
| (30+ additional columns) | Footpath, crossing, traffic, lighting details |

### `demographics_darebin.csv`
ABS Census 2021 demographic data for the suburbs surrounding each school. Columns: suburb, nearby school, total population, median household income, car ownership, transport mode shares, workforce participation, proportion of children aged 5–17.

---

## How to run

### Full pipeline (recommended — runs everything in order)

```
crash_analysis.py  →  spatial_features.py  →  poc_pipeline.py  →  pyqgis_pipeline.py
                                          ↘  feature_engineering.py
```

> `spatial_features.py` is now a key step — it computes the **CYS cycling score** used by `poc_pipeline.py` in addition to OSM features for the ML pipeline. Run it before `poc_pipeline.py` to get cycling scores in your charts and maps.

### Quick run (charts and maps only, no cycling score or ML)

```
crash_analysis.py  →  poc_pipeline.py  →  pyqgis_pipeline.py
```

### ML pipeline only

```
crash_analysis.py  →  spatial_features.py  →  feature_engineering.py
```

---

## Step 1 — Download crash data (`crash_analysis.py`)

Downloads Victorian road crash data from [data.vic.gov.au](https://data.vic.gov.au) and filters for:
- Statewide pedestrian or cyclist involvement
- Last 5 years
- All Victorian government secondary schools as proximity targets (downloaded from DET; falls back to 3 Darebin gates if unavailable)

```bash
pip install pandas numpy requests
python crash_analysis.py
```

**Outputs:**

| File | Description |
|---|---|
| `outputs/crash_data_statewide.csv` | All Victorian ped/cyc crashes with `nearest_school` and `dist_to_gate_m` |
| `outputs/crash_data_darebin.csv` | Darebin subset within 400m of the original 3 school gates (backward compat) |

Key columns: `ACCIDENT_NO`, `ACCIDENT_DATE`, `SEVERITY`, `SPEED_ZONE`, `LATITUDE`, `LONGITUDE`, `LGA_NAME`, `nearest_school`, `dist_to_gate_m`, `PED_OR_CYC`.

> Downloads three tables from the Victorian Open Data portal (`accident.csv`, `node.csv`, `person.csv`) joined on `ACCIDENT_NO`. School gates are fetched from the DET school-locations-time-series dataset (government, secondary/combined, open status) with a Victoria bounding-box validity check.

---

## Step 1b — OSM spatial features + CYS source data (`spatial_features.py`)

Computes OpenStreetMap-based spatial features for each school gate at **200m, 400m, and 800m** buffer radii. Uses **EPSG:7855** (GDA2020 / MGA zone 55) for accurate metric distances.

**This step is required to auto-compute the CYS cycling score in `poc_pipeline.py`.** It is also used by `feature_engineering.py` for the ML pipeline.

```bash
pip install geopandas osmnx shapely pyproj networkx
python spatial_features.py
```

> Makes ~4 Overpass API calls per school per radius (walk, drive, crossings, signals, bike network). Expect **1–2 minutes per school**. Individual failures fall back to `NaN` rather than crashing.

**Feature groups (per radius — 15 features × 3 radii = 45 total):**

| Group | Features |
|---|---|
| Walking network | `walk_edges`, `walk_length_m`, `footpath_length_m`, `footpath_pct` |
| Road network | `road_count`, `arterial_count`, `arterial_pct`, `avg_speed_kmh`, `high_speed_road_count` |
| Crossings | `crossings`, `signals` |
| Cycling network | `cycle_length_m`, `protected_cycle_length_m`, `cycle_pct` |
| Derived | `crossing_density` (crossings per km of walkable path) |

**Output:** `outputs/spatial_features.csv` — 45 features per school gate.

> **Cycling columns** (`cycle_length_*`, `protected_cycle_length_*`, `cycle_pct_*`) are what `poc_pipeline.py` reads to compute the CYS score. If this file is missing or the cycling columns are absent, CYS will show as N/A in all charts.

---

## Step 1c — Build ML feature matrix (`feature_engineering.py`)

Reads `crash_data_statewide.csv` and engineers features for model training. Automatically merges `spatial_features.csv` if it exists.

```bash
python feature_engineering.py
```

**Base features (13):**

| Group | Features |
|---|---|
| Time | `hour`, `day_of_week`, `month`, `is_weekend`, `is_school_hours` |
| Speed | `speed_zone_num`, `is_high_speed_zone` |
| Road | `road_geometry_code` |
| Geometry | `no_of_vehicles` |
| Lighting | `light_condition_code`, `is_dark` |
| School proximity | `dist_to_gate_m`, `near_school_400m` |

**Target variable:** `serious_or_fatal` — 1 if SEVERITY is fatal (1) or serious injury (2), else 0.

**Output:** `outputs/ml_features.csv` — one row per crash, ready for model training.

---

## Step 2 — Charts, interactive maps, and recommendations (`poc_pipeline.py`)

Reads `school_data.csv`, `demographics_darebin.csv`, and optionally `outputs/crash_data_darebin.csv` and `outputs/spatial_features.csv`.

```bash
pip install pandas matplotlib numpy folium rasterio
python poc_pipeline.py
```

**CYS score loading priority:**
1. Manual field data — `Cycling Safety Score — CYS (0 to 10)` column in `school_data.csv` (if present)
2. Auto-computed from OSM — reads `spatial_features.csv` and applies the CYS scoring rubric
3. N/A — if neither source is available (charts show grey N/A bar)

**Outputs saved to `outputs/`:**

| File | Description |
|---|---|
| `chart1_safety_scores.png` | FAS / CSS / EEI / CYS scores per school (4 bars) |
| `chart2_hazard_severity.png` | Hazard severity counts per school |
| `chart3_score_breakdown.png` | Per-location score breakdown including CYS |
| `chart4_demographics.png` | Demographic context (income, car ownership, transport mode) |
| `heatmap.png` | Static heatmap of assessment point scores |
| `map_interactive.html` | Interactive map — click markers for FAS / CSS / EEI / CYS and crash data |
| `map_heatmap.html` | Interactive heatmap with crash markers overlay |
| `recommendations.csv` | Auto-generated rule-based intervention list (15 rules including CYS thresholds) |

Open HTML files by double-clicking in Finder, or drag into any browser.

---

## Step 3 — GIS layers and map exports (`pyqgis_pipeline.py`)

Requires **QGIS 3.x** installed. Run Step 1 first so `outputs/crash_data_darebin.csv` exists (the crash layer is skipped gracefully if the file is missing).

**From the QGIS Python Console** (recommended):
```python
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

**Standalone** (edit `QGIS_PREFIX` at the top of the script to match your QGIS install path):
```bash
python pyqgis_pipeline.py
```

**Outputs saved to `outputs/`:**

| File | Description |
|---|---|
| `kde_heatmap.tif` | KDE raster (GeoTIFF, EPSG:7855) |
| `school_streets.gpkg` | GeoPackage with all vector layers |
| `school_streets.qgz` | QGIS project — open directly in QGIS |
| `map_<School>.png` | Per-school static map image (1200×900 px) |

**Layers created in QGIS (bottom to top):**

| Layer | Style |
|---|---|
| OpenStreetMap | XYZ tile base map |
| Hazard Heatmap (KDE) | Green → yellow → red gradient, 65% opacity |
| 800m Walking Zone | Light grey buffer ring |
| 400m Walking Zone | Dark grey buffer ring |
| Road Crashes (ped/cyc) | Blue diamond markers — from `crash_data_darebin.csv` |
| Safety Assessment Points | Circles coloured by severity (red / orange / green) |
| School Gates | Black star markers |

Buffers use **EPSG:7855** (GDA2020 / MGA zone 55) for accurate metric distances.

Only schools with rows in `school_data.csv` get a gate marker and buffers. Schools with no data are automatically skipped.

---

## Updating the data

1. Edit `school_data.csv` with new field observations.
2. Re-run `crash_analysis.py` to refresh crash data (downloads live from data.vic.gov.au).
3. Re-run `spatial_features.py` to refresh OSM cycling and spatial data (updates CYS scores).
4. Re-run `feature_engineering.py` to rebuild the ML feature matrix.
5. Re-run `poc_pipeline.py` → `pyqgis_pipeline.py` to regenerate all charts, maps, and QGIS outputs.

**To add a new school:** add its gate coordinates to `SCHOOL_GATES` in both `crash_analysis.py` and `spatial_features.py`, add field observation rows to `school_data.csv`, and re-run the full pipeline.

**To override CYS with field data:** add a column `Cycling Safety Score — CYS (0 to 10)` to `school_data.csv`. The pipeline will use this instead of the OSM-computed value.

---

## Dependencies

| Script | Requirements |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `spatial_features.py` | `geopandas`, `osmnx`, `shapely`, `pyproj`, `networkx` |
| `feature_engineering.py` | `pandas`, `numpy` |
| `poc_pipeline.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `rasterio`, `scipy` |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS — not pip-installable) |

Install pip dependencies:
```bash
pip install -r requirements.txt
```

> `pyqgis_pipeline.py` requires QGIS 3.x to be installed separately. It cannot be installed via pip.

---

## Crash data source

Victorian Road Crash Data is published by the Department of Transport and Planning:
[https://www.data.vic.gov.au/data/dataset/victoria-road-crash-data](https://www.data.vic.gov.au/data/dataset/victoria-road-crash-data)

Tables used: `accident.csv`, `node.csv` (coordinates + LGA), `person.csv` (road user type).

School gate locations sourced from the DET School Locations Time Series dataset:
[https://www.data.vic.gov.au/data/dataset/school-locations-time-series](https://www.data.vic.gov.au/data/dataset/school-locations-time-series)

---

## Dataset reference

### `outputs/crash_data_statewide.csv`

Produced by `crash_analysis.py`. One row per pedestrian or cyclist crash in Victoria over the last 5 years.

**Current snapshot:** 7,809 crashes · May 2021 – Dec 2025

**Severity breakdown:**

| SEVERITY value | Meaning | Count |
|---|---|---|
| 1 | Fatal | 201 |
| 2 | Serious injury | 3,170 |
| 3 | Other injury | 4,438 |

**All columns:**

| Column | Type | Description |
|---|---|---|
| `ACCIDENT_NO` | string | Unique crash identifier (e.g. `T20210000001`) |
| `ACCIDENT_DATE` | date | Date of crash (parsed to YYYY-MM-DD) |
| `ACCIDENT_TIME` | string | Time of crash (HHMM format) |
| `ACCIDENT_TYPE` | integer | Crash type code |
| `ACCIDENT_TYPE_DESC` | string | Crash type description (e.g. `Collision with vehicle`) |
| `DAY_OF_WEEK` | integer | Day code (1 = Monday … 7 = Sunday) |
| `DAY_WEEK_DESC` | string | Day name |
| `DCA_CODE` | integer | Crash configuration code |
| `DCA_DESC` | string | Crash configuration description |
| `LIGHT_CONDITION` | integer | 1 = Day · 2 = Dusk/dawn · 3–6 = Various night conditions |
| `NODE_ID` | integer | Road node identifier |
| `NO_OF_VEHICLES` | integer | Number of vehicles involved |
| `NO_PERSONS_KILLED` | integer | Number of fatalities |
| `NO_PERSONS_INJ_2` | integer | Number of serious injuries |
| `NO_PERSONS_INJ_3` | integer | Number of other injuries |
| `NO_PERSONS_NOT_INJ` | integer | Number of people not injured |
| `NO_PERSONS` | integer | Total persons involved |
| `POLICE_ATTEND` | integer | 1 = Police attended |
| `ROAD_GEOMETRY` | integer | Road geometry code (1 = Cross intersection · 2 = T-intersection · etc.) |
| `ROAD_GEOMETRY_DESC` | string | Road geometry description |
| `SEVERITY` | integer | Crash severity: 1 Fatal · 2 Serious · 3 Other injury |
| `SPEED_ZONE` | integer | Posted speed limit at crash location (km/h) |
| `RMA` | string | Road management authority |
| `LGA_NAME` | string | Local Government Area name |
| `LATITUDE` | float | Crash latitude (WGS84) |
| `LONGITUDE` | float | Crash longitude (WGS84) |
| `POSTCODE_CRASH` | integer | Postcode of crash location |
| `PED_OR_CYC` | boolean | True if crash involved a pedestrian or cyclist |
| `nearest_school` | string | Name of the closest Victorian government secondary school gate |
| `dist_to_gate_m` | float | Haversine distance in metres to the nearest school gate |

---

### `outputs/ml_features.csv`

Produced by `feature_engineering.py` (after running `crash_analysis.py` and optionally `spatial_features.py`). One row per crash — the training-ready feature matrix for the ML model.

**Current snapshot:** 7,809 rows · 52 columns · 43.2% serious/fatal (target positive rate)

#### Identifier columns

| Column | Description |
|---|---|
| `ACCIDENT_NO` | Crash identifier — links back to `crash_data_statewide.csv` |
| `nearest_school` | Name of the nearest school gate — links to `spatial_features.csv` |

#### Target variable

| Column | Description |
|---|---|
| `serious_or_fatal` | **1** if SEVERITY is 1 (fatal) or 2 (serious injury) · **0** otherwise |

#### Time features

| Column | Description |
|---|---|
| `hour` | Hour of crash (0–23) |
| `day_of_week` | Day of week (0 = Monday … 6 = Sunday) |
| `month` | Month (1–12) |
| `is_weekend` | 1 if Saturday or Sunday |
| `is_school_hours` | 1 if weekday and hour is 7–9 or 14–17 |

#### Speed and road features

| Column | Description |
|---|---|
| `speed_zone_num` | Posted speed limit (km/h) as a number |
| `is_high_speed_zone` | 1 if speed zone ≥ 60 km/h |
| `road_geometry_code` | Road geometry code from the crash record |
| `no_of_vehicles` | Number of vehicles involved in the crash |

#### Lighting features

| Column | Description |
|---|---|
| `light_condition_code` | Raw light condition code (1 = Day · 2–6 = Night/dusk) |
| `is_dark` | 1 if light condition code > 1 |

#### School proximity features

| Column | Description |
|---|---|
| `dist_to_gate_m` | Distance in metres to the nearest school gate |
| `near_school_400m` | 1 if crash is within 400m of a school gate |

#### OSM spatial features — per buffer radius (200m / 400m / 800m)

These are merged from `spatial_features.csv`. Only present if `spatial_features.py` has been run.

| Column pattern | Description |
|---|---|
| `walk_edges_{r}m` | Number of walkable path segments within radius |
| `walk_length_{r}m` | Total length of walkable network (metres) |
| `footpath_length_{r}m` | Length of dedicated footpaths only (metres) |
| `footpath_pct_{r}m` | Footpaths as a percentage of total walkable network |
| `road_count_{r}m` | Number of driveable road segments within radius |
| `arterial_count_{r}m` | Number of arterial/trunk road segments |
| `arterial_pct_{r}m` | Arterial roads as a percentage of total road network |
| `avg_speed_{r}m` | Average posted speed limit across road segments (km/h) |
| `high_speed_road_{r}m` | Number of road segments with speed limit ≥ 60 km/h |
| `crossings_{r}m` | Number of OSM-tagged pedestrian crossings |
| `signals_{r}m` | Number of OSM-tagged traffic signals |
| `crossing_density_{r}m` | Crossings per kilometre of walkable path |
| `cycle_length_{r}m` | Total length of OSM bikeable network within radius (metres) |
| `protected_cycle_length_{r}m` | Length of dedicated cycleways and physically separated tracks (metres) |
| `cycle_pct_{r}m` | Cycling network as a percentage of the walkable network |

> **Note on nulls:** `signals_200m` is null for ~84% of crashes because most school gates have no traffic signals within 200m. `avg_speed_200m` and `high_speed_road_200m` are null for ~20% where OSM road data is incomplete. Treat nulls as informative — impute with 0 or median before training.

#### CYS score feature

| Column | Description |
|---|---|
| `cys_score` | Cycling Safety Score (0–10) averaged per school, joined from `school_data.csv` if the CYS column is present, otherwise NaN |

---

*300,000 Streets of Melbourne — Regen Melbourne x RMIT University*
