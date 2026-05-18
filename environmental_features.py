"""
Environmental Features — Healthy Streets Pipeline
Fetches AQI (HS10) and crime rate (HS7) data for each assessed school.

Data sources:
  AQI   — EPA Victoria AirWatch API (Alphington monitoring station, closest to Darebin)
           Falls back to suburb-level annual averages if API unavailable.
  Crime — Crime Statistics Agency Victoria (crimestatistics.vic.gov.au)
           Personal crime offence rate per 100,000 population by suburb.
           Falls back to hardcoded 2023-24 values if download fails.

Run:    python environmental_features.py
Output: outputs/environmental_features.csv
"""

import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
from datetime import datetime

from src.data.epa_fetcher   import fetch_epa_aqi,    AQI_FALLBACK
from src.data.crime_fetcher import fetch_crime_rate, CRIME_FALLBACK

OUT_DIR = 'outputs'
OUT_CSV = os.path.join(OUT_DIR, 'environmental_features.csv')
os.makedirs(OUT_DIR, exist_ok=True)

SCHOOL_DATA_CSV = 'school_data.csv'

# ── School → suburb mapping ────────────────────────────────────────────────────
SCHOOL_SUBURB_MAP = {
    'Reservoir HS':             {'suburb': 'Reservoir',  'postcode': '3073', 'lga': 'Darebin'},
    'William Ruthven SC':       {'suburb': 'Thornbury',  'postcode': '3071', 'lga': 'Darebin'},
    'Preston HS':               {'suburb': 'Preston',    'postcode': '3072', 'lga': 'Darebin'},
    'Reservoir High School':            {'suburb': 'Reservoir',  'postcode': '3073', 'lga': 'Darebin'},
    'William Ruthven Secondary College':{'suburb': 'Thornbury',  'postcode': '3071', 'lga': 'Darebin'},
    'Preston High School':              {'suburb': 'Preston',    'postcode': '3072', 'lga': 'Darebin'},
}

print("\n" + "="*60)
print("  Environmental Features — AQI & Crime Data")
print("="*60)

# ── Load school list ───────────────────────────────────────────────────────────
def load_schools():
    schools = list({k for k in SCHOOL_SUBURB_MAP.keys()
                    if 'High School' in k or 'Secondary College' in k or 'SC' in k or 'HS' in k})
    if os.path.exists(SCHOOL_DATA_CSV):
        try:
            sd = pd.read_csv(SCHOOL_DATA_CSV)
            sd.columns = sd.columns.str.strip()
            name_col = next((c for c in sd.columns if 'school name' in c.lower() or c.lower() == 'school'), None)
            if name_col:
                schools = sd[name_col].dropna().unique().tolist()
                print(f"  Loaded {len(schools)} schools from {SCHOOL_DATA_CSV}")
        except Exception as e:
            print(f"  Warning: could not read {SCHOOL_DATA_CSV} ({e})")
    return schools


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
schools = load_schools()
rows    = []

for school in schools:
    info   = SCHOOL_SUBURB_MAP.get(school, {})
    suburb = info.get('suburb', school)
    lga    = info.get('lga', 'Unknown')

    print(f"\n[{schools.index(school)+1}/{len(schools)}] {school}  ({suburb})")

    aqi_pm25   = fetch_epa_aqi(suburb)
    crime_rate = fetch_crime_rate(suburb, out_dir=OUT_DIR)

    # Derived: AQI category (US EPA PM2.5 breakpoints)
    if   aqi_pm25 <= 12:  aqi_category = 'Good'
    elif aqi_pm25 <= 35:  aqi_category = 'Moderate'
    elif aqi_pm25 <= 55:  aqi_category = 'Unhealthy for Sensitive Groups'
    elif aqi_pm25 <= 150: aqi_category = 'Unhealthy'
    else:                 aqi_category = 'Very Unhealthy'

    # HS10 score (0–10)
    if   aqi_pm25 <= 12:  hs10_base = 10.0
    elif aqi_pm25 <= 35:  hs10_base = 7.0
    elif aqi_pm25 <= 55:  hs10_base = 5.0
    elif aqi_pm25 <= 150: hs10_base = 2.0
    else:                 hs10_base = 0.0

    # HS7 crime component (0–4 pts, used inside main.py via compute_hs7)
    if   crime_rate <= 300:  hs7_crime_pts = 4.0
    elif crime_rate <= 600:  hs7_crime_pts = 3.0
    elif crime_rate <= 900:  hs7_crime_pts = 2.0
    elif crime_rate <= 1200: hs7_crime_pts = 1.0
    else:                    hs7_crime_pts = 0.0

    rows.append({
        'school_name'           : school,
        'suburb'                : suburb,
        'lga'                   : lga,
        'aqi_pm25'              : aqi_pm25,
        'aqi_category'          : aqi_category,
        'hs10_base_score'       : hs10_base,
        'crime_rate_per_100k'   : crime_rate,
        'hs7_crime_pts'         : hs7_crime_pts,
        'data_date'             : datetime.now().strftime('%Y-%m-%d'),
        'aqi_source'            : 'EPA AirWatch Alphington' if aqi_pm25 != AQI_FALLBACK.get(suburb) else 'Fallback 2023 annual avg',
        'crime_source'          : 'CSA Victoria 2023-24' if crime_rate != CRIME_FALLBACK.get(suburb) else 'Fallback 2023-24 estimate',
    })

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT_CSV, index=False)

print(f"\n{'='*60}")
print(f"  Environmental features saved -> {OUT_CSV}")
print(f"{'='*60}")
print(out_df[['school_name', 'suburb', 'aqi_pm25', 'aqi_category',
              'crime_rate_per_100k', 'hs7_crime_pts', 'hs10_base_score']].to_string(index=False))
print(f"\n  These feed into main.py:")
print(f"    aqi_pm25            → HS10 (Clean air)")
print(f"    crime_rate_per_100k → HS7  (People feel safe)")
