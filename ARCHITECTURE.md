# System Architecture — 300,000 Streets of Melbourne
## School Streets Safety Analysis

**Project:** 300,000 Streets of Melbourne — School Streets POC
**Partners:** Regen Melbourne × RMIT University
**Scope:** Pedestrian and cyclist safety assessment around secondary schools in the City of Darebin, Victoria

---

## 1. System Overview

This system combines field observation data, open government crash records, and OpenStreetMap network data to produce:

- Quantified safety scores per school gate across five dimensions
- Auto-generated intervention recommendations ranked by priority
- Interactive maps and static charts for stakeholder communication
- A trained machine learning model predicting serious or fatal crash risk
- GIS layers for council planning workflows (QGIS-ready)

The system is designed as a reproducible pipeline — all outputs regenerate from source data by re-running the scripts in order.

---

## 2. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│                                                                      │
│  data.vic.gov.au          OpenStreetMap          ABS Census 2021    │
│  (crash records +         (walk / bike /         (demographics_     │
│   DET school gates)        road networks)         darebin.csv)      │
└──────────┬────────────────────────┬──────────────────────┬──────────┘
           │                        │                      │
           ▼                        ▼                      │
┌──────────────────┐   ┌────────────────────────┐         │
│ crash_analysis   │   │  spatial_features.py   │         │
│      .py         │   │                        │         │
│                  │   │  OSM features per gate │         │
│  Downloads and   │   │  at 200m / 400m / 800m │         │
│  joins accident  │   │  buffers (45 features) │         │
│  node + person   │   │                        │         │
│  tables          │   │  Also saves network    │         │
│                  │   │  geometries to         │         │
│  Nearest-school  │   │  networks.gpkg         │         │
│  assignment via  │   └──────────┬─────────────┘         │
│  haversine       │              │                        │
└──────────┬───────┘              │                        │
           │                      │                        │
           ▼                      ▼                        │
┌──────────────────────────────────────────────┐          │
│           outputs/                           │          │
│  crash_data_statewide.csv  (7,773 crashes)   │          │
│  crash_data_darebin.csv    (400m subset)     │          │
│  spatial_features.csv      (45 cols × 3 sch) │          │
│  networks.gpkg             (6 network layers)│          │
└──────────┬──────────────────────┬────────────┘          │
           │                      │                        │
           ▼                      │           ┌────────────┘
┌──────────────────────┐          │           │
│ feature_engineering  │◄─────────┘           │
│       .py            │                      │
│                      │   ┌──────────────────┘
│  Merges crash data   │   │
│  + spatial features  │   │  school_data.csv
│  + CYS scores        │   │  (field observations)
│                      │   │
│  Produces ML-ready   │   │
│  feature matrix      │   │
└──────────┬───────────┘   │
           │               ▼
           │    ┌─────────────────────┐
           │    │    poc_pipeline.py  │
           │    │                    │
           │    │  Scoring engine    │
           │    │  (FAS/CSS/EEI/     │
           │    │   CIS/CYS)         │
           │    │                    │
           │    │  Charts, maps,     │
           │    │  recommendations   │
           │    │  + network layers  │
           │    └──────────┬─────────┘
           │               │
           ▼               ▼
