"""
Victorian Road Crash Data — School Streets Safety Analysis
Downloads crash data from data.vic.gov.au and filters for:
  - City of Darebin LGA
  - Within 400m of 3 school gates
  - Pedestrian or cyclist involvement (ROAD_USER_TYPE_DESC)
  - Last 5 years

Data schema (confirmed):
  accident.csv  — ACCIDENT_NO, ACCIDENT_DATE, SEVERITY, SPEED_ZONE, ...
  node.csv      — ACCIDENT_NO, LGA_NAME, LATITUDE, LONGITUDE, POSTCODE_CRASH
  person.csv    — ACCIDENT_NO, ROAD_USER_TYPE_DESC (join key for ped/cyc filter)

Run:    conda run -n geo python crash_analysis.py
Output: outputs/crash_data_darebin.csv
"""

import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime, timedelta

OUT_DIR  = 'outputs'
OUT_CSV  = os.path.join(OUT_DIR, 'crash_data_darebin.csv')

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


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def fetch_csv(name, url):
    print(f'  Downloading {name}.csv ...')
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    print(f'    {len(df):,} rows')
    return df


# ── 1. Download ────────────────────────────────────────────────────────────────
print('\n' + '='*55)
print('  Victorian Road Crash Analysis')
print('='*55)
print('\n[1/5] Downloading crash tables...')
accident = fetch_csv('accident', URLS['accident'])
node     = fetch_csv('node',     URLS['node'])
person   = fetch_csv('person',   URLS['person'])

# ── 2. Join node → accident (gets LGA_NAME + coordinates) ────────────────────
print('\n[2/5] Joining node → accident on ACCIDENT_NO...')
# node.csv has: ACCIDENT_NO, LGA_NAME, LATITUDE, LONGITUDE
node_slim = node[['ACCIDENT_NO', 'LGA_NAME', 'LATITUDE', 'LONGITUDE', 'POSTCODE_CRASH']].drop_duplicates('ACCIDENT_NO')
merged = accident.merge(node_slim, on='ACCIDENT_NO', how='left')
print(f'  Merged: {len(merged):,} accidents with coordinates')
coords_ok = merged['LATITUDE'].notna().sum()
print(f'  {coords_ok:,} have valid coordinates')

# ── 3. Filter: City of Darebin ────────────────────────────────────────────────
print('\n[3/5] Filtering City of Darebin...')
darebin = merged[merged['LGA_NAME'].astype(str).str.upper().str.contains('DAREBIN', na=False)].copy()
print(f'  {len(darebin):,} accidents in City of Darebin')

# ── 4. Filter: last 5 years ───────────────────────────────────────────────────
print('\n[4/5] Filtering last 5 years and pedestrian/cyclist involvement...')
cutoff = datetime.now() - timedelta(days=365 * YEARS_BACK)
darebin['ACCIDENT_DATE'] = pd.to_datetime(darebin['ACCIDENT_DATE'], dayfirst=True, errors='coerce')
darebin = darebin[darebin['ACCIDENT_DATE'] >= cutoff].copy()
print(f'  {len(darebin):,} accidents in last {YEARS_BACK} years (since {cutoff.strftime("%Y-%m-%d")})')

# Flag pedestrian/cyclist via person.csv (ROAD_USER_TYPE_DESC)
ped_cyc_acc = person[
    person['ROAD_USER_TYPE_DESC'].astype(str).str.upper()
    .str.contains('PEDESTRIAN|CYCLIST|BICYCL', na=False)
]['ACCIDENT_NO'].unique()
print(f'  {len(ped_cyc_acc):,} accidents involving pedestrian or cyclist (all Victoria)')

darebin['PED_OR_CYC'] = darebin['ACCIDENT_NO'].isin(ped_cyc_acc)
ped_darebin = darebin[darebin['PED_OR_CYC']].copy()
print(f'  {len(ped_darebin):,} ped/cyc accidents in Darebin (last {YEARS_BACK} yrs)')

# ── 5. Filter: within 400m of a school gate ───────────────────────────────────
print('\n[5/5] Filtering within 400m of school gates...')
ped_darebin = ped_darebin.dropna(subset=['LATITUDE', 'LONGITUDE'])

nearest_school = []
dist_to_gate   = []

for _, row in ped_darebin.iterrows():
    best_d = float('inf')
    best_s = None
    for school, gate in SCHOOL_GATES.items():
        d = haversine_m(row['LATITUDE'], row['LONGITUDE'], gate['lat'], gate['lon'])
        if d < best_d:
            best_d = d
            best_s = school
    nearest_school.append(best_s)
    dist_to_gate.append(round(best_d, 1))

ped_darebin = ped_darebin.copy()
ped_darebin['nearest_school'] = nearest_school
ped_darebin['dist_to_gate_m'] = dist_to_gate

final = ped_darebin[ped_darebin['dist_to_gate_m'] <= BUFFER_M].copy()
print(f'  {len(final):,} crashes within {BUFFER_M}m of a school gate')

# ── Summary ───────────────────────────────────────────────────────────────────
print('\n' + '='*55)
print('  CRASH SUMMARY — last 5 years, ped/cyc, within 400m')
print('='*55)
if len(final) > 0:
    summary = final.groupby('nearest_school').agg(
        crash_count=('ACCIDENT_NO', 'count'),
        fatal=('NO_PERSONS_KILLED', 'sum'),
        serious_injury=('NO_PERSONS_INJ_2', 'sum'),
    ).reset_index()
    print(summary.to_string(index=False))
    print()
    print(final[['ACCIDENT_NO', 'ACCIDENT_DATE', 'SEVERITY', 'SPEED_ZONE',
                 'nearest_school', 'dist_to_gate_m']].to_string(index=False))
else:
    print('  No crashes found within 400m — try expanding buffer or checking data')
    print(f'\n  Darebin ped/cyc total (any distance): {len(ped_darebin)}')
    if len(ped_darebin) > 0:
        print('\n  Nearest crashes to school gates:')
        closest = ped_darebin.nsmallest(10, 'dist_to_gate_m')[
            ['ACCIDENT_NO', 'ACCIDENT_DATE', 'nearest_school', 'dist_to_gate_m', 'LATITUDE', 'LONGITUDE']
        ]
        print(closest.to_string(index=False))

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
final.to_csv(OUT_CSV, index=False)
print(f'\nSaved -> {OUT_CSV}  ({len(final)} rows)')
