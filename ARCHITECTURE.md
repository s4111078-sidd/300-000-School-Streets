# System Architecture — 300,000 Streets of Melbourne
## School Streets Safety Analysis

**Project:** 300,000 Streets of Melbourne — School Streets POC
**Partners:** Regen Melbourne × RMIT University
**Scope:** Healthy Streets assessment for secondary school walking routes, City of Darebin, Victoria
**Framework:** Healthy Streets (Lucy Saunders / Transport for London) — 10 indicators, 0–10 per indicator

---

## 1. System Overview

This system combines field observation data, open government crash records, OpenStreetMap network data, EPA air quality readings, and Victorian crime statistics to produce:

- Quantified Healthy Streets scores (HS1–HS10) per school gate
- Auto-generated intervention recommendations ranked by priority, cost, and expected score delta
- Interactive maps and static charts for stakeholder communication
- A trained Ridge regression model that predicts HS indicator scores from open data
- GIS layers for council planning workflows (QGIS-ready)

The system is designed as a reproducible pipeline — all outputs regenerate from source data by re-running the scripts in order.

---

## 2. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
│                                                                              │
│  data.vic.gov.au        OpenStreetMap         EPA Victoria   CSA Victoria   │
│  (crash records +       (walk / bike /        AirWatch       crime rate     │
│   DET school gates)      road networks +      PM2.5 AQI      per suburb     │
│                          amenities/trees)                                    │
└──────┬──────────────────────────┬──────────────────┬──────────────┬─────────┘
       │                          │                  │              │
       ▼                          ▼                  ▼              ▼
┌─────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐
│crash_analysis│    │ spatial_features.py  │    │ environmental_features   │
│    .py       │    │                      │    │         .py              │
│              │    │ OSM queries per gate │    │                          │
│ Downloads +  │    │ 200m / 400m / 800m   │    │ AQI (PM2.5) → HS10      │
│ joins crash  │    │ buffers (53 features)│    │ Crime rate  → HS7        │
│ + school     │    │                      │    │                          │
│   gates      │    │ HS3/HS4/HS6/HS8      │    │ Falls back to hardcoded  │
│              │    │ amenity/tree/shelter │    │ 2023-24 values if APIs   │
│ Nearest-gate │    │ /bench/park/PT/cafe  │    │ are unavailable          │
│ via haversine│    └──────────┬───────────┘    └───────────┬──────────────┘
└──────┬───────┘               │                            │
       │                       │                            │
       ▼                       ▼                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          outputs/                                    │
│  crash_data_statewide.csv  (7,773 crashes)                          │
│  crash_data_darebin.csv    (400m Darebin subset)                    │
│  spatial_features.csv      (53 cols × 3 schools)                   │
│  environmental_features.csv (AQI + crime per school)               │
│  networks.gpkg              (walk/cycling/road geometries)          │
└──────┬───────────────────────────────────┬──────────────────────────┘
       │                                   │
       │       school_data.csv             │
       │       (field observations)        │
       │               │                   │
       │               ▼                   │
       │    ┌──────────────────────┐        │
       │    │   poc_pipeline.py    │        │
       │    │                      │        │
       │    │  HS1–HS10 scoring    │        │
       │    │  Charts (5)          │        │
       │    │  Interactive maps    │        │
       │    │  Recommendations     │        │
       │    │  → hs_scores.csv     │        │
       │    └──────────┬───────────┘        │
       │               │                   │
       └───────────────┼───────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ feature_engineering  │
            │       .py            │
            │                      │
            │ School-level matrix  │
            │ X: 26 open-data      │
            │    features          │
            │ Y: HS1–HS10 scores   │
            │ → ml_school_         │
            │   features.csv       │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │    ml_model.py       │
            │                      │
            │  Ridge regression    │
            │  (multi-output)      │
            │  LOO-CV, n=3 schools │
            │                      │
            │  Predicts HS1–HS10   │
            │  from open data      │
            └──────────────────────┘

                                        ┌──────────────────────────────┐
    crash_data_darebin.csv ─────────►   │   pyqgis_pipeline.py         │
                                        │                              │
                                        │  KDE heatmap, buffers,       │
                                        │  styled layers, per-school   │
                                        │  PNG exports, QGIS project   │
                                        └──────────────────────────────┘
