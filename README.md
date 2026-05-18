# 300,000 Streets of Melbourne — School Streets Safety Analysis

A pedestrian and cyclist safety assessment tool for walking routes around secondary schools in Melbourne, grounded in the **Healthy Streets framework** (Lucy Saunders / Transport for London). Built in collaboration between **Regen Melbourne** and **RMIT University**.

---

## Schools assessed

| School | Address | Suburb | Gate coordinates |
|---|---|---|---|
| Reservoir High School | 855 Plenty Rd | Reservoir VIC 3073 | -37.7224, 145.0294 |
| William Ruthven Secondary College | 60 Merrilands Rd | Thornbury VIC 3071 | -37.69654, 145.00299 |
| Preston High School | 2-16 Cooma St | Preston VIC 3072 | -37.7417, 145.0071 |

---

## Scoring system — Healthy Streets framework

Each school gate is scored across **10 Healthy Streets indicators** (0 = worst, 10 = best), as defined by Lucy Saunders and adopted by Transport for London. The overall score is the NaN-safe mean across all 10 indicators.

| Code | Indicator | Data source |
|---|---|---|
| **HS1** | Pedestrians from all walks of life | Field observation — footpath presence, width, continuity, kerb ramps |
| **HS2** | Easy to cross | Field observation — crossing type, distance, visibility, tactile pavers, signals |
| **HS3** | Shade and shelter | OSM — tree count (100m), shelters (200m), green space % (400m) |
| **HS4** | Places to stop and rest | OSM — benches (200m), parks and cafes (400m) |
| **HS5** | Not too noisy | Field observation — traffic volume, speed, heavy vehicles, lanes |
| **HS6** | People choose to walk, cycle, or PT | OSM + field — cycling infrastructure coverage, PT stops (400m) |
| **HS7** | People feel safe | Field observation + Crime Statistics Agency Victoria — lighting, crime rate |
| **HS8** | Things to see and do | OSM — amenities and cafes (400m), parks (400m) |
| **HS9** | People feel relaxed | Field observation — traffic calming, school zone signage, parking |
| **HS10** | Clean air | EPA Victoria AirWatch — PM2.5 annual average (μg/m³) |

Hazard severity is classified as **Major**, **Moderate**, or **Minor** based on rule thresholds applied to HS1, HS2, HS5, and HS9.

### Current scores

| School | HS1 | HS2 | HS3 | HS4 | HS5 | HS6 | HS7 | HS8 | HS9 | HS10 | Overall | Severity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reservoir HS | 4.2 | 5.7 | 5.0 | 6.0 | 5.0 | 6.0 | 8.0 | 6.8 | 5.2 | 9.0 | 6.1 | Minor |
| William Ruthven SC | 9.5 | 6.8 | 3.0 | 3.3 | 10.0 | 4.2 | 7.5 | 4.3 | 8.0 | 10.0 | 6.7 | Minor |
| Preston HS | 9.1 | 0.4 | 5.0 | 8.0 | 7.0 | 7.8 | 8.0 | 10.0 | 7.6 | 9.0 | 7.2 | **Major** |

Preston HS is flagged **Major** due to HS2 = 0.4 — no formal pedestrian crossing adjacent to the school gate.

---

## Project structure

