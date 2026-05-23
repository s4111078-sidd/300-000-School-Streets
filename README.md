# 300,000 Streets of Melbourne — School Streets Safety Analysis

A pedestrian and cyclist safety assessment tool for walking routes around secondary schools in Melbourne, grounded in the **Healthy Streets framework** (Lucy Saunders / Transport for London). Built in collaboration between **Regen Melbourne** and **RMIT University**.

---

## Schools assessed

| School | Address | Suburb | Gate coordinates |
|---|---|---|---|
| Reservoir High School | 855 Plenty Rd | Reservoir VIC 3073 | -37.7224, 145.0294 |
| William Ruthven Secondary College | 60 Merrilands Rd | Reservoir VIC 3073 | -37.69654, 145.00299 |
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

Hazard severity is classified as **Major**, **Moderate**, or **Minor** based on rule thresholds applied to HS1, HS2, HS5, and the count of indicators below 6.0.

### Current scores

| School | HS1 | HS2 | HS3 | HS4 | HS5 | HS6 | HS7 | HS8 | HS9 | HS10 | Overall | Severity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reservoir HS | 4.2 | 5.7 | 5.0 | 6.0 | 5.0 | 6.0 | 8.0 | 6.8 | 5.2 | 9.0 | 6.1 | **Moderate** |
| William Ruthven SC | 9.5 | 6.8 | 3.0 | 3.3 | 10.0 | 4.2 | 7.5 | 4.3 | 8.0 | 10.0 | 6.7 | **Moderate** |
| Preston HS | 9.1 | 0.4 | 5.0 | 8.0 | 7.0 | 7.8 | 8.0 | 10.0 | 7.6 | 9.0 | 7.2 | **Major** |

- **Preston HS** is flagged **Major** due to HS2 = 0.4 — no formal pedestrian crossing adjacent to the school gate.
- **Reservoir HS** is flagged **Moderate** — 5 indicators below 6.0 (HS1, HS2, HS3, HS5, HS9).
- **William Ruthven SC** is flagged **Moderate** — 4 indicators below 6.0 (HS3, HS4, HS6, HS8).

---

## Project structure