```

---

## 3. Pipeline Components

### `crash_analysis.py`
Downloads Victorian road crash data and assigns each crash to its nearest school gate.

| Item | Detail |
|---|---|
| Source tables | `accident.csv`, `node.csv`, `person.csv` joined on `ACCIDENT_NO` |
| Filter | Pedestrian or cyclist involvement · last 5 years · Victoria only |
| School gates | DET school-locations-time-series API (government / secondary / open) · falls back to 3 hardcoded Darebin gates |
| Proximity method | Vectorised haversine — iterates over gates, broadcasts over crash rows |
| Outputs | `crash_data_statewide.csv` (7,773 crashes) · `crash_data_darebin.csv` (400m Darebin subset) |

### `spatial_features.py`
Queries OpenStreetMap for each assessed school at three buffer radii and computes 53 spatial features. Also exports network geometries for map visualisation.

| Item | Detail |
|---|---|
| School source | `school_data.csv` only — avoids querying all Victorian schools |
| Radii | 200m · 400m · 800m |
| Network types | Walk (`network_type='walk'`) · Drive · Bike |
| CRS | EPSG:7855 (GDA2020 / MGA zone 55) — accurate metric distances for Victoria |
| API | Overpass API via `osmnx` · ~1–2 min per school |
| Feature groups | Walking · Roads · Crossings · Cycling · Amenity (trees, shelters, benches, parks, PT, cafes) |
| Geometry output | `outputs/networks.gpkg` — walk / cycling / arterial road layers |

**HS indicator inputs provided by this script:**

| HS indicator | Columns |
|---|---|
| HS3 — Shade/shelter | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m` |
| HS4 — Rest places | `bench_count_200m`, `park_count_400m` |
| HS6 — Active travel | `cycle_pct_400m`, `protected_cycle_length_400m`, `pt_stops_400m` |
| HS8 — Things to do | `amenity_count_400m`, `cafe_count_400m`, `park_count_400m` |

### `environmental_features.py`
Fetches or estimates air quality and crime data for each school's suburb.

| Item | Detail |
|---|---|
| AQI source | EPA Victoria AirWatch API — Alphington station (site 10102) · falls back to 2023 suburb averages |
| Crime source | Crime Statistics Agency Victoria XLSX download · falls back to 2023-24 suburb estimates |
| AQI fallbacks | Reservoir 8.5 μg/m³ · Thornbury 7.0 · Preston 7.8 |
| Crime fallbacks | Reservoir 820/100k · Thornbury 560 · Preston 710 |
| Output | `outputs/environmental_features.csv` |

**HS indicator inputs provided:**

| HS indicator | Column |
|---|---|
| HS7 — Feel safe | `crime_rate_per_100k` |
| HS10 — Clean air | `aqi_pm25` |

### `poc_pipeline.py`
The main scoring and visualisation engine. Reads field data, spatial features, and environmental data to compute all 10 HS indicator scores, generate charts and maps, and produce recommendations.

| Item | Detail |
|---|---|
| Inputs | `school_data.csv` · `spatial_features.csv` · `environmental_features.csv` · `crash_data_darebin.csv` |
| Scoring | 10 `_hs*()` functions — each maps field + OSM + env columns to a 0–10 score |
| Severity | Major if HS2 < 3 or HS1 < 3 · Moderate if 2+ core indicators < 5 or overall < 5 |
| Recommendations | Gap-based rule engine — one rule block per indicator, each with `Expected_Score_Delta` |
| Maps | Folium interactive map — HS scores in popup, crash overlay, network layer toggle |
| Key outputs | `hs_scores.csv` · `recommendations.csv` · 5 charts · 2 HTML maps |

**HS scoring approach (abbreviated):**