```
300-000-School-Streets/
├── school_data.csv              ← Field observation data (update to refresh outputs)
├── demographics_darebin.csv     ← ABS Census 2021 demographic data
├── requirements.txt             ← Python dependencies
│
├── crash_analysis.py            ← Step 1: Download Victorian ped/cyc crash data
├── spatial_features.py          ← Step 2: OSM features per school (HS3/HS4/HS6/HS8)
├── environmental_features.py    ← Step 3: AQI (HS10) + crime rate (HS7)
├── poc_pipeline.py              ← Step 4: HS scoring, charts, maps, recommendations
├── feature_engineering.py       ← Step 5: School-level ML feature matrix
├── ml_model.py                  ← Step 6: Predict HS scores from open data (Ridge + LOO-CV)
└── pyqgis_pipeline.py           ← GIS: KDE heatmap, buffers, layers, PNG exports (QGIS only)
│
└── outputs/
    ├── crash_data_statewide.csv     ← 7,773 Victorian ped/cyc crashes
    ├── crash_data_darebin.csv       ← Darebin subset within 400m of school gates
    ├── spatial_features.csv         ← 53 OSM features per school at 200m/400m/800m
    ├── environmental_features.csv   ← AQI + crime rate per school
    ├── hs_scores.csv                ← HS1–HS10 scores per school (input for ML)
    ├── ml_school_features.csv       ← School-level feature matrix (input for ml_model.py)
    ├── ml_predictions.csv           ← LOO-CV predicted vs actual HS scores
    ├── recommendations.csv          ← HS-aligned intervention recommendations
    │
    ├── chart1_hs_radar.png          ← 10-indicator radar chart (all schools)
    ├── chart2_hs_scores.png         ← Per-indicator bar comparison
    ├── chart3_hs_breakdown.png      ← Per-school indicator breakdown
    ├── chart4_severity.png          ← Hazard severity counts
    ├── chart5_demographics.png      ← Suburb demographic context
    ├── chart_hs_correlation.png     ← Feature × indicator Pearson correlation heatmap
    ├── chart_hs_prediction.png      ← LOO-CV actual vs predicted HS scores
    ├── chart_feature_importance.png ← Ridge regression coefficients per HS indicator
    ├── heatmap.png                  ← Static crash heatmap
    ├── map_interactive.html         ← Interactive map (open in browser)
    ├── map_heatmap.html             ← Interactive heatmap with crash markers
    │
    ├── kde_heatmap.tif              ← KDE raster (GeoTIFF, EPSG:7855) — pyqgis
    ├── map_Preston_HS.png           ← Per-school static map exports — pyqgis
    ├── map_Reservoir_HS.png
    ├── map_William_Ruthven_SC.png
    ├── networks.gpkg                ← Walk/cycling/road network geometries
    ├── school_streets.gpkg          ← All GIS vector layers
    ├── school_streets.qgz           ← QGIS project file
    └── hs_predictor.pkl             ← Trained Ridge regression model
```

---

## How to run

### Full pipeline

```bash
python crash_analysis.py           # Step 1 — crash data
python spatial_features.py         # Step 2 — OSM features (takes ~5 min)
python environmental_features.py   # Step 3 — AQI + crime
python poc_pipeline.py             # Step 4 — HS scores, charts, maps
python feature_engineering.py      # Step 5 — ML feature matrix
python ml_model.py                 # Step 6 — HS score prediction model
```

### QGIS maps (after Step 1)
```python
# From the QGIS Python Console:
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

### Quick run (charts and maps only)
```bash
python crash_analysis.py && python poc_pipeline.py
```

---

## Step 1 — Download crash data (`crash_analysis.py`)

Downloads Victorian road crash data from [data.vic.gov.au](https://data.vic.gov.au) and filters for pedestrian or cyclist involvement over the last 5 years, assigning each crash to its nearest school gate.

```bash
pip install pandas numpy requests
python crash_analysis.py
```

**Outputs:**

| File | Description |
|---|---|
| `outputs/crash_data_statewide.csv` | 7,773 Victorian ped/cyc crashes with `nearest_school` and `dist_to_gate_m` |
| `outputs/crash_data_darebin.csv` | Darebin subset within 400m of the 3 school gates |

Key columns: `ACCIDENT_NO`, `ACCIDENT_DATE`, `SEVERITY`, `SPEED_ZONE`, `LATITUDE`, `LONGITUDE`, `nearest_school`, `dist_to_gate_m`.

---

## Step 2 — OSM spatial features (`spatial_features.py`)

Queries OpenStreetMap for each school gate at **200m, 400m, and 800m** buffers. Provides the open-data inputs for **HS3** (shade/shelter), **HS4** (rest places), **HS6** (active travel), and **HS8** (things to do).

```bash
pip install geopandas osmnx shapely pyproj networkx
python spatial_features.py
```

> Makes ~6 Overpass API calls per school per radius. Expect **1–2 minutes per school**. Uses **EPSG:7855** (GDA2020 / MGA zone 55) for accurate metric distances.

**Feature groups (53 total):**

| Group | Features |
|---|---|
| Walking network | `walk_edges`, `walk_length_m`, `footpath_length_m`, `footpath_pct` |
| Road network | `road_count`, `arterial_count`, `arterial_pct`, `avg_speed_kmh`, `high_speed_road_count` |
| Crossings | `crossings`, `signals`, `crossing_density` |
| Cycling network | `cycle_length_m`, `protected_cycle_length_m`, `cycle_pct` |
| Amenity (HS3/HS4/HS8) | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m`, `bench_count_200m`, `park_count_400m`, `pt_stops_400m`, `amenity_count_400m`, `cafe_count_400m` |