```
300-000-School-Streets/
├── school_data.csv              ← Field observation data (update to refresh outputs)
├── demographics_darebin.csv     ← ABS Census 2021 demographic data
├── requirements.txt             ← Python dependencies
│
├── run_all.py                   ← Master runner — runs all 10 steps in order
├── config.py                    ← Shared constants (paths, school gates, HS indicators)
│
│── crash_analysis.py            ← Step 1:  Download Victorian ped/cyc crash data
├── spatial_features.py          ← Step 2:  OSM features per school (HS3/HS4/HS6/HS8)
├── environmental_features.py    ← Step 3:  AQI (HS10) + crime rate (HS7)
├── main.py                      ← Step 4:  HS scoring, charts, maps, recommendations
├── feature_engineering.py       ← Step 5:  School-level ML feature matrix
├── ml_model.py                  ← Step 6:  Predict HS scores from open data (Ridge + LOO-CV)
├── seifa_analysis.py            ← Step 7:  SEIFA 2021 disadvantage analysis
├── equity_analysis.py           ← Step 8:  Equity overlay — SEIFA × HS safety scores
├── crash_trend_analysis.py      ← Step 9:  Crash trends, school-hours breakdown, time-of-day
├── demographics_chart.py        ← Step 10: ABS Census demographics chart
├── scenario_analyzer.py         ← Scenario CLI: what-if intervention analysis
│
├── src/                         ← Modular source code
│   ├── scoring/                 ← HS1–HS10 scoring functions (one file per indicator)
│   │   ├── hs1.py … hs10.py
│   │   └── severity.py
│   ├── data/                    ← Data loaders (CSV, crash downloader, OSM extractor)
│   ├── recommendations/         ← Rule engine + 17 HS-based recommendation rules
│   ├── ml/                      ← ML training, evaluation, prediction modules
│   ├── scenarios/               ← What-if scenario engine
│   │   ├── engine.py            ← Delta-method prediction engine
│   │   └── interventions.py     ← 10 intervention templates with feature deltas
│   ├── visualisation/           ← Charts, heatmap, interactive map, QGIS export
│   └── utils/                   ← Geo helpers, IO utilities
│
└── outputs/
    ├── crash_data_statewide.csv     ← 7,948 Victorian ped/cyc crashes (2021–2025)
    ├── crash_data_darebin.csv       ← Darebin subset within 400m of school gates
    ├── spatial_features.csv         ← OSM features per school at 200m/400m/800m
    ├── environmental_features.csv   ← AQI + crime rate per school
    ├── hs_scores.csv                ← HS1–HS10 scores per school (input for ML)
    ├── ml_school_features.csv       ← School-level feature matrix (input for ml_model.py)
    ├── ml_predictions.csv           ← LOO-CV predicted vs actual HS scores
    ├── recommendations.csv          ← HS-aligned intervention recommendations
    ├── seifa_darebin.csv            ← SEIFA disadvantage index by school catchment
    ├── seifa_darebin_sa1.csv        ← SA1-level SEIFA breakdown
    │
    ├── chart1_safety_scores.png     ← Grouped bar: HS sub-scores per school
    ├── chart2_hazard_severity.png   ← Stacked bar: Major/Moderate/Minor counts
    ├── chart3_score_breakdown.png   ← Per-school HS indicator breakdown panels
    ├── chart4_demographics.png      ← ABS Census 2021: income, car ownership, travel mode
    ├── chart_hs_correlation.png     ← Feature × indicator Pearson correlation heatmap
    ├── chart_hs_prediction.png      ← LOO-CV actual vs predicted HS scores
    ├── chart_feature_importance.png ← Ridge regression coefficients per HS indicator
    ├── chart_equity_seifa.png       ← Equity analysis: SEIFA disadvantage × HS scores
    ├── chart_crash_trends.png       ← Crash trends 2021–2025 + time-of-day distribution
    ├── heatmap.png                  ← Static crash heatmap
    ├── map_interactive.html         ← Interactive map (open in browser)
    ├── map_heatmap.html             ← Interactive heatmap with crash markers
    │
    ├── kde_heatmap.tif              ← KDE raster (GeoTIFF, EPSG:7855)
    ├── networks.gpkg                ← Walk/cycling/road network geometries
    ├── school_streets.gpkg          ← All GIS vector layers
    ├── school_streets.qgz           ← QGIS project file
    ├── hs_predictor.pkl             ← Trained Ridge regression model
    │
    ├── scenario_<school>_<keys>.png      ← Before/after HS chart per scenario run
    └── scenario_ranking_<school>.png     ← Intervention ranking chart (--rank-all)
```

---

## How to run

### One command — run everything
```bash
python run_all.py
```
Skips steps whose outputs already exist. Use `--force` to re-run everything from scratch, or `--from 8` to run only the new analysis steps.

### Step by step
```bash
python crash_analysis.py           # Step 1  — crash data (requires internet)
python spatial_features.py         # Step 2  — OSM features (~3–5 min per school)
python environmental_features.py   # Step 3  — AQI + crime
python main.py                     # Step 4  — HS scores, charts, maps, recommendations
python feature_engineering.py      # Step 5  — ML feature matrix
python ml_model.py                 # Step 6  — HS score prediction model
python seifa_analysis.py           # Step 7  — SEIFA disadvantage analysis
python equity_analysis.py          # Step 8  — Equity overlay (SEIFA × HS scores)
python crash_trend_analysis.py     # Step 9  — Crash trend analysis
python demographics_chart.py       # Step 10 — ABS Census demographics chart
```

### Quick re-run (scores + charts only, after data is downloaded)
```bash
python main.py
```

### Run only the new analysis steps
```bash
python run_all.py --from 8
```

