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
- Auto-generated intervention recommendations ranked by priority, cost, and HS indicator
- Interactive maps and static charts for stakeholder communication
- A trained Ridge regression model that predicts HS indicator scores from open data
- SEIFA socio-economic disadvantage analysis for school catchments
- Equity analysis linking disadvantage to safety outcomes
- Crash trend analysis (2021–2025) with school-hours breakdown
- ABS Census 2021 demographic context per catchment
- GIS layers for council planning workflows (QGIS-ready)

The system is designed as a reproducible pipeline — all outputs regenerate from source data by re-running `python run_all.py`.

---

## 2. Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                     │
│                                                                               │
│  data.vic.gov.au        OpenStreetMap         EPA Victoria   CSA Victoria    │
│  (crash records +       (walk / bike /        AirWatch       crime rate      │
│   DET school gates)      road networks +      PM2.5 AQI      per suburb      │
│                          amenities/trees)                                     │
│                                                  ABS SEIFA 2021              │
│                                                  ABS Census 2021             │
└──────┬──────────────────────────┬──────────────────┬──────────────┬──────────┘
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
┌──────────────────────────────────────────────────────────────────┐
│                          outputs/                                  │
│  crash_data_statewide.csv  (7,948 crashes, 2021–2025)            │
│  crash_data_darebin.csv    (400m Darebin subset)                 │
│  spatial_features.csv      (53 cols × 3 schools)                │
│  environmental_features.csv (AQI + crime per school)            │
│  networks.gpkg              (walk/cycling/road geometries)       │
└──────┬────────────────────────────────┬─────────────────────────┘
       │                                │
       │       school_data.csv          │
       │       (field observations)     │
       │               │                │
       │               ▼                │
       │    ┌──────────────────────────────────────────┐
       │    │   main.py  +  src/                        │
       │    │                                           │
       │    │  src/scoring/hs1.py … hs10.py             │
       │    │  src/scoring/severity.py                  │
       │    │  src/recommendations/engine.py            │
       │    │  src/recommendations/rules.py  (17 rules) │
       │    │  src/visualisation/                       │
       │    │                                           │
       │    │  → hs_scores.csv                          │
       │    │  → recommendations.csv                    │
       │    │  → chart1_safety_scores.png               │
       │    │  → chart2_hazard_severity.png             │
       │    │  → chart3_score_breakdown.png             │
       │    │  → map_interactive.html                   │
       │    │  → map_heatmap.html                       │
       │    └──────────┬────────────────────────────────┘
       │               │
       └───────────────┼───────────────────────────────────────┐
                       │                                       │
           ┌───────────┴──────────┐              ┌────────────┴───────────┐
           │                      │              │                        │
           ▼                      ▼              ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│feature_engineering│  │ seifa_analysis   │  │ equity_analysis  │  │crash_trend       │
│      .py         │  │     .py          │  │     .py          │  │_analysis.py      │
│                  │  │                  │  │                  │  │                  │
│ X: 26 open-data  │  │ ABS SEIFA 2021   │  │ Joins SEIFA +    │  │ Year trends      │
│    features      │  │ Darebin school   │  │ hs_scores.csv    │  │ School-hours vs  │
│ Y: HS1–HS10      │  │ catchment IRSD   │  │ 3-panel equity   │  │ off-peak         │
│    scores        │  │ disadvantage     │  │ chart            │  │ Time-of-day dist │
└────────┬─────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
         │
         ▼