**Output:** `outputs/spatial_features.csv`

---

## Step 3 — Environmental features (`environmental_features.py`)

Fetches **AQI** (HS10) and **crime rate** (HS7) per school. Tries live APIs first, falls back to hardcoded 2023-24 values if unavailable.

```bash
python environmental_features.py
```

| Data | Source | Fallback |
|---|---|---|
| PM2.5 (μg/m³) | EPA Victoria AirWatch — Alphington station (site 10102) | Suburb-level 2023 annual averages |
| Crime rate (per 100k) | Crime Statistics Agency Victoria XLSX | 2023-24 suburb estimates |

**Output:** `outputs/environmental_features.csv`

---

## Step 4 — HS scoring, charts, and recommendations (`poc_pipeline.py`)

The main analysis engine. Reads `school_data.csv` + `spatial_features.csv` + `environmental_features.csv` and computes all 10 HS indicator scores.

```bash
pip install pandas matplotlib numpy folium rasterio scipy
python poc_pipeline.py
```

**Outputs:**

| File | Description |
|---|---|
| `chart1_hs_radar.png` | 10-indicator radar chart overlaying all 3 schools |
| `chart2_hs_scores.png` | Per-indicator bar comparison across schools |
| `chart3_hs_breakdown.png` | Per-school breakdown of all 10 indicators |
| `chart4_severity.png` | Hazard severity counts |
| `chart5_demographics.png` | Demographic context (income, car ownership, transport mode) |
| `heatmap.png` | Static crash density heatmap |
| `map_interactive.html` | Interactive map — HS scores in popup, crash overlay, network layers |
| `map_heatmap.html` | Interactive KDE heatmap |
| `recommendations.csv` | Rule-based interventions per indicator with priority, cost, and expected score delta |
| `hs_scores.csv` | HS1–HS10 scores per school — used by `feature_engineering.py` |

---

## Step 5 — ML feature matrix (`feature_engineering.py`)

Builds a **school-level** feature matrix (one row per school) combining open data as predictors of HS indicator scores.

```bash
python feature_engineering.py
```

**Features (26 total):**

| Group | Features | HS indicator proxied |
|---|---|---|
| Footpath coverage | `footpath_pct_200m`, `footpath_pct_400m` | HS1 |
| Crossings | `crossings_400m`, `signals_400m`, `crossing_density_400m` | HS2 |
| Green / shade | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m` | HS3 |
| Rest places | `bench_count_200m`, `park_count_400m` | HS4 |
| Traffic stress | `avg_speed_400m`, `arterial_pct_400m`, `high_speed_road_400m`, `road_count_400m` | HS5 / HS9 |
| Active travel | `cycle_pct_400m`, `protected_cycle_length_400m`, `pt_stops_400m` | HS6 |
| Safety / crime | `crime_rate_per_100k` | HS7 |
| Amenity | `amenity_count_400m`, `cafe_count_400m` | HS8 |
| Air quality | `aqi_pm25` | HS10 |
| Crash statistics | `crash_count`, `serious_or_fatal_rate`, `school_hours_pct`, `avg_speed_zone` | context |

**Target:** HS1–HS10 scores (from `hs_scores.csv`)

**Output:** `outputs/ml_school_features.csv` — 3 rows × 38 columns (26 features + 10 targets + 1 overall + school label)

---

## Step 6 — HS score prediction model (`ml_model.py`)

Trains a Ridge regression to predict HS indicator scores from open data — demonstrating that Healthy Streets assessments can be estimated without field surveys.

```bash
pip install scikit-learn seaborn
python ml_model.py
```

**Approach:**
- **Model:** Multi-output Ridge regression (`alpha=1.0`)
- **Evaluation:** Leave-One-Out CV (LOO-CV) — appropriate for 3 schools
- **Purpose:** Which open-data features predict which HS indicators? Which indicators require ground-truthing?

**LOO-CV MAE per indicator:**

| Indicator | MAE | Interpretation |
|---|---|---|
| HS7 — Feel safe | 0.54 | Crime rate is a strong proxy — little survey needed |
| HS10 — Clean air | 0.92 | AQI maps directly — no survey needed |
| HS9 — Feel relaxed | 1.72 | Speed/arterial data works well |
| HS3 — Shade/shelter | 2.17 | OSM tree/shelter data reasonably predictive |
| HS6 — Active travel | 3.08 | Cycling coverage adequate but quality matters |
| HS1 — Pedestrians | 3.27 | Footpath % is a rough proxy; condition needs survey |
| HS5 — Not too noisy | 3.68 | Traffic volume from OSM is incomplete |
| HS4 — Rest places | 4.19 | Bench/park counts unreliable in OSM |
| HS2 — Easy to cross | 4.51 | Crossing presence ≠ crossing quality |
| HS8 — Things to do | 4.72 | OSM amenity count doesn't capture activity quality |

> **Research finding:** HS2 and HS8 have the highest prediction error — these indicators cannot be reliably estimated from open data and require field observation. HS7 and HS10 can be fully automated.

**Outputs:**

| File | Description |
|---|---|
| `chart_hs_correlation.png` | Pearson correlation heatmap — feature × HS indicator |
| `chart_hs_prediction.png` | LOO-CV actual vs predicted per school |
| `chart_feature_importance.png` | Ridge coefficients per HS indicator (top 8 predictors) |
| `ml_predictions.csv` | Actual and predicted HS scores for all 3 schools |
| `hs_predictor.pkl` | Trained model (all 3 schools) — use to score new schools |

---

## Step 7 — GIS layers and map exports (`pyqgis_pipeline.py`)

Requires **QGIS 3.x** installed. Run Step 1 first so crash data exists.

**From the QGIS Python Console:**
```python
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