| Indicator | Method | Max pts |
|---|---|---|
| HS1 | Footpath presence (3) + width (2) + continuity (2) + kerb ramps (2) + obstructions (-1) | 10 |
| HS2 | Crossing type (3) + distance (2) + visibility (2) + tactile (1) + signals (2) | 10 |
| HS3 | tree_count_100m (0–4) + shelter_count_200m (0–3) + green_pct_400m (0–3) | 10 |
| HS4 | bench_count_200m (0–4) + shelter (0–2) + park_count_400m (0–2) + cafe (0–2) | 10 |
| HS5 | 10 − traffic_volume (0–3) − speed_penalty (0–3) − heavy_vehicles (0–2) − lanes (0–2) | 10 |
| HS6 | CIS×0.35 + CYS×0.45 + PT_score×0.20 (weighted, NaN-safe) | 10 |
| HS7 | lighting (0–4) + no_safety_hazard (0–2) + crime_rate (0–4) | 10 |
| HS8 | amenity_count (0–4) + park_count (0–3) + cafe_count (0–3) | 10 |
| HS9 | calming (0–3) + school_zone (0–2) + parking (0–2) + lanes (0–2) + FP_condition (0–1) | 10 |
| HS10 | AQI PM2.5 → base score (0–10) − arterial_pct penalty (0–2) | 10 |

### `feature_engineering.py`
Builds the school-level feature matrix for ML training. One row per school.

| Item | Detail |
|---|---|
| Inputs | `spatial_features.csv` · `environmental_features.csv` · `crash_data_statewide.csv` · `hs_scores.csv` |
| Feature matrix X | 26 columns: 20 OSM spatial + 2 environmental + 4 crash aggregates |
| Target matrix Y | 10 columns: HS1–HS10 scores |
| Crash aggregates | `crash_count`, `serious_or_fatal_rate`, `school_hours_pct`, `avg_speed_zone` |
| Output | `ml_school_features.csv` — 3 rows × 38 columns |

### `ml_model.py`
Predicts Healthy Streets indicator scores from open data using Ridge regression and Leave-One-Out cross-validation.

| Item | Detail |
|---|---|
| Input | `ml_school_features.csv` |
| Model | `MultiOutputRegressor(Ridge(alpha=1.0))` wrapped in `StandardScaler` pipeline |
| Evaluation | Leave-One-Out CV (n=3) — train on 2 schools, predict the left-out school |
| Purpose | Identify which HS indicators can be estimated from open data vs which require field surveys |
| Mean LOO-CV MAE | 2.88 across all 10 indicators |
| Best predicted | HS7 (MAE 0.54), HS10 (MAE 0.92) — crime rate and AQI are strong proxies |
| Hardest to predict | HS8 (MAE 4.72), HS2 (MAE 4.51) — quality cannot be inferred from OSM |
| Outputs | `chart_hs_correlation.png` · `chart_hs_prediction.png` · `chart_feature_importance.png` · `ml_predictions.csv` · `hs_predictor.pkl` |

### `pyqgis_pipeline.py`
GIS automation script. Builds a full QGIS project with styled layers and per-school static map exports.

| Item | Detail |
|---|---|
| Requires | QGIS 3.x installed (not pip-installable) |
| Run method | QGIS Python Console (recommended) or standalone with `QGIS_PREFIX` set |
| Layers (bottom → top) | OSM basemap · KDE heatmap · 800m/400m buffers · walk/cycling/road networks · crash points · assessment points · school gates |
| CRS | EPSG:7855 for raster/buffer · EPSG:4326 for vector storage |
| Outputs | `school_streets.gpkg` · `school_streets.qgz` · `map_<School>.png` (1200×900 px per school) |

---

## 4. Healthy Streets Scoring Framework

### 10 Indicators — Data sources