┌──────────────────┐  ┌──────────────────────────────┐
│   ml_model.py   │  │     pyqgis_pipeline.py        │
│                  │  │                              │
│  Random Forest   │  │  GIS automation:             │
│  classifier      │  │  KDE heatmap, buffers,       │
│                  │  │  network layers, per-school  │
│  ROC-AUC: 0.626  │  │  PNG exports, QGIS project  │
└──────────┬───────┘  └──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│                  outputs/                            │
│  ml_features.csv              crash_risk_model.pkl  │
│  chart_feature_importance.png                       │
│  chart_confusion_matrix.png                         │
│  chart1_safety_scores.png     recommendations.csv   │
│  chart2_hazard_severity.png   map_interactive.html  │
│  chart3_score_breakdown.png   map_heatmap.html      │
│  chart4_demographics.png      school_streets.gpkg   │
│  map_<School>.png (×3)        school_streets.qgz    │
└─────────────────────────────────────────────────────┘
```

---

## 3. Pipeline Components

### `crash_analysis.py`
Downloads Victorian road crash data from [data.vic.gov.au](https://discover.data.vic.gov.au) and assigns each crash to its nearest school gate.

| Item | Detail |
|---|---|
| Source tables | `accident.csv`, `node.csv`, `person.csv` joined on `ACCIDENT_NO` |
| Filter | Pedestrian or cyclist involvement · last 5 years · Victoria only |
| School gates | DET school-locations-time-series API (government / secondary / open) · falls back to 3 hardcoded Darebin gates |
| Proximity method | Vectorised haversine — iterates over gates, not crash rows |
| Outputs | `crash_data_statewide.csv` (7,773 crashes) · `crash_data_darebin.csv` (400m Darebin subset) |

### `spatial_features.py`
Fetches OpenStreetMap network data for each assessed school and computes 45 spatial features per school across three buffer radii. Also exports network geometries for map visualisation.

| Item | Detail |
|---|---|
| School source | `school_data.csv` only — prevents fetching all Victorian schools |
| Radii | 200m · 400m · 800m |
| Network types | Walk (`network_type='walk'`) · Drive · Bike |
| CRS | EPSG:7855 (GDA2020 / MGA zone 55) — accurate metric distances for Victoria |
| API | Overpass API via `osmnx` · ~1–2 min per school |
| Feature groups | Walking · Roads · Crossings · Traffic signals · Cycling · Derived (crossing density) |
| Geometry output | `outputs/networks.gpkg` — 6 layers (walk / cycling / arterial roads × 400m / 800m) |

**Features computed (15 per radius × 3 radii = 45 total):**

| Group | Features |
|---|---|
| Walking | `walk_edges`, `walk_length_m`, `footpath_length_m`, `footpath_pct` |
| Roads | `road_count`, `arterial_count`, `arterial_pct`, `avg_speed_kmh`, `high_speed_road_count` |
| Crossings | `crossings`, `signals`, `crossing_density` |
| Cycling | `cycle_length_m`, `protected_cycle_length_m`, `cycle_pct` |

### `feature_engineering.py`
Reads crash data and builds the ML-ready feature matrix.

| Item | Detail |
|---|---|
| Input | `crash_data_statewide.csv` + `spatial_features.csv` (optional) |
| Base features | 13 crash-record features across time, speed, road, lighting, proximity |
| Spatial merge | Left-join on `nearest_school` — spatial features added for 3 assessed schools |
| CYS loading | 3-tier: manual `school_data.csv` column → OSM-computed from spatial features → NaN |
| Target | `serious_or_fatal` — 1 if SEVERITY ∈ {1 fatal, 2 serious injury} |
| Output | `ml_features.csv` — 7,773 rows · 62 columns · 43.1% positive rate |

### `poc_pipeline.py`
The main visualisation and scoring engine. Reads `school_data.csv` and produces all charts, maps, and recommendations.

| Item | Detail |
|---|---|
| Scoring | Computes FAS / CSS / EEI / CIS / CYS from sub-indicator rules |
| CYS loading | Manual column in CSV → OSM spatial features → NaN |
| Recommendations | 15-rule engine generating ranked interventions per location |
| Maps | Interactive folium map with school markers, crash data, network layers, and layer toggle |
| Network layers | Loaded from `networks.gpkg` — walk (green) / cycling (blue, thick = protected) / arterials (red) |
| Charts | 4 charts: safety scores · hazard severity · score breakdown · demographics |

### `ml_model.py`
Trains a binary classifier to predict serious or fatal crash risk near school gates.

| Item | Detail |
|---|---|
| Model | Random Forest (300 trees · max depth 10 · class_weight balanced) |
| Split | 80/20 stratified train/test · 5-fold cross-validation |
| Imputation | `SimpleImputer(strategy='median')` inside sklearn Pipeline |
| Performance | ROC-AUC 0.626 · CV AUC 0.622 ± 0.011 · Accuracy 60% |
| Outputs | `crash_risk_model.pkl` · `chart_feature_importance.png` · `chart_confusion_matrix.png` |

### `pyqgis_pipeline.py`
GIS automation script. Builds a full QGIS project with all layers styled and per-school map exports.

| Item | Detail |
|---|---|
| Requires | QGIS 3.x installed (not pip-installable) |
| Run method | QGIS Python Console (recommended) or standalone with `QGIS_PREFIX` set |
| Layers (bottom → top) | OSM basemap · KDE heatmap · 800m/400m buffers · walk/cycling/road networks · crash points · assessment points · school gates |
| CRS | EPSG:7855 for raster/buffer operations · EPSG:4326 for vector storage |
| Outputs | `school_streets.gpkg` · `school_streets.qgz` · `map_<School>.png` (1200×900 px per school) |

---

## 4. Scoring Framework

Each assessed location is scored across five dimensions (0 = worst, 10 = best):

| Score | Full name | Source | Method |
|---|---|---|---|
| **FAS** | Footpath Accessibility Score | Manual field observation | Rule-based from footpath presence, width, continuity, condition |
| **CSS** | Crossing Safety Score | Manual field observation | Rule-based from crossing type, distance, visibility, signals |
| **EEI** | Environmental Exposure Indicator | Manual field observation | Rule-based from speed, traffic volume, lanes, lighting, school zone |
| **CIS** | Cycling Infrastructure Score | Manual field observation | LTS classification of frontage road infrastructure type |
| **CYS** | Cycling Safety Score | Auto-computed from OSM | 5-component rubric (see below) |

**Overall score** = NaN-safe mean of all five dimensions. Threshold: **≥ 6.0 = good**.

**Severity classification:** Major / Moderate / Minor — derived from rule-based thresholds on FAS, CSS, EEI, speed, crossing distance, and school zone status.

### CYS Rubric (400m buffer, 0–10 pts)

| Component | OSM column | Points |
|---|---|---|
| Cycling network coverage | `cycle_pct_400m` | ≥40%: 4 · ≥25%: 3 · ≥15%: 2 · ≥5%: 1 |
| Protected infrastructure length | `protected_cycle_length_400m` | ≥300m: 3 · ≥100m: 2 · >0m: 1 |
| Traffic signals | `signals_400m` | ≥3 signals: +1 |
| Crossing density | `crossing_density_400m` | ≥1/km: +1 |
| Speed environment | `avg_speed_400m` | ≤40 km/h: +1 |

**Current CYS scores (OSM-computed):**

| School | CYS | Key driver |
|---|---|---|
| Reservoir HS | 8.0 / 10 | 43% cycling coverage + 202m of protected lanes |
| Preston HS | 6.0 / 10 | 45% cycling coverage, good signals, no protected lanes |
| William Ruthven SC | 5.0 / 10 | 39% cycling coverage, zero protected infrastructure, high avg speed (70 km/h) |

### CIS Framework

Based on Level of Traffic Stress (Mekuria, Furth & Nixon 2012) and VicRoads TEM Vol. 3 Part 218:

| Infrastructure | LTS | CIS |
|---|---|---|
| Separated bike lane | LTS 1 | 9.0 |
| Shared path / greenway | LTS 1 | 8.0 |
| Painted bike lane | LTS 2–3 | 4.5 |
| Advisory lane / shared road | LTS 3–4 | 2.0 |
| No cycling infrastructure | LTS 4 | 1.0 |

---

## 5. ML Model

### Features (59 after removing all-NaN columns)

| Group | Features | Count |
|---|---|---|
| Time | `hour`, `day_of_week`, `month`, `is_weekend`, `is_school_hours` | 5 |
| Speed / road | `speed_zone_num`, `is_high_speed_zone`, `road_geometry_code`, `no_of_vehicles` | 4 |
| Lighting | `light_condition_code`, `is_dark` | 2 |
| Proximity | `dist_to_gate_m`, `near_school_400m` | 2 |
| CYS | `cys_score` | 1 |
| OSM spatial | Walking / road / crossing / cycling features at 200m · 400m · 800m | 45 |

### Results

| Metric | Value |
|---|---|
| ROC-AUC (test) | 0.626 |
| 5-fold CV AUC | 0.622 ± 0.011 |
| Accuracy | 60% |
| Recall — Serious/Fatal | 0.57 |
| Precision — Serious/Fatal | 0.53 |

### Top Feature Importances

| Rank | Feature | Category | Importance |
|---|---|---|---|
| 1 | `dist_to_gate_m` | Proximity | ~0.22 |
| 2 | `speed_zone_num` | Road / speed | ~0.15 |
| 3 | `hour` | Time | ~0.13 |
| 4 | `month` | Time | ~0.11 |
| 5 | `day_of_week` | Time | ~0.08 |
| 6 | `light_condition_code` | Other | ~0.07 |
| 7 | `road_geometry_code` | Road / speed | ~0.06 |

### Interpretation

- **Distance from gate dominates** — crashes far from school gates have a different severity profile to those immediately adjacent, suggesting the gate proximity gradient matters more than a binary 400m cutoff
- **Speed zone is the strongest infrastructure predictor** — directly validates the project's focus on speed environments
- **Temporal features are highly predictive** — hour, month, and day collectively account for ~30% of model decision-making, supporting the case for time-variable enforcement
- **OSM spatial features have low individual importance** — due to only 3 schools having spatial data; expanding coverage would significantly improve model performance
- **Stable CV performance** (±0.011) confirms the model is not overfitting

---

## 6. Key Design Decisions

| Decision | Rationale |
|---|---|
| EPSG:7855 for all metric operations | GDA2020 / MGA zone 55 is the standard geodetic datum for Victoria, used by VicRoads and DSE. Provides sub-metre accuracy for buffer and distance operations in Melbourne. |
| Vectorised haversine over spatial join | Iterating over ~500 school gates and broadcasting over 7,773 crash rows is faster and avoids the overhead of building spatial indices on un-projected data. |
| `spatial_features.py` reads from `school_data.csv` only | Running OSM queries for all ~500 Victorian government secondary schools would take hours. The script is scoped to assessed schools only; `crash_analysis.py` handles the full DET gate list for proximity assignment. |
| `SimpleImputer(strategy='median')` inside Pipeline | Median imputation prevents data leakage — the imputer is fitted only on training data and applied to the test set. Most NaN values come from OSM features only present for 3 schools; treating them as missing-at-random is appropriate for a POC. |
| `class_weight='balanced'` in Random Forest | The 43% positive rate is mild imbalance but `balanced` weighting prevents the model from ignoring the minority (serious/fatal) class, improving recall on the safety-critical outcome. |
| Networks saved to `networks.gpkg` in `spatial_features.py` | Separating geometry export from visualisation avoids re-running Overpass API calls every time charts or maps are regenerated. Both `poc_pipeline.py` and `pyqgis_pipeline.py` consume the same file. |
| 15-rule recommendation engine | Rule-based recommendations are fully explainable and auditable — important for council stakeholders. ML predictions complement but do not replace structured engineering judgement. |

---

## 7. Limitations

| Limitation | Impact |
|---|---|
| OSM spatial features cover 3 schools only | 59 features are NaN for ~90% of crash rows; imputed with median, which reduces model signal |
| CYS has only 3 unique values in crash data | Low variance makes it a weak ML predictor; the raw OSM component columns are more informative |
| DET school gate API returns coordinates only — no exact gate location | Gate is approximated as school centroid; actual pedestrian gate may differ by up to ~100m |
| ROC-AUC of 0.626 | Modest predictive power; crash severity is influenced by many unobserved factors (vehicle type, driver state, exact road condition) not present in the dataset |
| `pyqgis_pipeline.py` requires QGIS 3.x | Cannot be pip-installed; must be run inside QGIS or with a configured QGIS Python path |
| Field observations are point-in-time | `school_data.csv` reflects conditions at one visit; infrastructure changes are not automatically detected |

---

## 8. Future Work

| Priority | Enhancement |
|---|---|
| High | Run `spatial_features.py` for all Victorian government secondary schools — would populate OSM features for all 7,773 crashes and materially improve ML model AUC |
| High | Add XGBoost classifier (`brew install libomp`) for model comparison and ensemble |
| Medium | Expand field observations to more schools and more observation points per school |
| Medium | Add pedestrian count data (school morning/afternoon peaks) as a crash exposure variable |
| Medium | Replace binary `serious_or_fatal` target with multi-class severity (Fatal / Serious / Other) |
| Low | Automate re-run on new crash data releases (quarterly, data.vic.gov.au) |
| Low | Deploy interactive map as a hosted web application for council access |

---

## 9. Run Order

```bash
# Step 1 — Download crash data and assign nearest school
python crash_analysis.py

# Step 1b — Compute OSM spatial features + save network geometries
python spatial_features.py

# Step 1c — Build ML feature matrix
python feature_engineering.py

# Step 2 — Generate charts, maps, and recommendations
python poc_pipeline.py

# Step 3 — GIS layers and QGIS project (requires QGIS installed)
# Run from QGIS Python Console:
exec(open('/full/path/to/pyqgis_pipeline.py').read())

# Step 4 — Train crash risk classifier
python ml_model.py
```

**Quick run (charts and maps only — no OSM or ML):**
```bash
python crash_analysis.py
python poc_pipeline.py
```

---

## 10. Dependencies

| Script | Key packages |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `spatial_features.py` | `geopandas`, `osmnx`, `shapely`, `pyproj`, `networkx`, `fiona` |
| `feature_engineering.py` | `pandas`, `numpy` |
| `poc_pipeline.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `geopandas`, `fiona`, `rasterio`, `scipy` |
| `ml_model.py` | `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `seaborn` |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS — not pip-installable) |

```bash
pip install -r requirements.txt
```

---

*300,000 Streets of Melbourne — Regen Melbourne × RMIT University*