### Run what-if scenario analysis (requires steps 1–6 completed)
```bash
python scenario_analyzer.py --list                                              # list schools + interventions
python scenario_analyzer.py --school "Preston HS" --interventions pedestrian_crossing
python scenario_analyzer.py --school "Reservoir HS" --interventions footpath speed_reduction
python scenario_analyzer.py --school "Preston HS" --rank-all                   # rank all 10 interventions
python scenario_analyzer.py --all-schools --rank-all                           # all schools × all interventions
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
| `outputs/crash_data_statewide.csv` | 7,948 Victorian ped/cyc crashes with `nearest_school` and `dist_to_gate_m` |
| `outputs/crash_data_darebin.csv` | Darebin subset within 400m of the 3 school gates |

Key columns: `ACCIDENT_NO`, `ACCIDENT_DATE`, `ACCIDENT_TIME`, `SEVERITY`, `SPEED_ZONE`, `LATITUDE`, `LONGITUDE`, `nearest_school`, `dist_to_gate_m`.

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

## Step 4 — HS scoring, charts, and recommendations (`main.py`)

The main analysis engine. Reads `school_data.csv` + `spatial_features.csv` + `environmental_features.csv` and computes all 10 HS indicator scores using the modular `src/scoring/` functions.

```bash
pip install pandas matplotlib numpy folium rasterio scipy
python main.py
```

**Outputs:**

| File | Description |
|---|---|
| `chart1_safety_scores.png` | Grouped bar: HS sub-scores (FAS/CSS/EEI/CIS/CYS) per school |
| `chart2_hazard_severity.png` | Stacked bar: Major/Moderate/Minor hazard counts per school |
| `chart3_score_breakdown.png` | Per-school breakdown panels for all 10 HS indicators |
| `heatmap.png` | Static crash density heatmap |
| `map_interactive.html` | Interactive map — HS scores, crash overlay, network layers |
| `map_heatmap.html` | Interactive KDE heatmap |
| `recommendations.csv` | Rule-based interventions per indicator with priority, cost, and timeframe |
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

## Step 7 — SEIFA disadvantage analysis (`seifa_analysis.py`)

Maps ABS SEIFA 2021 Indexes of Relative Socio-Economic Disadvantage onto school catchment areas in Darebin.

```bash
python seifa_analysis.py
```

**Outputs:**

| File | Description |
|---|---|
| `seifa_darebin.csv` | SEIFA score per school catchment |
| `seifa_darebin_sa1.csv` | SA1-level SEIFA breakdown |

| School | IRSD Score | Decile | Disadvantage level |
|---|---|---|---|
| Reservoir HS | 975 | 4 | Moderate-high disadvantage |
| William Ruthven SC | 975 | 4 | Moderate-high disadvantage |
| Preston HS | 1010 | 6 | Moderate disadvantage |

---

## Step 8 — Equity analysis (`equity_analysis.py`)

Joins SEIFA disadvantage data with Healthy Streets scores to reveal whether the most socioeconomically disadvantaged school catchments also have the worst pedestrian safety outcomes.

```bash
python equity_analysis.py
```

**Output:** `outputs/chart_equity_seifa.png` — 3-panel chart:
1. Side-by-side bars: SEIFA decile vs HS overall per school
2. Scatter plot: IRSD decile × HS overall with equity quadrant shading
3. Full 10-indicator heatmap with SEIFA scores annotated

**Key finding:** Correlation r = 0.84 between IRSD decile and HS overall — more disadvantaged catchments have worse safety scores. Reservoir HS (most disadvantaged, Decile 4) also has the lowest HS overall (6.1). This supports prioritised investment under the 300,000 Streets initiative.

---

## Step 9 — Crash trend analysis (`crash_trend_analysis.py`)

Deep-dives into VicRoads crash data (2021–2025) to reveal year-on-year trends, school-hours patterns, and time-of-day distribution.

```bash
python crash_trend_analysis.py
```

**Output:** `outputs/chart_crash_trends.png` — 4-panel chart:
1. Darebin LGA ped/cyc crashes by year (stacked by severity)
2. Our 3 schools: crashes by year
3. School-hours vs off-peak breakdown per school
4. Time-of-day distribution (Darebin LGA)

**Key findings:**
- Darebin LGA crashes increasing: 25 (2021) → 73 (2024)
- Peak crash hour: **17:00** (school pickup window)
- Preston HS has the most crashes (15) within 400m of its gate
- William Ruthven SC: 2 of 2 crashes occurred during school hours

---

## Step 10 — Demographics chart (`demographics_chart.py`)

Generates suburb-level demographic context from ABS Census 2021, showing income, car ownership, and active travel mode share for Reservoir and Preston catchments.

```bash
python demographics_chart.py
```

**Output:** `outputs/chart4_demographics.png`

| Suburb | Median income | No car households | PT to work | School-age children |
|---|---|---|---|---|
| Reservoir | $1,541/week | 11.1% | 7.7% | ~4,854 |
| Preston | $1,844/week | 12.8% | 7.9% | ~3,278 |

---

## Scenario analysis — What-if interventions (`scenario_analyzer.py`)

After running the full pipeline (steps 1–6), use `scenario_analyzer.py` to model the effect of physical street interventions on HS indicator scores and severity classification.

```bash
pip install scikit-learn pandas numpy matplotlib
```

### How it works

The engine uses the **delta method**:

```
scenario_score[i] = actual_score[i] + (model(X_scenario)[i] − model(X_baseline)[i])
```

Actual HS scores are used as the baseline — matching ground truth exactly. The Ridge model contributes the predicted *change* only. Results are clamped to [0, 10] and severity is recomputed.

### CLI examples

```bash
# List all available interventions
python scenario_analyzer.py --list

