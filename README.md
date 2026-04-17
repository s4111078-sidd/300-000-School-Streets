# 300,000 Streets — School Street Safety & Active Travel Analysis

> **RMIT University | COSC2667/2777 | Partner: Regen Melbourne**

A data science pipeline that collects, scores, maps, and generates recommendations for school street safety in Melbourne's City of Darebin.

---

## Team

| Name | Student ID |
|---|---|
| Vipparla Reddy Pranay | |
| Venkata Nagendra Anamala | |
| Siddhartha Ananthula | |
| Hishikesh Phukan | |
| Sameer Yadav | |

**Supervisor:** Lawrence  
**Industry Partner:** Regen Melbourne

---

## Project Overview

The 300,000 Streets project analyses street safety conditions around schools in the City of Darebin, Melbourne. Field observations are collected via Google Form, scored using a documented framework, mapped using QGIS and Folium, and processed through a rule-based recommendation engine that automatically generates prioritised infrastructure interventions.

### Schools Assessed
- Reservoir High School — 855 Plenty Rd, Reservoir VIC 3073
- William Ruthven Secondary College — 60 Merrilands Rd, Reservoir VIC 3073
- Preston High School — 2-16 Cooma St, Preston VIC 3072 *(Sprint 2)*

---

## Scores Produced

| Score | Full Name | Range | Measures |
|---|---|---|---|
| **FAS** | Footpath Accessibility Score | 0–10 | Footpath quality, width, continuity, condition |
| **CSS** | Crossing Safety Score | 0–10 | Crossing type, distance from gate, visibility, tactile indicators |
| **EEI** | Environmental Exposure Indicator | 0–10 | Speed limit, traffic volume, lanes, calming measures |

Higher score = safer conditions for all three metrics.

---

## Repository Structure

```
300000-Streets/
│
├── poc_pipeline.py                  # Main pipeline — run this to generate all outputs
├── school_data.csv                  # Field observation data (Google Form export)
│
├── outputs/
│   ├── chart1_safety_scores.png     # Bar chart — FAS, CSS, EEI per school
│   ├── chart2_hazard_severity.png   # Stacked bar — hazard count by severity
│   ├── chart3_score_breakdown.png   # Per-school score breakdown with severity badge
│   ├── map_interactive.html         # Interactive Folium map — open in browser
│   ├── recommendations.csv          # Auto-generated recommendations from rules engine
│   └── school_data_scored.csv       # Cleaned and scored dataset
│
│
└── README.md
```

---

## Getting Started

### Prerequisites

Make sure you have Python 3.8 or above installed. Then install the required libraries:

```bash
pip install pandas matplotlib folium numpy
```

### Running the Pipeline

1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/300000-streets.git
cd 300000-streets
```

2. Make sure your CSV file is in the same folder as `poc_pipeline.py`

3. Open `poc_pipeline.py` and confirm the filename on line 20 matches your CSV:
```python
CSV_FILE = '300_000_Streets___Dataset_-_Form_Responses.csv'
```

4. Run the pipeline
```bash
python poc_pipeline.py
```

5. All outputs are saved to the `/outputs/` folder automatically

### Expected Terminal Output

```
=======================================================
  300,000 Streets — POC Pipeline
=======================================================

[1/5] Loading and cleaning data...
      Loaded 2 rows
      SCORES CONFIRMED:
      School_short  FAS  CSS  EEI  Sev_clean
      Reservoir HS  4.2  5.7  7.0  Moderate
William Ruthven SC  9.5  6.8 10.0  Moderate

[2/5] Generating Chart 1 — Safety Scores...
[3/5] Generating Chart 2 — Hazard Severity...
[4/5] Generating Chart 3 — Score Breakdown...
[5/5] Generating Interactive Map...

  All outputs saved to /outputs/
```

---

## How to Update Data

When new observations are collected:

1. Export the Google Form responses as CSV
2. Replace `school_data.csv` in the project folder with the new file
3. Make sure the filename matches `CSV_FILE` in `poc_pipeline.py`
4. Run `python poc_pipeline.py`
5. All charts, maps, and recommendations regenerate automatically

No code changes required when adding new rows or schools.

---

## Recommendation Engine

Recommendations are generated **automatically** from field data using a rule-based engine — not typed manually. The engine applies 10 documented rules to each observation row.

### Current Rules

| Rule | Trigger | Priority |
|---|---|---|
| FOOTPATH_MISSING | Footpath absent or broken | High |
| FOOTPATH_NARROW | Width < 1.5m | Medium |
| CROSSING_ABSENT | No formal crossing | High |
| CROSSING_TOO_FAR | Crossing > 150m from gate | High |
| TACTILE_MISSING | No tactile indicators | Medium |
| NO_SCHOOL_ZONE | No school zone signage | High |
| NO_TRAFFIC_CALMING | No calming + 3 or more lanes | High |
| NO_CYCLING_INFRA | No cycling infrastructure | Low |
| POOR_LIGHTING | Poor or no street lighting | Medium |
| VEGETATION_BLOCK | Vegetation blocking footpath | Medium |

---

## Tools and Technologies

| Tool | Purpose | License |
|---|---|---|
| Python 3.x | Pipeline, scoring, charts, recommendations | Free |
| pandas | Data cleaning and analysis | Free |
| matplotlib | Chart generation | Free |
| Folium | Interactive HTML map | Free |
| QGIS 3.x | Cartographic mapping, buffer zones | Free (GNU GPL) |
| GeoPackage | Spatial database format | Free |
| Google Forms | Field data collection | Free |
| OpenStreetMap | Base map layer | Free (ODbL) |

No paid tools or licenses required at any stage of this project.

---

## Data Collection

Field observations are collected using a 47-field Google Form covering:
- Footpath condition, width, continuity, and obstructions
- Pedestrian crossing type, distance, visibility, and tactile indicators
- Speed limits, school zone status, traffic volume, and lane count
- Cycling infrastructure, lighting, and hazard types


---

## Scoring Framework

All scores are calculated from field observations using documented formulas.  

### Severity Classification

| Severity | Condition |
|---|---|
| **Major** | FAS < 4.0 OR CSS < 4.0 OR EEI < 4.0 OR within 100m of gate with CSS < 5.0 |
| **Moderate** | FAS < 6.0 OR CSS < 6.0 OR EEI < 6.0 OR no school zone |
| **Minor** | All scores ≥ 6.0 and no critical conditions |

---

## References

- Australian Standard AS 1428.1 — Design for access and mobility
- VicRoads School Zone Guidelines
- Transport Accident Commission (TAC) Victoria — pedestrian safety research
- Regen Melbourne — 300,000 Streets initiative
- OpenStreetMap contributors (ODbL license)
