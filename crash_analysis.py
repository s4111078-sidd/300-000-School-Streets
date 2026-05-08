"""
Victorian Road Crash Data — School Streets Safety Analysis (Statewide)
Downloads crash data from data.vic.gov.au and filters for:
  - Statewide pedestrian or cyclist involvement
  - All Victorian government secondary schools (via DET; fallback: 3 Darebin gates)
  - Last 5 years

Also produces a backward-compatible Darebin subset within 400m of the original 3 gates.

Data schema (confirmed):
  accident.csv  — ACCIDENT_NO, ACCIDENT_DATE, SEVERITY, SPEED_ZONE, ...
  node.csv      — ACCIDENT_NO, LGA_NAME, LATITUDE, LONGITUDE, POSTCODE_CRASH
  person.csv    — ACCIDENT_NO, ROAD_USER_TYPE_DESC (join key for ped/cyc filter)

Run:    python crash_analysis.py
Output: outputs/crash_data_statewide.csv
        outputs/crash_data_darebin.csv   (backward compat)
"""

import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime, timedelta

OUT_DIR       = 'outputs'
OUT_STATEWIDE = os.path.join(OUT_DIR, 'crash_data_statewide.csv')
OUT_DAREBIN   = os.path.join(OUT_DIR, 'crash_data_darebin.csv')

# Fallback: original 3 Darebin school gates
SCHOOL_GATES = {
    'Reservoir HS':       {'lat': -37.7224,  'lon': 145.0294},
    'William Ruthven SC': {'lat': -37.69654, 'lon': 145.00299},
    'Preston HS':         {'lat': -37.7417,  'lon': 145.0071},
}
BUFFER_M   = 400
YEARS_BACK = 5

URLS = {
    'accident': 'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/20772c1a-8b19-424a-a733-eb84f725f611/download/accident.csv',
    'person':   'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/60c8fc0c-2806-40f3-bb33-5c52691120e8/download/person.csv',
    'node':     'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/466fd3b5-201b-42b5-b10d-e926324fa215/download/node.csv',
}

VIC_BBOX = {'lat_min': -39.2, 'lat_max': -33.9, 'lon_min': 140.9, 'lon_max': 150.0}


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def fetch_school_gates():
    """Download Victorian government secondary school locations from DET via CKAN API.
    Falls back to the original 3 Darebin gates on any error."""
    fallback = dict(SCHOOL_GATES)
    try:
        print('  Fetching school locations from DET (data.vic.gov.au)...')
        pkg = requests.get(
            'https://www.data.vic.gov.au/api/3/action/package_show',
            params={'id': 'school-locations-time-series'},
            timeout=30,
        )
        pkg.raise_for_status()
        resources = pkg.json()['result']['resources']

        csv_resources = [r for r in resources if r.get('format', '').upper() == 'CSV']
        if not csv_resources:
            raise ValueError('No CSV resource found in DET package')

        csv_resources.sort(key=lambda r: r.get('name', ''), reverse=True)
        url = csv_resources[0]['url']
        print(f'  Downloading: {csv_resources[0].get("name", url)}')

        r = requests.get(url, timeout=60)
        r.raise_for_status()
        schools = pd.read_csv(StringIO(r.text), low_memory=False)
        schools.columns = schools.columns.str.strip().str.upper()

        mask = (
            schools.get('SCHOOL_SECTOR_NAME', pd.Series(dtype=str))
                   .astype(str).str.upper().str.contains('GOVERNMENT', na=False) &
            schools.get('SCHOOL_TYPE_NAME', pd.Series(dtype=str))
                   .astype(str).str.upper().str.contains('SECONDARY|COMBINED', na=False) &
            schools.get('STATUS', pd.Series(dtype=str))
                   .astype(str).str.upper().str.contains('OPEN', na=False)
        )
        schools = schools[mask].dropna(subset=['Y', 'X'])

        schools = schools[
            schools['Y'].between(VIC_BBOX['lat_min'], VIC_BBOX['lat_max']) &
            schools['X'].between(VIC_BBOX['lon_min'], VIC_BBOX['lon_max'])
        ]

        gates = {}
        for _, row in schools.iterrows():
            name = str(row.get('SCHOOL_NAME', row.get('SCHOOL_NO', 'Unknown'))).strip()
            gates[name] = {'lat': float(row['Y']), 'lon': float(row['X'])}

        gates.update(fallback)  # ensure original 3 Darebin gates are always present
        print(f'  Loaded {len(gates):,} school gates ({len(gates) - len(fallback)} from DET + {len(fallback)} Darebin fallback)')
        return gates

    except Exception as e:
        print(f'  Warning: DET school download failed ({e})')
        print(f'  Using fallback: {len(fallback)} Darebin gates')
        return fallback


def fetch_csv(name, url):
    print(f'  Downloading {name}.csv ...')
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    print(f'    {len(df):,} rows')
    return df