| Code | Indicator | Primary source | Open-data proxy |
|---|---|---|---|
| HS1 | Pedestrians from all walks of life | Field observation | `footpath_pct_*` |
| HS2 | Easy to cross | Field observation | `crossing_density_*`, `signals_*` |
| HS3 | Shade and shelter | OSM | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m` |
| HS4 | Places to stop and rest | OSM | `bench_count_200m`, `park_count_400m`, `cafe_count_400m` |
| HS5 | Not too noisy | Field observation | `avg_speed_400m`, `arterial_pct_400m` |
| HS6 | People choose active travel | Field + OSM | `cycle_pct_400m`, `pt_stops_400m` |
| HS7 | People feel safe | Field + CSA Victoria | `crime_rate_per_100k` |
| HS8 | Things to see and do | OSM | `amenity_count_400m`, `cafe_count_400m` |
| HS9 | People feel relaxed | Field observation | `avg_speed_400m`, `road_count_400m` |
| HS10 | Clean air | EPA Victoria | `aqi_pm25` |

### Current scores

| School | HS1 | HS2 | HS3 | HS4 | HS5 | HS6 | HS7 | HS8 | HS9 | HS10 | Overall | Severity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reservoir HS | 4.2 | 5.7 | 5.0 | 6.0 | 5.0 | 6.0 | 8.0 | 6.8 | 5.2 | 9.0 | 6.1 | Minor |
| William Ruthven SC | 9.5 | 6.8 | 3.0 | 3.3 | 10.0 | 4.2 | 7.5 | 4.3 | 8.0 | 10.0 | 6.7 | Minor |
| Preston HS | 9.1 | 0.4 | 5.0 | 8.0 | 7.0 | 7.8 | 8.0 | 10.0 | 7.6 | 9.0 | 7.2 | **Major** |

---

## 5. ML Model — HS Score Prediction

### Research question
Can Healthy Streets indicator scores be predicted from freely available open data (OSM, AQI, crime statistics, crash records) without requiring field surveys?

### Feature → indicator mapping

| Feature group | Features | Proxies for |
|---|---|---|
| Footpath | `footpath_pct_200m`, `footpath_pct_400m` | HS1 |
| Crossings | `crossings_400m`, `signals_400m`, `crossing_density_400m` | HS2 |
| Green / shade | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m` | HS3 |
| Rest | `bench_count_200m`, `park_count_400m` | HS4 |
| Traffic stress | `avg_speed_400m`, `arterial_pct_400m`, `high_speed_road_400m`, `road_count_400m` | HS5 / HS9 |
| Active travel | `cycle_pct_400m`, `protected_cycle_length_400m`, `pt_stops_400m` | HS6 |
| Crime | `crime_rate_per_100k` | HS7 |
| Amenity | `amenity_count_400m`, `cafe_count_400m` | HS8 |
| Air quality | `aqi_pm25` | HS10 |
| Crash context | `crash_count`, `serious_or_fatal_rate`, `school_hours_pct`, `avg_speed_zone` | general |

### LOO-CV results (n=3)

| Indicator | MAE | Automated? |
|---|---|---|
| HS7 — Feel safe | 0.54 | Yes — crime rate is a reliable proxy |
| HS10 — Clean air | 0.92 | Yes — AQI maps directly |
| HS9 — Feel relaxed | 1.72 | Largely — speed/arterial captures most variance |
| HS3 — Shade/shelter | 2.17 | Partial — OSM tree data is incomplete |
| HS6 — Active travel | 3.08 | Partial — infrastructure coverage adequate, quality not |
| HS1 — Pedestrians | 3.27 | Partial — footpath presence/coverage measurable, condition not |
| HS5 — Not too noisy | 3.68 | Partial — OSM speed data underestimates traffic volume |
| HS4 — Rest places | 4.19 | No — OSM bench/park data poorly maintained |
| HS2 — Easy to cross | 4.51 | No — crossing presence ≠ crossing quality |
| HS8 — Things to do | 4.72 | No — activity quality not captured by POI counts |

**Mean LOO-CV MAE: 2.88**

> **Note:** n=3 schools — results are illustrative of the framework. Adding more schools will improve model generalisability.

---

## 6. Key Design Decisions