# Single intervention — saves before/after chart to outputs/
python scenario_analyzer.py --school "Preston HS" --interventions pedestrian_crossing

# Combine multiple interventions
python scenario_analyzer.py --school "Reservoir HS" \
    --interventions pedestrian_crossing speed_reduction footpath

# Rank all 10 interventions by impact for one school
python scenario_analyzer.py --school "Preston HS" --rank-all

# Run across all schools
python scenario_analyzer.py --all-schools --rank-all

# Custom output path / suppress chart
python scenario_analyzer.py --school "Preston HS" --interventions bike_lane \
    --out outputs/my_scenario.png --no-chart
```

### Available interventions (10)

| Key | Label | Cost | Timeframe | Target indicator |
|---|---|---|---|---|
| `pedestrian_crossing` | Install signalised pedestrian crossing | ~$80k–$200k | < 1 year | HS2 |
| `bike_lane` | Install protected bike lane | ~$500k–$1.5M/km | 1–3 years | HS6 |
| `speed_reduction` | Reduce speed limit to 40 km/h school zone | ~$5k–$20k | < 6 months | HS5 |
| `traffic_calming` | Install traffic calming (speed humps / raised crossing) | ~$50k–$150k | < 1 year | HS9 |
| `footpath` | Build / extend continuous footpath | ~$100k–$300k | < 1 year | HS1 |
| `street_trees` | Plant street trees | ~$20k–$60k | < 1 year | HS3 |
| `benches` | Add street benches / seating | ~$5k–$15k | < 6 months | HS4 |
| `pt_stop` | Add / improve public transport stop | ~$50k–$200k | 1–2 years | HS6 |
| `shelter` | Install covered shelter / bus shelter | ~$15k–$40k | < 6 months | HS3 |
| `remove_arterial` | Reroute heavy vehicles / reduce arterial traffic | Council decision | 2–5 years | HS5 |

### Outputs

| File | Description |
|---|---|
| `outputs/scenario_<school>_<keys>.png` | 2-panel chart: before/after HS bars + delta bars |
| `outputs/scenario_ranking_<school>.png` | Intervention ranking chart (--rank-all mode) |

> **Note on rank-all results:** The Ridge model was trained on n=3 schools. Severity changes in rank-all mode may reflect model noise for some interventions. Focus on **ΔHS overall** for comparison across interventions.

---

## Updating the data

1. Edit `school_data.csv` with new field observations.
2. Run `python run_all.py --force` to re-run the full pipeline.

**To add a new school:** add gate coordinates to `SCHOOL_GATES` in `config.py`, add the suburb mapping to `environmental_features.py`, add field observation rows to `school_data.csv`, and re-run `python run_all.py`.

---

## Dependencies

| Script | Requirements |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `spatial_features.py` | `geopandas`, `osmnx`, `shapely`, `pyproj`, `networkx` |
| `environmental_features.py` | `pandas`, `numpy`, `requests` |
| `main.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `geopandas`, `rasterio`, `scipy` |
| `feature_engineering.py` | `pandas`, `numpy` |
| `ml_model.py` | `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `seaborn` |
| `seifa_analysis.py` | `pandas`, `numpy`, `requests` |
| `equity_analysis.py` | `pandas`, `numpy`, `matplotlib` |
| `crash_trend_analysis.py` | `pandas`, `numpy`, `matplotlib` |
| `demographics_chart.py` | `pandas`, `matplotlib` |
| `scenario_analyzer.py` | `scikit-learn`, `pandas`, `numpy`, `matplotlib` |

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
| Socioeconomic disadvantage | ABS SEIFA 2021 — Index of Relative Socio-Economic Disadvantage (IRSD) |

---

## Healthy Streets framework reference

Saunders, L. (2015). *Healthy Streets for London: Prioritising walking, cycling and public transport to create a healthy city.* Transport for London / Lucy Saunders Public Health Consulting.

The 10 Healthy Streets indicators describe the human experience of streets and are designed to be assessed both through observation and open data. A score ≥ 6.0 across all indicators is the target threshold for a school street.

---

*300,000 Streets of Melbourne — Regen Melbourne × RMIT University*