# ── 1. Download ────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  Victorian Road Crash Analysis — Statewide')
print('='*60)
print('\n[1/5] Downloading crash tables...')
accident = fetch_csv('accident', URLS['accident'])
node     = fetch_csv('node',     URLS['node'])
person   = fetch_csv('person',   URLS['person'])

# ── 2. Join node → accident (coordinates + LGA) ───────────────────────────────
print('\n[2/5] Joining node → accident on ACCIDENT_NO...')
node_slim = node[['ACCIDENT_NO', 'LGA_NAME', 'LATITUDE', 'LONGITUDE', 'POSTCODE_CRASH']].drop_duplicates('ACCIDENT_NO')
merged = accident.merge(node_slim, on='ACCIDENT_NO', how='left')
print(f'  Merged: {len(merged):,} accidents with coordinates')

# ── 3. Filter: last 5 years ───────────────────────────────────────────────────
print('\n[3/5] Filtering last 5 years...')
cutoff = datetime.now() - timedelta(days=365 * YEARS_BACK)
merged['ACCIDENT_DATE'] = pd.to_datetime(merged['ACCIDENT_DATE'], dayfirst=True, errors='coerce')
merged = merged[merged['ACCIDENT_DATE'] >= cutoff].copy()
print(f'  {len(merged):,} accidents since {cutoff.strftime("%Y-%m-%d")}')

# ── 4. Filter: pedestrian/cyclist involvement (statewide) ─────────────────────
print('\n[4/5] Filtering pedestrian/cyclist involvement (statewide)...')
ped_cyc_acc = person[
    person['ROAD_USER_TYPE_DESC'].astype(str).str.upper()
    .str.contains('PEDESTRIAN|CYCLIST|BICYCL', na=False)
]['ACCIDENT_NO'].unique()
print(f'  {len(ped_cyc_acc):,} ped/cyc accidents in Victoria')

merged['PED_OR_CYC'] = merged['ACCIDENT_NO'].isin(ped_cyc_acc)
statewide = merged[merged['PED_OR_CYC']].dropna(subset=['LATITUDE', 'LONGITUDE']).copy()
print(f'  {len(statewide):,} ped/cyc crashes with valid coordinates (last {YEARS_BACK} yrs)')

# ── 5. School proximity — vectorized over gates, not rows ─────────────────────
print('\n[5/5] Computing school proximity...')
all_gates = fetch_school_gates()

crash_lats = statewide['LATITUDE'].to_numpy()
crash_lons = statewide['LONGITUDE'].to_numpy()

best_dist   = np.full(len(statewide), np.inf)
best_school = np.full(len(statewide), '', dtype=object)

for school, gate in all_gates.items():
    d = haversine_m(crash_lats, crash_lons, gate['lat'], gate['lon'])
    closer = d < best_dist
    best_dist[closer]   = d[closer]
    best_school[closer] = school

statewide = statewide.copy()
statewide['nearest_school'] = best_school
statewide['dist_to_gate_m'] = np.round(best_dist, 1)
print(f'  Nearest school assigned for {len(statewide):,} crashes')

# ── Save statewide ────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
statewide.to_csv(OUT_STATEWIDE, index=False)
print(f'\nSaved statewide -> {OUT_STATEWIDE}  ({len(statewide)} rows)')

# ── Darebin backward-compat subset ───────────────────────────────────────────
darebin_schools = set(SCHOOL_GATES.keys())
darebin = statewide[
    statewide['nearest_school'].isin(darebin_schools) &
    (statewide['dist_to_gate_m'] <= BUFFER_M)
].copy()

# ── Summary ───────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  CRASH SUMMARY — statewide ped/cyc, last 5 years')
print('='*60)
if len(statewide) > 0:
    by_severity = statewide['SEVERITY'].value_counts().sort_index()
    print(f'  Fatal (1):          {by_severity.get(1, 0):,}')
    print(f'  Serious injury (2): {by_severity.get(2, 0):,}')
    print(f'  Other injury (3):   {by_severity.get(3, 0):,}')
    print(f'  Non-injury (4):     {by_severity.get(4, 0):,}')

print(f'\n  Darebin subset (within {BUFFER_M}m of 3 school gates): {len(darebin)} crashes')

if len(darebin) > 0:
    cols = ['nearest_school', 'ACCIDENT_NO']
    if 'NO_PERSONS_KILLED' in darebin.columns:
        summary = darebin.groupby('nearest_school').agg(
            crash_count=('ACCIDENT_NO', 'count'),
            fatal=('NO_PERSONS_KILLED', 'sum'),
            serious_injury=('NO_PERSONS_INJ_2', 'sum') if 'NO_PERSONS_INJ_2' in darebin.columns else ('ACCIDENT_NO', 'count'),
        ).reset_index()
        print(summary.to_string(index=False))

darebin.to_csv(OUT_DAREBIN, index=False)
print(f'\nSaved Darebin subset -> {OUT_DAREBIN}  ({len(darebin)} rows)')