| Decision | Rationale |
|---|---|
| Healthy Streets framework (HS1–HS10) over custom scores | Internationally recognised, TfL-adopted framework provides comparability with other cities and a published evidence base for each indicator. |
| School-level ML (not crash-level) | HS scores are per-school not per-crash. The research question is "can open data predict HS scores?" — this requires school-level features and targets, not crash rows. |
| Ridge regression over Random Forest | Only 3 training samples. Ridge regression is regularised, works reliably with small n, and produces interpretable coefficients. Random Forest would overfit immediately. |
| LOO-CV over train/test split | Train/test split is meaningless with n=3. LOO-CV (train on 2, test on 1) is the only valid evaluation strategy and gives 3 independent predictions. |
| EPSG:7855 for all metric operations | GDA2020 / MGA zone 55 is the standard geodetic datum for Victoria, used by VicRoads and DSE. Provides sub-metre accuracy for buffer and distance operations in Melbourne. |
| `spatial_features.py` scoped to `school_data.csv` | Running OSM queries for all ~500 Victorian government secondary schools would take hours. Scoped to assessed schools only; `crash_analysis.py` handles the full DET gate list for proximity assignment. |
| Separate `environmental_features.py` | AQI and crime data have their own API/download cadence. Separating them from the spatial pipeline means they can be refreshed independently without re-querying OSM. |
| Networks saved to `networks.gpkg` in `spatial_features.py` | Geometry export is separated from visualisation to avoid re-running Overpass API calls every time charts or maps are regenerated. |
| Gap-based recommendations with `Expected_Score_Delta` | Provides actionable, auditable interventions that stakeholders can prioritise by cost and expected improvement — more useful for council than a black-box prediction. |

---

## 7. Limitations

| Limitation | Impact |
|---|---|
| n=3 schools | ML results are illustrative; LOO-CV MAE values are high-variance with 3 samples. Adding schools to reach 5–10 is the highest-priority improvement. |
| HS2 and HS8 cannot be automated | Crossing quality and activity/amenity quality require physical observation. Open-data proxies have MAE > 4.0 for these indicators. |
| OSM amenity data is incomplete | Benches, trees, and shelters are sparsely tagged in OSM for Melbourne suburban areas. HS3/HS4 scores may understate reality. |
| Crime rate is suburb-level | The CSA Victoria data is at suburb granularity, not street level. Crimes near a school may differ from the suburb average. |
| AQI uses a single monitoring station | The Alphington station is the closest EPA site, but PM2.5 readings may not reflect localised traffic exposure at individual school gates. |
| DET gate coordinates are school centroids | Actual pedestrian gate may differ by up to ~100m from the school centroid used as the gate location. |
| Field observations are point-in-time | `school_data.csv` reflects conditions at one visit; infrastructure changes are not automatically detected. |

---

## 8. Future Work

| Priority | Enhancement |
|---|---|
| High | Add 2 more schools (scope is 3–5) to strengthen ML generalisability |
| High | Build `scenario_engine.py` — impact matrix per recommendation → before/after HS radar → mode shift projections |
| High | Update `generate_report.py` and `generate_ppt.py` to reflect HS framework, new charts, and ML results |
| Medium | Run `spatial_features.py` for all Victorian government secondary schools — enables statewide HS score prediction |
| Medium | Expand field observations to more locations per school (currently one gate per school) |
| Medium | Add pedestrian count data (morning/afternoon peak volumes) as a crash exposure variable |
| Low | Deploy interactive map as a hosted web app for council access |
| Low | Automate quarterly re-run on new crash data releases from data.vic.gov.au |

---

## 9. Run Order

```bash
# Step 1 — Download crash data and assign nearest school
python crash_analysis.py

# Step 2 — Compute OSM spatial features + save network geometries (~5 min)
python spatial_features.py

# Step 3 — Fetch AQI and crime data
python environmental_features.py

# Step 4 — HS scoring, charts, interactive maps, recommendations
python poc_pipeline.py

# Step 5 — Build school-level ML feature matrix
python feature_engineering.py

# Step 6 — Train HS score prediction model (LOO-CV)
python ml_model.py

# GIS layers and QGIS project (requires QGIS installed)
# Run from QGIS Python Console:
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

---

## 10. Dependencies

| Script | Key packages |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `spatial_features.py` | `geopandas`, `osmnx`, `shapely`, `pyproj`, `networkx`, `fiona` |
| `environmental_features.py` | `pandas`, `numpy`, `requests` |
| `poc_pipeline.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `geopandas`, `fiona`, `rasterio`, `scipy` |
| `feature_engineering.py` | `pandas`, `numpy` |
| `ml_model.py` | `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `seaborn` |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS — not pip-installable) |

```bash
pip install -r requirements.txt
```

---

*300,000 Streets of Melbourne — Regen Melbourne × RMIT University*
