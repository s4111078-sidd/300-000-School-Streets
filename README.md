# 300,000 Streets of Melbourne — School Streets Safety Analysis

A pedestrian safety assessment tool for walking routes around three secondary schools in Melbourne's northern suburbs. Built in collaboration between **Regen Melbourne** and **RMIT University**.

---

## Schools assessed

| School | Address | Gate coordinates |
|---|---|---|
| Reservoir High School | 855 Plenty Rd, Reservoir VIC 3073 | -37.7224, 145.0294 |
| William Ruthven Secondary College | 60 Merrilands Rd, Reservoir VIC 3073 | -37.69654, 145.00299 |
| Preston High School | 2-16 Cooma St, Preston VIC 3072 | -37.7417, 145.0071 |

---

## Scoring system

Each assessed location is scored across three dimensions (0 = worst, 10 = best):

| Score | Meaning |
|---|---|
| **FAS** — Footpath Accessibility Score | Footpath presence, width, continuity, and condition |
| **CSS** — Crossing Safety Score | Crossing type, distance, visibility, and signals |
| **EEI** — Environmental Exposure Indicator | Traffic volume, speed, lighting, and school zone |

Overall score = average of FAS + CSS + EEI. A score of **6.0 or above** is considered good.

Hazard severity is classified as **Major**, **Moderate**, or **Minor**.

---

## Project structure

```
300-000-School-Streets/
├── school_data.csv              ← Field observation data (update to refresh outputs)
├── demographics_darebin.csv     ← ABS Census 2021 demographic data for Reservoir & Preston
├── requirements.txt             ← Python dependencies
│
├── crash_analysis.py            ← Downloads Victorian road crash data from data.vic.gov.au
├── poc_pipeline.py              ← Charts, interactive maps, and recommendations (pandas / matplotlib / folium)
├── pyqgis_pipeline.py           ← GIS automation: KDE heatmap, buffers, layers, PNG exports (PyQGIS)
│
└── outputs/
    ├── crash_data_darebin.csv       ← Produced by crash_analysis.py
    │
    ├── chart1_safety_scores.png     ← Produced by poc_pipeline.py
    ├── chart2_hazard_severity.png
    ├── chart3_score_breakdown.png
    ├── chart4_demographics.png
    ├── heatmap.png
    ├── map_interactive.html         ← Interactive map (open in browser)
    ├── map_heatmap.html             ← Interactive heatmap with crash markers (open in browser)
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

Run the scripts in this order:

```
crash_analysis.py  →  poc_pipeline.py  →  pyqgis_pipeline.py
```

---

### Step 1 — Download crash data (`crash_analysis.py`)

Downloads Victorian road crash data from [data.vic.gov.au](https://data.vic.gov.au) and filters for:
- City of Darebin LGA
- Within 400m of a school gate
- Pedestrian or cyclist involvement
- Last 5 years

```bash
pip install pandas numpy requests
python crash_analysis.py
```

Output: `outputs/crash_data_darebin.csv`

Columns include: `ACCIDENT_NO`, `ACCIDENT_DATE`, `SEVERITY`, `SPEED_ZONE`, `LATITUDE`, `LONGITUDE`, `nearest_school`, `dist_to_gate_m`, `PED_OR_CYC`.

> The script downloads three tables from the Victorian Open Data portal (`accident.csv`, `node.csv`, `person.csv`) and joins them on `ACCIDENT_NO`. Coordinates and LGA come from `node.csv`.

---

### Step 2 — Charts, interactive maps, and recommendations (`poc_pipeline.py`)

Reads `school_data.csv`, `demographics_darebin.csv`, and (if present) `outputs/crash_data_darebin.csv`.

```bash
pip install pandas matplotlib numpy folium rasterio
python poc_pipeline.py
```

Outputs saved to `outputs/`:

| File | Description |
|---|---|
| `chart1_safety_scores.png` | Average FAS / CSS / EEI scores per school |
| `chart2_hazard_severity.png` | Hazard severity counts per school |
| `chart3_score_breakdown.png` | Per-location score breakdown |
| `chart4_demographics.png` | Demographic context (income, car ownership, transport mode) |
| `heatmap.png` | Static heatmap of assessment point scores |
| `map_interactive.html` | Interactive map — click markers for location details and crash data |
| `map_heatmap.html` | Interactive heatmap with crash markers overlay |
| `recommendations.csv` | Auto-generated rule-based intervention list |

Open HTML files by double-clicking them in Finder, or drag into any browser.

---

### Step 3 — GIS layers and map exports (`pyqgis_pipeline.py`)

Requires **QGIS 3.x** installed. Run Step 1 first so `outputs/crash_data_darebin.csv` exists (optional — the crash layer is skipped gracefully if the file is missing).

**From the QGIS Python Console** (recommended):
```python
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

**Standalone** (edit `QGIS_PREFIX` at the top of the script to match your QGIS install path):
```bash
python pyqgis_pipeline.py
```

Outputs saved to `outputs/`:

| File | Description |
|---|---|
| `kde_heatmap.tif` | KDE raster (GeoTIFF, EPSG:7855) |
| `school_streets.gpkg` | GeoPackage with all vector layers |
| `school_streets.qgz` | QGIS project — open directly in QGIS |
| `map_<School>.png` | Per-school static map image (1200×900 px) |

Layers created in QGIS (bottom to top):

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
2. Re-run `crash_analysis.py` if you want fresh crash data (downloads live from data.vic.gov.au).
3. Re-run `poc_pipeline.py` → `pyqgis_pipeline.py` in order.

---

## Dependencies

| Script | Requirements |
|---|---|
| `crash_analysis.py` | `pandas`, `numpy`, `requests` |
| `poc_pipeline.py` | `pandas`, `matplotlib`, `numpy`, `folium`, `rasterio` |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS + processing framework — not pip-installable) |

Install pip dependencies:
```bash
pip install -r requirements.txt
```

> `pyqgis_pipeline.py` requires QGIS 3.x to be installed separately. It cannot be installed via pip.

---

## Crash data source

Victorian Road Crash Data is published by the Department of Transport and Planning and available at:
[https://www.data.vic.gov.au/data/dataset/victoria-road-crash-data](https://www.data.vic.gov.au/data/dataset/victoria-road-crash-data)

Tables used: `accident.csv`, `node.csv` (coordinates + LGA), `person.csv` (road user type).

---

*300,000 Streets of Melbourne — Regen Melbourne x RMIT University*