**Outputs:**

| File | Description |
|---|---|
| `kde_heatmap.tif` | KDE raster (GeoTIFF, EPSG:7855) |
| `school_streets.gpkg` | GeoPackage with all vector layers |
| `school_streets.qgz` | QGIS project — open directly in QGIS |
| `map_<School>.png` | Per-school static map image (1200×900 px) |

---

## Updating the data

1. Edit `school_data.csv` with new field observations.
2. Re-run `crash_analysis.py` to refresh crash data (live from data.vic.gov.au).
3. Re-run `spatial_features.py` to refresh OSM data.
4. Re-run `environmental_features.py` to refresh AQI and crime data.
5. Re-run `poc_pipeline.py` → `feature_engineering.py` → `ml_model.py`.

**To add a new school:** add gate coordinates to `SCHOOL_GATES` in `crash_analysis.py` and `spatial_features.py`, add the suburb mapping to `environmental_features.py`, add field observation rows to `school_data.csv`, and re-run the full pipeline.

---

## Dependencies

| Script | Requirements |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `spatial_features.py` | `geopandas`, `osmnx`, `shapely`, `pyproj`, `networkx` |
| `environmental_features.py` | `pandas`, `numpy`, `requests` |
| `poc_pipeline.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `geopandas`, `rasterio`, `scipy` |
| `feature_engineering.py` | `pandas`, `numpy` |
| `ml_model.py` | `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `seaborn` |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS — not pip-installable) |

```bash
pip install -r requirements.txt
```

---

## Data sources

| Data | Source |
|---|---|
| Victorian road crash records | [data.vic.gov.au — Victoria Road Crash Data](https://www.data.vic.gov.au/data/dataset/victoria-road-crash-data) |
| School gate locations | [data.vic.gov.au — School Locations Time Series](https://www.data.vic.gov.au/data/dataset/school-locations-time-series) |
| OSM spatial data | OpenStreetMap via `osmnx` / Overpass API |
| Air quality (PM2.5) | EPA Victoria AirWatch — Alphington monitoring station (site 10102) |
| Crime rate | Crime Statistics Agency Victoria — suburb-level offences per 100k |
| Demographics | ABS Census 2021 — `demographics_darebin.csv` |

---

## Healthy Streets framework reference

Saunders, L. (2015). *Healthy Streets for London: Prioritising walking, cycling and public transport to create a healthy city.* Transport for London / Lucy Saunders Public Health Consulting.

The 10 Healthy Streets indicators describe the human experience of streets and are designed to be assessed both through observation and open data. A score ≥ 6.0 across all indicators is the target threshold for a school street.

---

*300,000 Streets of Melbourne — Regen Melbourne × RMIT University*
