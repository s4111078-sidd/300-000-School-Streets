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

Run standalone:  python -m src.data.crash_downloader
Output:          outputs/crash_data_statewide.csv
                 outputs/crash_data_darebin.csv  (backward compat)
"""
import os
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
from io import StringIO

import numpy as np
import pandas as pd
import requests

from config import OUT_DIR, SCHOOL_GATES_BY_SHORT
from src.utils.geo import haversine_m

OUT_STATEWIDE = OUT_DIR / 'crash_data_statewide.csv'
OUT_DAREBIN   = OUT_DIR / 'crash_data_darebin.csv'

BUFFER_M   = 400
YEARS_BACK = 5

URLS = {
    'accident': 'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/20772c1a-8b19-424a-a733-eb84f725f611/download/accident.csv',
    'person':   'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/60c8fc0c-2806-40f3-bb33-5c52691120e8/download/person.csv',
    'node':     'https://opendata.transport.vic.gov.au/dataset/bb77800e-1857-4edc-bf9e-e188437a1c8e/resource/466fd3b5-201b-42b5-b10d-e926324fa215/download/node.csv',
}

VIC_BBOX = {'lat_min': -39.2, 'lat_max': -33.9, 'lon_min': 140.9, 'lon_max': 150.0}



def fetch_school_gates() -> dict:
    """
    Download Victorian government secondary school locations from DET via CKAN API.
    Falls back to the original 3 Darebin gates (SCHOOL_GATES_BY_SHORT) on any error.

    Returns:
        dict mapping school name → {'lat': float, 'lon': float}
    """
    fallback = dict(SCHOOL_GATES_BY_SHORT)
    try:
        print('  Fetching school locations from DET (discover.data.vic.gov.au)...')
        pkg = requests.get(
            'https://discover.data.vic.gov.au/api/3/action/package_show',
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

        def _col_mask(df, col, pattern):
            if col in df.columns:
                return df[col].astype(str).str.upper().str.contains(pattern, na=False)
            return pd.Series(True, index=df.index)

        mask = (
            _col_mask(schools, 'SCHOOL_SECTOR_NAME', 'GOVERNMENT') &
            _col_mask(schools, 'SCHOOL_TYPE_NAME',   'SECONDARY|COMBINED') &
            _col_mask(schools, 'STATUS',              'OPEN')
        )
        coord_cols = ['Y', 'X'] if 'Y' in schools.columns else ['LATITUDE', 'LONGITUDE']
        schools = schools[mask].dropna(subset=coord_cols)
        lat_col, lon_col = coord_cols

        schools = schools[
            schools[lat_col].between(VIC_BBOX['lat_min'], VIC_BBOX['lat_max']) &
            schools[lon_col].between(VIC_BBOX['lon_min'], VIC_BBOX['lon_max'])
        ]

        gates = {}
        for _, row in schools.iterrows():
            name = str(row.get('SCHOOL_NAME', row.get('SCHOOL_NO', 'Unknown'))).strip()
            gates[name] = {'lat': float(row[lat_col]), 'lon': float(row[lon_col])}

        gates.update(fallback)  # ensure original 3 Darebin gates are always present
        print(f'  Loaded {len(gates):,} school gates ({len(gates) - len(fallback)} from DET + {len(fallback)} Darebin fallback)')
        return gates

    except Exception as e:
        print(f'  Warning: DET school download failed ({e})')
        print(f'  Using fallback: {len(fallback)} Darebin gates')
        return fallback


def fetch_csv(name: str, url: str) -> pd.DataFrame:
    """Download a single crash data CSV from the VicRoads open data portal."""
    print(f'  Downloading {name}.csv ...')
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    print(f'    {len(df):,} rows')
    return df


def download_crash_data() -> None:
    """
    Download and process Victorian road crash data, saving two output files:
      - crash_data_statewide.csv: all ped/cyc crashes statewide for last 5 years
      - crash_data_darebin.csv:   Darebin subset within 400m of 3 school gates

    Data sourced from the Victorian Open Data portal (data.vic.gov.au).
    School gate locations sourced from the DET School Locations Time Series dataset.
    """
    print('\n' + '='*60)
    print('  Victorian Road Crash Analysis — Statewide')
    print('='*60)

    print('\n[1/5] Downloading crash tables...')
    accident = fetch_csv('accident', URLS['accident'])
    node     = fetch_csv('node',     URLS['node'])
    person   = fetch_csv('person',   URLS['person'])

    print('\n[2/5] Joining node → accident on ACCIDENT_NO...')
    node_slim = node[['ACCIDENT_NO', 'LGA_NAME', 'LATITUDE', 'LONGITUDE', 'POSTCODE_CRASH']].drop_duplicates('ACCIDENT_NO')
    merged = accident.merge(node_slim, on='ACCIDENT_NO', how='left')
    print(f'  Merged: {len(merged):,} accidents with coordinates')

    print('\n[3/5] Filtering last 5 years...')
    cutoff = datetime.now() - timedelta(days=365 * YEARS_BACK)
    merged['ACCIDENT_DATE'] = pd.to_datetime(merged['ACCIDENT_DATE'], dayfirst=True, errors='coerce')
    merged = merged[merged['ACCIDENT_DATE'] >= cutoff].copy()
    print(f'  {len(merged):,} accidents since {cutoff.strftime("%Y-%m-%d")}')

    print('\n[4/5] Filtering pedestrian/cyclist involvement (statewide)...')
    ped_cyc_acc = person[
        person['ROAD_USER_TYPE_DESC'].astype(str).str.upper()
        .str.contains('PEDESTRIAN|CYCLIST|BICYCL', na=False)
    ]['ACCIDENT_NO'].unique()
    print(f'  {len(ped_cyc_acc):,} ped/cyc accidents in Victoria')

    merged['PED_OR_CYC'] = merged['ACCIDENT_NO'].isin(ped_cyc_acc)
    statewide = merged[merged['PED_OR_CYC']].dropna(subset=['LATITUDE', 'LONGITUDE']).copy()
    print(f'  {len(statewide):,} ped/cyc crashes with valid coordinates (last {YEARS_BACK} yrs)')

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

    os.makedirs(str(OUT_DIR), exist_ok=True)
    statewide.to_csv(str(OUT_STATEWIDE), index=False)
    print(f'\nSaved statewide -> {OUT_STATEWIDE}  ({len(statewide)} rows)')

    darebin_schools = set(SCHOOL_GATES_BY_SHORT.keys())
    darebin = statewide[
        statewide['nearest_school'].isin(darebin_schools) &
        (statewide['dist_to_gate_m'] <= BUFFER_M)
    ].copy()

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

    if len(darebin) > 0 and 'NO_PERSONS_KILLED' in darebin.columns:
        summary = darebin.groupby('nearest_school').agg(
            crash_count=('ACCIDENT_NO', 'count'),
            fatal=('NO_PERSONS_KILLED', 'sum'),
            serious_injury=('NO_PERSONS_INJ_2', 'sum') if 'NO_PERSONS_INJ_2' in darebin.columns else ('ACCIDENT_NO', 'count'),
        ).reset_index()
        print(summary.to_string(index=False))

    darebin.to_csv(str(OUT_DAREBIN), index=False)
    print(f'\nSaved Darebin subset -> {OUT_DAREBIN}  ({len(darebin)} rows)')


if __name__ == '__main__':
    download_crash_data()
