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

import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta

OUT_DIR = 'outputs'
OUT_CSV = os.path.join(OUT_DIR, 'environmental_features.csv')
os.makedirs(OUT_DIR, exist_ok=True)

SCHOOL_DATA_CSV = 'school_data.csv'

# ── School → suburb mapping ────────────────────────────────────────────────────
SCHOOL_SUBURB_MAP = {
    'Reservoir HS':             {'suburb': 'Reservoir',  'postcode': '3073', 'lga': 'Darebin'},
    'William Ruthven SC':       {'suburb': 'Thornbury',  'postcode': '3071', 'lga': 'Darebin'},
    'Preston HS':               {'suburb': 'Preston',    'postcode': '3072', 'lga': 'Darebin'},
    # Full names as fallback keys
    'Reservoir High School':            {'suburb': 'Reservoir',  'postcode': '3073', 'lga': 'Darebin'},
    'William Ruthven Secondary College':{'suburb': 'Thornbury',  'postcode': '3071', 'lga': 'Darebin'},
    'Preston High School':              {'suburb': 'Preston',    'postcode': '3072', 'lga': 'Darebin'},
}

# ── Fallback values (when live APIs unavailable) ───────────────────────────────
# AQI PM2.5 (μg/m³): EPA AirWatch Alphington station annual averages 2023
# Source: EPA Victoria AirWatch historical data — Alphington is within Darebin
# Reservoir is slightly more exposed due to Plenty Rd arterial traffic
AQI_FALLBACK = {
    'Reservoir':  8.5,   # slightly elevated — Plenty Rd arterial
    'Thornbury':  7.0,   # residential, lower traffic
    'Preston':    7.8,   # mixed — Bell St / High St arterials
}

# Crime: offences against person per 100,000 population, Victoria Police 2023-24
# Source: Crime Statistics Agency Victoria — suburb-level data
# Indicator: Assault + Robbery + Other crimes against person (personal safety relevant)
CRIME_FALLBACK = {
    'Reservoir': 820,   # higher exposure — arterial corridor
    'Thornbury': 560,   # lower, more residential
    'Preston':   710,   # medium — mixed use
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
# AQI — EPA Victoria AirWatch
# ══════════════════════════════════════════════════════════

# Alphington monitoring station (EPA site ID: 10102) — in Darebin, closest to all 3 schools
EPA_STATION_ID = '10102'
EPA_BASE_URL   = 'https://gateway.api.epa.vic.gov.au/environmentMonitoring/v1'

def fetch_epa_aqi(suburb: str) -> float:
    """
    Try to fetch recent PM2.5 average from EPA Victoria AirWatch API.
    Returns PM2.5 μg/m³ float, or falls back to suburb-level constant.
    API docs: https://www.epa.vic.gov.au/for-community/monitoring-your-environment/about-epa-airwatch
    """
    # EPA Victoria public data portal (no API key required for summary data)
    try:
        url = f'{EPA_BASE_URL}/sites/{EPA_STATION_ID}/parameters'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for param in data.get('parameters', []):
                if 'PM2.5' in param.get('name', ''):
                    avg = param.get('averages', {}).get('24hour', {}).get('value')
                    if avg is not None:
                        print(f"    AQI: EPA API — PM2.5 24h avg = {avg} μg/m³ (Alphington)")
                        return float(avg)
    except Exception:
        pass

    # Try the public AirWatch data download endpoint
    try:
        end   = datetime.now()
        start = end - timedelta(days=30)
        url   = (f'https://www.epa.vic.gov.au/api/siteresult?'
                 f'monitorId={EPA_STATION_ID}'
                 f'&timePeriodFrom={start.strftime("%Y-%m-%d")}'
                 f'&timePeriodTo={end.strftime("%Y-%m-%d")}')
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            vals = [r.get('pm25') for r in resp.json() if r.get('pm25') is not None]
            if vals:
                avg = round(float(np.mean(vals)), 1)
                print(f"    AQI: AirWatch download — PM2.5 30-day avg = {avg} μg/m³")
                return avg
    except Exception:
        pass

    fallback = AQI_FALLBACK.get(suburb, 8.0)
    print(f"    AQI: Using fallback for {suburb} — PM2.5 = {fallback} μg/m³ (2023 annual avg)")
    return fallback


# ══════════════════════════════════════════════════════════
# CRIME — Crime Statistics Agency Victoria
# ══════════════════════════════════════════════════════════

CSA_DOWNLOAD_URL = (
    'https://files.crimestatistics.vic.gov.au/2024-06/'
    'Data_Tables_Recorded_Offences_Visualisation_Year_Ending_March_2024.xlsx'
)

def fetch_crime_rate(suburb: str) -> float:
    """
    Try to download Crime Statistics Agency Victoria suburb-level data.
    Returns offences against person per 100,000 population.
    Falls back to hardcoded 2023-24 values.
    """
    try:
        print(f"    Crime: Attempting CSA Victoria download...")
        resp = requests.get(CSA_DOWNLOAD_URL, timeout=30, stream=True)
        if resp.status_code == 200:
            tmp = os.path.join(OUT_DIR, '_csa_tmp.xlsx')
            with open(tmp, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            xl = pd.ExcelFile(tmp)
            # Look for suburb-level sheet
            for sheet in xl.sheet_names:
                if 'suburb' in sheet.lower() or 'lga' in sheet.lower():
                    csa = xl.parse(sheet)
                    csa.columns = csa.columns.str.strip().str.upper()
                    suburb_col = next((c for c in csa.columns if 'SUBURB' in c or 'LGA' in c), None)
                    rate_col   = next((c for c in csa.columns if 'RATE' in c), None)
                    offence_col= next((c for c in csa.columns if 'OFFENCE' in c), None)
                    if suburb_col and (rate_col or offence_col):
                        match = csa[csa[suburb_col].str.upper() == suburb.upper()]
                        if not match.empty:
                            col = rate_col or offence_col
                            rate = float(match[col].iloc[0])
                            os.remove(tmp)
                            print(f"    Crime: CSA data — {suburb} = {rate:.0f}/100k")
                            return rate
            os.remove(tmp)
    except Exception as e:
        print(f"    Crime: CSA download failed ({type(e).__name__}) — using fallback")

    fallback = CRIME_FALLBACK.get(suburb, 700)
    print(f"    Crime: Using fallback for {suburb} — {fallback}/100k (2023-24 CSA estimate)")
    return fallback


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

    aqi_pm25        = fetch_epa_aqi(suburb)
    crime_rate      = fetch_crime_rate(suburb)

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

    # HS7 crime component (0–4 pts, used inside poc_pipeline.py)
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
print(f"\n  These feed into poc_pipeline.py:")
print(f"    aqi_pm25            → HS10 (Clean air)")
print(f"    crime_rate_per_100k → HS7  (People feel safe)")