┌──────────────────────┐        ┌──────────────────────┐
│    ml_model.py       │        │  demographics_chart  │
│                      │        │       .py            │
│  Ridge regression    │        │                      │
│  (multi-output)      │        │ ABS Census 2021      │
│  LOO-CV, n=3 schools │        │ income / car / mode  │
│                      │        │ share per suburb     │
│  → hs_predictor.pkl  │        └──────────────────────┘
│  → ML charts         │
└──────────────────────┘
```

---

## 3. Modular Source Structure (`src/`)

```
src/
├── scoring/          ← One module per HS indicator
│   ├── hs1.py        ← Pedestrians from all walks of life
│   ├── hs2.py        ← Easy to cross
│   ├── hs3.py        ← Shade and shelter
│   ├── hs4.py        ← Places to stop and rest
│   ├── hs5.py        ← Not too noisy
│   ├── hs6.py        ← People choose to walk / cycle / PT
│   ├── hs7.py        ← People feel safe
│   ├── hs8.py        ← Things to see and do
│   ├── hs9.py        ← People feel relaxed
│   ├── hs10.py       ← Clean air
│   └── severity.py   ← Major / Moderate / Minor classification
│
├── data/
│   ├── loader.py             ← load_school_data() — CSV clean + rename
│   ├── crash_downloader.py   ← VicRoads crash API helpers
│   ├── osm_extractor.py      ← OSM / Overpass API helpers
│   ├── epa_fetcher.py        ← EPA AirWatch PM2.5 fetcher
│   └── crime_fetcher.py      ← Crime Statistics Agency Victoria fetcher
│
├── recommendations/
│   ├── engine.py    ← run_recommendations() — applies all rules to df
│   └── rules.py     ← 17 HS-mapped rules (rule_01 … rule_17)
│
├── ml/
│   ├── train.py     ← fit Ridge regression pipeline
│   ├── evaluate.py  ← LOO-CV, MAE per indicator
│   └── predict.py   ← score new schools from pkl model (stub — not yet implemented)
│
├── visualisation/
│   ├── charts.py          ← static PNG charts (chart1–chart4)
│   ├── heatmap.py         ← KDE heatmap (folium + scipy)
│   ├── interactive_map.py ← folium hazard + crash + network map
│   └── qgis_export.py     ← QGIS layer styling helpers
│
└── utils/
    ├── geo.py   ← haversine, buffer, CRS helpers
    └── io.py    ← CSV / GeoPackage helpers
