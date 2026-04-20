# 300,000 Streets of Melbourne — School Streets Safety Analysis

A pedestrian safety assessment tool for walking routes around three secondary schools in Melbourne's northern suburbs. Built in collaboration between **Regen Melbourne** and **RMIT University**.

---

## Schools assessed

| School | Address |
|---|---|
| Reservoir High School | 855 Plenty Rd, Reservoir VIC 3073 |
| William Ruthven Secondary College | 60 Merrilands Rd, Reservoir VIC 3073 |
| Preston High School | 2-16 Cooma St, Preston VIC 3072 |

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
├── school_data.csv          ← Field observation data (update this to refresh outputs)
├── poc_pipeline.py          ← Charts + interactive map (pandas / matplotlib / folium)
├── pyqgis_pipeline.py       ← GIS automation (PyQGIS)
├── kde_analysis.py          ← KDE heatmap analysis — maintained by teammate
└── outputs/
    ├── chart1_safety_scores.png
    ├── chart2_hazard_severity.png
    ├── chart3_score_breakdown.png
    ├── map_interactive.html
    ├── recommendations.csv
    ├── kde_heatmap.tif          ← Produced by kde_analysis.py (input to PyQGIS pipeline)
    ├── map_Reservoir_HS.png     ← Per-school map exports
    ├── map_William_Ruthven_SC.png
    ├── school_streets.gpkg      ← GeoPackage (all vector layers)
    └── school_streets.qgz       ← QGIS project file
```

---

## How to run

### Step 1 — Charts, interactive map, and recommendations (`poc_pipeline.py`)

Requires Python 3 with `pandas`, `matplotlib`, `numpy`, and `folium`.

```bash
pip install pandas matplotlib numpy folium
python poc_pipeline.py
```

Outputs saved to `outputs/`:
- `chart1_safety_scores.png` — average FAS / CSS / EEI scores per school
- `chart2_hazard_severity.png` — hazard severity counts per school
- `chart3_score_breakdown.png` — per-location score breakdown
- `map_interactive.html` — open in any browser; click markers for details
- `recommendations.csv` — auto-generated rule-based intervention list

---

### Step 2 — KDE heatmap analysis (`kde_analysis.py`)

> Maintained by a separate team member. Run this before Step 3.

Produces `outputs/kde_heatmap.tif` — the raster input required by the PyQGIS pipeline.

```bash
python kde_analysis.py
```

---

### Step 3 — GIS layers and map exports (`pyqgis_pipeline.py`)

Requires **QGIS 3.x** installed. Run Step 2 first so `outputs/kde_heatmap.tif` exists.  
If the KDE raster is missing the pipeline will still run — the heatmap layer is simply skipped.

**From the QGIS Python Console** (recommended):
```python
exec(open('/full/path/to/pyqgis_pipeline.py').read())
```

**Standalone** (edit `QGIS_PREFIX` at the top of the script to match your QGIS install):
```bash
python pyqgis_pipeline.py
```

Outputs saved to `outputs/`:

| File | Description |
|---|---|
| `school_streets.gpkg` | GeoPackage with all vector layers |
| `school_streets.qgz` | QGIS project — open directly in QGIS |
| `map_<School>.png` | Per-school map image (1200×900 px) |

Layers created in QGIS (bottom to top):

| Layer | Style |
|---|---|
| OpenStreetMap | XYZ tile base map |
| Hazard Heatmap (KDE) | Green → yellow → red gradient, 65% opacity |
| 800m Walking Zone | Light grey buffer rings |
| 400m Walking Zone | Dark grey buffer rings |
| Safety Assessment Points | Circles coloured by severity (red / orange / green) |
| School Gates | Black star markers |

Buffers use **EPSG:7855** (GDA2020 / MGA zone 55) for accurate metric distances.  
Only schools with rows in `school_data.csv` get a gate marker and buffers — schools with no data are automatically skipped.

---

## Updating the data

1. Replace or edit `school_data.csv` with new field observations.
2. Re-run Step 1, Step 2, and Step 3 in order.

---

## Dependencies

| Script | Requirement |
|---|---|
| `poc_pipeline.py` | Python 3 — `pandas`, `matplotlib`, `numpy`, `folium` |
| `kde_analysis.py` | Python 3 — see teammate's script for dependencies |
| `pyqgis_pipeline.py` | QGIS 3.x (PyQGIS + processing framework) |

---

*300,000 Streets of Melbourne — Regen Melbourne x RMIT University*