```

All shared constants (school gates, HS indicator list, column rename map) live in `config.py` at the project root.

---

## 4. Pipeline Components

### `run_all.py` — Master runner
Runs all 10 steps in order. Skips steps whose outputs already exist.

```bash
python run_all.py              # run all, skip existing
python run_all.py --force      # force re-run everything
python run_all.py --from 4     # start from step 4
python run_all.py --from 8     # run only the analysis steps (8–10)
```

### `crash_analysis.py` — Step 1
Downloads Victorian road crash data and assigns each crash to its nearest school gate.

| Item | Detail |
|---|---|
| Source tables | `accident.csv`, `node.csv`, `person.csv` joined on `ACCIDENT_NO` |
| Filter | Pedestrian or cyclist involvement · last 5 years · Victoria only |
| School gates | DET school-locations-time-series API · falls back to 3 hardcoded Darebin gates |
| Proximity method | Vectorised haversine |
| Outputs | `crash_data_statewide.csv` (7,948 crashes) · `crash_data_darebin.csv` (400m Darebin subset) |

### `spatial_features.py` — Step 2
Queries OpenStreetMap for each assessed school at three buffer radii and computes 53 spatial features.

| Item | Detail |
|---|---|
| Radii | 200m · 400m · 800m |
| CRS | EPSG:7855 (GDA2020 / MGA zone 55) |
| Feature groups | Walking · Roads · Crossings · Cycling · Amenity (trees, shelters, benches, parks, PT, cafes) |
| Output | `outputs/spatial_features.csv` · `outputs/networks.gpkg` |

### `environmental_features.py` — Step 3
Fetches AQI (HS10) and crime rate (HS7) per school suburb.

| Data | Source | Fallback |
|---|---|---|
| PM2.5 (μg/m³) | EPA Victoria AirWatch — Alphington station | Suburb 2023 averages |
| Crime rate (per 100k) | Crime Statistics Agency Victoria XLSX | 2023-24 suburb estimates |

### `main.py` — Step 4 (core pipeline)
Orchestrates HS scoring, chart generation, recommendations, and map output.

| Item | Detail |
|---|---|
| Inputs | `school_data.csv` + `spatial_features.csv` + `environmental_features.csv` |
| Scoring | Calls `src/scoring/hs1.py … hs10.py` — one function per indicator |
| Severity | `src/scoring/severity.py` — Major / Moderate / Minor |
| Recommendations | `src/recommendations/engine.py` + `rules.py` (17 rules, each tagged to an HS indicator) |
| Key outputs | `hs_scores.csv` · `recommendations.csv` · 3 charts · 2 HTML maps |

**HS scoring approach:**

| Indicator | Method | Max pts |
|---|---|---|
| HS1 | Footpath presence + width + continuity + kerb ramps + obstructions | 10 |
| HS2 | Crossing type + distance + visibility + tactile + signals | 10 |
| HS3 | tree_count_100m + shelter_count_200m + green_pct_400m | 10 |
| HS4 | bench_count_200m + shelter + park_count_400m + cafe | 10 |
| HS5 | 10 − traffic_volume − speed_penalty − heavy_vehicles − lanes | 10 |
| HS6 | CIS×0.35 + CYS×0.45 + PT_score×0.20 (NaN-safe weighted avg) | 10 |
| HS7 | lighting + no_safety_hazard + crime_rate | 10 |
| HS8 | amenity_count + park_count + cafe_count | 10 |
| HS9 | calming + school_zone + parking + lanes + FP_condition | 10 |
| HS10 | AQI PM2.5 → base score − arterial_pct penalty | 10 |

**Severity classification:**

| Level | Threshold |
|---|---|
| **Major** | HS2 < 3.0 OR HS1 < 3.0 OR HS5 < 2.0 |
| **Moderate** | 2+ indicators below 6.0 OR HS_overall < 5.0 |
| **Minor** | All other cases |

### `feature_engineering.py` — Step 5

| Item | Detail |
|---|---|
| Inputs | `spatial_features.csv` + `environmental_features.csv` + `crash_data_statewide.csv` + `hs_scores.csv` |
| Feature matrix X | 26 columns: 20 OSM spatial + 2 environmental + 4 crash aggregates |
| Target matrix Y | 10 columns: HS1–HS10 scores |
| Output | `ml_school_features.csv` — 3 rows × 38 columns |

### `ml_model.py` — Step 6

| Item | Detail |
|---|---|
| Model | `MultiOutputRegressor(Ridge(alpha=1.0))` wrapped in `StandardScaler` |
| Evaluation | Leave-One-Out CV (n=3) |
| Mean LOO-CV MAE | 2.88 |
| Best predicted | HS7 (MAE 0.54) · HS10 (MAE 0.92) |
| Hardest to predict | HS8 (MAE 4.72) · HS2 (MAE 4.51) |
| Scenario readiness | Change a feature value (e.g. `cycle_pct_400m`) and call `pipe.predict()` — no retraining needed |
| Outputs | `ml_predictions.csv` · `hs_predictor.pkl` · 3 ML charts |

### `seifa_analysis.py` — Step 7
Maps ABS SEIFA 2021 disadvantage scores onto Darebin school catchment areas.

| Output | Description |
|---|---|
| `seifa_darebin.csv` | Weighted IRSD score and decile per school catchment |
| `seifa_darebin_sa1.csv` | SA1-level SEIFA breakdown |

### `equity_analysis.py` — Step 8
Joins `seifa_darebin.csv` with `hs_scores.csv` and visualises the relationship between socioeconomic disadvantage and pedestrian safety.

| Output | Description |
|---|---|
| `chart_equity_seifa.png` | 3-panel: decile vs HS bars · scatter with equity quadrant · 10-indicator heatmap |

**Key finding:** Pearson r = 0.84 between IRSD decile and HS overall — more disadvantaged catchments have worse safety scores (Reservoir HS: Decile 4, HS 6.1 vs Preston HS: Decile 6, HS 7.2).

### `crash_trend_analysis.py` — Step 9
Deep-dives into the statewide crash dataset, filtering for Darebin LGA and the 3 assessed schools.

| Output | Description |
|---|---|
| `chart_crash_trends.png` | 4-panel: LGA year trend · per-school year trend · school-hours vs off-peak · time-of-day |

**Key findings:**
- Darebin LGA ped/cyc crashes rose from 25 (2021) to 73 (2024)
- Peak crash hour: 17:00 (school pickup)
- Preston HS has 15 crashes within 400m — the highest of the 3 schools

### `demographics_chart.py` — Step 10
Calls `src/visualisation/charts.plot_demographics()` using `demographics_darebin.csv` (ABS Census 2021).

| Output | Description |
|---|---|
| `chart4_demographics.png` | 4-panel bar: median income · no-car households · PT mode share · full-time work rate |

---

## 5. Healthy Streets Scoring Framework

| Code | Indicator | Primary source | Open-data proxy |
|---|---|---|---|
| HS1 | Pedestrians from all walks of life | Field observation | `footpath_pct_*` |
| HS2 | Easy to cross | Field observation | `crossing_density_*`, `signals_*` |
| HS3 | Shade and shelter | OSM | `tree_count_100m`, `shelter_count_200m`, `green_pct_400m` |
| HS4 | Places to stop and rest | OSM | `bench_count_200m`, `park_count_400m` |
| HS5 | Not too noisy | Field observation | `avg_speed_400m`, `arterial_pct_400m` |
| HS6 | People choose active travel | Field + OSM | `cycle_pct_400m`, `pt_stops_400m` |
| HS7 | People feel safe | Field + CSA Victoria | `crime_rate_per_100k` |
| HS8 | Things to see and do | OSM | `amenity_count_400m`, `cafe_count_400m` |
| HS9 | People feel relaxed | Field observation | `avg_speed_400m`, `road_count_400m` |
| HS10 | Clean air | EPA Victoria | `aqi_pm25` |

### Current scores

| School | HS1 | HS2 | HS3 | HS4 | HS5 | HS6 | HS7 | HS8 | HS9 | HS10 | Overall | Severity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Reservoir HS | 4.2 | 5.7 | 5.0 | 6.0 | 5.0 | 6.0 | 8.0 | 6.8 | 5.2 | 9.0 | 6.1 | **Moderate** |
| William Ruthven SC | 9.5 | 6.8 | 3.0 | 3.3 | 10.0 | 4.2 | 7.5 | 4.3 | 8.0 | 10.0 | 6.7 | **Moderate** |
| Preston HS | 9.1 | 0.4 | 5.0 | 8.0 | 7.0 | 7.8 | 8.0 | 10.0 | 7.6 | 9.0 | 7.2 | **Major** |

---

## 6. ML Results — HS Score Prediction

| Indicator | MAE | Automated? |
|---|---|---|
| HS7 — Feel safe | 0.54 | Yes — crime rate is a reliable proxy |
| HS10 — Clean air | 0.92 | Yes — AQI maps directly |
| HS9 — Feel relaxed | 1.72 | Largely — speed/arterial captures most variance |
| HS3 — Shade/shelter | 2.17 | Partial — OSM tree data is incomplete |
| HS6 — Active travel | 3.08 | Partial — coverage adequate, quality not |
| HS1 — Pedestrians | 3.27 | Partial — footpath presence measurable, condition not |
| HS5 — Not too noisy | 3.68 | Partial — OSM speed data underestimates volume |
| HS4 — Rest places | 4.19 | No — OSM bench/park data poorly maintained |
| HS2 — Easy to cross | 4.51 | No — crossing presence ≠ crossing quality |
| HS8 — Things to do | 4.72 | No — activity quality not captured by POI counts |

**Mean LOO-CV MAE: 2.88** (n=3 — results are illustrative; generalisability improves with more schools)

---

## 7. Equity Analysis Results

| School | IRSD Decile | HS Overall | Disadvantage Level |
|---|---|---|---|
| Reservoir HS | 4 (most disadvantaged) | 6.1 (lowest) | Moderate-high |
| William Ruthven SC | 4 | 6.7 | Moderate-high |
| Preston HS | 6 (least disadvantaged) | 7.2 (highest) | Moderate |

**Pearson r = 0.84** — more disadvantaged catchments have worse pedestrian safety outcomes. Reservoir HS, which serves the most disadvantaged catchment in this study, also has the most indicators below 6.0 (HS1, HS2, HS3, HS5, HS9). This is the core policy finding for the Regen Melbourne 300,000 Streets initiative.

---

## 8. Crash Analysis Results (2021–2025)

| Year | Darebin LGA ped/cyc crashes |
|---|---|
| 2021 | 25 |
| 2022 | 53 |
| 2023 | 59 |
| 2024 | 73 |
| 2025 (partial) | 40 |

| School | Total crashes (400m) | During school hours |
|---|---|---|
| Preston HS | 15 | 4 (27%) |
| Reservoir HS | 4 | 0 |
| William Ruthven SC | 2 | 2 (100%) |

Peak crash hour across Darebin LGA: **17:00** (school pickup).

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| Modular `src/` structure | Each HS indicator in its own file — easy to update one indicator without touching others; aligns with team-based development |
| Healthy Streets framework | Internationally recognised, TfL-adopted — comparable with other cities and has a published evidence base |
| School-level ML (not crash-level) | HS scores are per-school; the question is "can open data predict HS scores?" |
| Ridge regression over Random Forest | Only 3 training samples — Ridge is regularised and doesn't overfit; RF would immediately |
| LOO-CV over train/test split | Meaningless with n=3; LOO gives 3 independent predictions |
| EPSG:7855 for metric operations | GDA2020 / MGA zone 55 — Victorian standard, sub-metre accuracy for buffers in Melbourne |
| `config.py` as single source of truth | All paths, school gates, HS indicator list in one place — any script can import rather than hardcode |
| `run_all.py` master runner | New team members run one command; skip logic means OSM queries don't re-run unnecessarily |
| Separate equity / crash / demographics scripts | Keeps analytical modules independent and re-runnable; `--from 8` allows fast re-analysis without re-downloading data |

---

## 10. Future Work

| Priority | Enhancement |
|---|---|
| High | Build `scenario_engine.py` — load `hs_predictor.pkl`, modify a feature value (e.g. `cycle_pct_400m`), call `pipe.predict()`, show before/after HS scores and severity change |
| High | Add 2+ more schools to strengthen ML generalisability |
| Medium | Run `spatial_features.py` for all Victorian government secondary schools — enables statewide HS prediction |
| Medium | Expand field observations to more gate locations per school |
| Medium | Add Safe Routes to School map using `networks.gpkg` and `osmnx` routing |
| Low | Deploy interactive map as a hosted web app for council access |
| Low | Automate quarterly re-run on new crash data releases |
| Low | Sentiment analysis on community feedback (surveys, Engage Victoria) using VADER or DistilBERT |

---

## 11. Run Order

```bash
python run_all.py           # recommended — runs all 10 steps, skips existing outputs

# or step by step:
python crash_analysis.py         # Step 1  — crash data (internet required)
python spatial_features.py       # Step 2  — OSM features (~5 min per school)
python environmental_features.py # Step 3  — AQI + crime
python main.py                   # Step 4  — HS scoring, charts, maps, recommendations
python feature_engineering.py    # Step 5  — ML feature matrix
python ml_model.py               # Step 6  — Ridge regression + LOO-CV
python seifa_analysis.py         # Step 7  — SEIFA disadvantage analysis
python equity_analysis.py        # Step 8  — Equity overlay (SEIFA × HS scores)
python crash_trend_analysis.py   # Step 9  — Crash trends + school-hours analysis
python demographics_chart.py     # Step 10 — ABS Census demographics chart

# Re-run only analysis steps (data already downloaded):
python run_all.py --from 8
```

---

## 12. Dependencies

| Script | Key packages |
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

```bash
pip install -r requirements.txt
```

---

*300,000 Streets of Melbourne — Regen Melbourne × RMIT University*
