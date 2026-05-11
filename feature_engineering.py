"""
Feature Engineering — School-level HS Score Prediction
Builds a school-level feature matrix from open data so that
ML can predict Healthy Streets indicator scores (HS1–HS10)
without requiring field surveys at new schools.

Feature groups (X):
  Spatial    — OSM-derived at 200m/400m buffers (spatial_features.csv)
  Environmental — AQI (PM2.5) + crime rate  (environmental_features.csv)
  Crash stats   — count, severity rate, peak-hour fraction (crash_data_statewide.csv)

Targets (y):
  HS1–HS10 individual indicator scores    (hs_scores.csv)

Run:    python feature_engineering.py
Output: outputs/ml_school_features.csv   (1 row per school)
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

SPATIAL_CSV = os.path.join('outputs', 'spatial_features.csv')
ENV_CSV     = os.path.join('outputs', 'environmental_features.csv')
CRASH_CSV   = os.path.join('outputs', 'crash_data_statewide.csv')
HS_CSV      = os.path.join('outputs', 'hs_scores.csv')
OUT_CSV     = os.path.join('outputs', 'ml_school_features.csv')

# canonical short names used in crash data and spatial_features short rows
SHORT_NAMES = {'Reservoir HS', 'William Ruthven SC', 'Preston HS'}

# maps full name → short name for normalisation
FULL_TO_SHORT = {
    'Reservoir High School':             'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School':               'Preston HS',
}

HS_TARGETS = ['HS1','HS2','HS3','HS4','HS5','HS6','HS7','HS8','HS9','HS10']

# OSM spatial features selected as open-data proxies for each HS indicator
SPATIAL_FEATURES = [
    # HS1 — pedestrian infrastructure
    'footpath_pct_200m',
    'footpath_pct_400m',
    # HS2 — crossings
    'crossings_400m',
    'signals_400m',
    'crossing_density_400m',
    # HS3 — shade + shelter
    'tree_count_100m',
    'shelter_count_200m',
    'green_pct_400m',
    # HS4 — rest places
    'bench_count_200m',
    'park_count_400m',
    # HS5 / HS9 — traffic stress
    'avg_speed_400m',
    'arterial_pct_400m',
    'high_speed_road_400m',
    'road_count_400m',
    # HS6 — active travel infrastructure
    'cycle_pct_400m',
    'protected_cycle_length_400m',
    'pt_stops_400m',
    # HS8 — things to see and do
    'amenity_count_400m',
    'cafe_count_400m',
    # context
    'walk_length_400m',
]

ENV_FEATURES = [
    'crime_rate_per_100k',   # HS7 proxy
    'aqi_pm25',              # HS10 proxy
]

print('\n' + '='*60)
print('  Feature Engineering — School-level HS Score Prediction')
print('='*60)

# ── 1. Spatial features (one row per school, short names only) ─────────────
print('\n[1/4] Loading spatial features...')
assert os.path.exists(SPATIAL_CSV), f"Run spatial_features.py first — {SPATIAL_CSV} not found"
sf_raw = pd.read_csv(SPATIAL_CSV)
# keep only short-name rows (deduplicate full-name duplicates)
sf = sf_raw[sf_raw['school_name'].isin(SHORT_NAMES)].copy()
sf = sf.rename(columns={'school_name': 'school'})
missing_sp = [c for c in SPATIAL_FEATURES if c not in sf.columns]
if missing_sp:
    print(f'  Warning: missing spatial columns: {missing_sp}')
sf_sel = sf[['school'] + [c for c in SPATIAL_FEATURES if c in sf.columns]].copy()
print(f'  {len(sf_sel)} schools × {len(sf_sel.columns)-1} spatial features')

# ── 2. Environmental features ──────────────────────────────────────────────
print('\n[2/4] Loading environmental features...')
assert os.path.exists(ENV_CSV), f"Run environmental_features.py first — {ENV_CSV} not found"
ef_raw = pd.read_csv(ENV_CSV)
ef_raw['school'] = ef_raw['school_name'].map(FULL_TO_SHORT).fillna(ef_raw['school_name'])
ef_sel = ef_raw[['school'] + ENV_FEATURES].copy()
print(f'  {len(ef_sel)} schools × {len(ENV_FEATURES)} environmental features')

# ── 3. Crash statistics aggregated per school ──────────────────────────────
print('\n[3/4] Aggregating crash statistics...')
assert os.path.exists(CRASH_CSV), f"Run crash_analysis.py first — {CRASH_CSV} not found"
cr = pd.read_csv(CRASH_CSV, low_memory=False)
cr.columns = cr.columns.str.strip().str.upper()

cr['school'] = cr['NEAREST_SCHOOL']
cr['SEVERITY'] = pd.to_numeric(cr['SEVERITY'], errors='coerce')
cr['serious_or_fatal'] = cr['SEVERITY'].isin([1, 2]).astype(int)
cr['ACCIDENT_TIME_RAW'] = cr['ACCIDENT_TIME'].astype(str).str.strip().str.zfill(4)
cr['hour'] = cr['ACCIDENT_TIME_RAW'].apply(
    lambda t: int(t.split(':')[0]) if ':' in t else int(t[:2]) if t[:2].isdigit() else np.nan
)
cr['is_school_hours'] = (
    (pd.to_datetime(cr['ACCIDENT_DATE'], dayfirst=True, errors='coerce').dt.dayofweek < 5) &
    (cr['hour'].between(7, 9) | cr['hour'].between(14, 17))
).astype(int)

crash_agg = (cr.groupby('school')
               .agg(
                   crash_count          = ('ACCIDENT_NO', 'count'),
                   serious_or_fatal_rate= ('serious_or_fatal', 'mean'),
                   school_hours_pct     = ('is_school_hours', 'mean'),
                   avg_speed_zone       = ('SPEED_ZONE',
                                           lambda x: pd.to_numeric(x, errors='coerce')
                                                       .where(lambda v: v < 200)   # drop sentinel codes 777/888/999
                                                       .mean()),
               )
               .round(4)
               .reset_index())
print(f'  Crash aggregates: {crash_agg.to_string(index=False)}')

# ── 4. HS targets ──────────────────────────────────────────────────────────
print('\n[4/4] Loading HS indicator targets...')
assert os.path.exists(HS_CSV), f"Run poc_pipeline.py first — {HS_CSV} not found"
hs = pd.read_csv(HS_CSV)
hs['school'] = hs['School_short']
hs_sel = hs[['school'] + HS_TARGETS + ['HS_overall']].copy()
print(f'  {len(hs_sel)} schools × {len(HS_TARGETS)} HS targets')

# ── Join all sources on school ─────────────────────────────────────────────
ml = (sf_sel
      .merge(ef_sel,    on='school', how='left')
      .merge(crash_agg, on='school', how='left')
      .merge(hs_sel,    on='school', how='left'))

FEATURE_COLS = (
    [c for c in SPATIAL_FEATURES if c in ml.columns] +
    [c for c in ENV_FEATURES if c in ml.columns] +
    ['crash_count', 'serious_or_fatal_rate', 'school_hours_pct', 'avg_speed_zone']
)

# ── Save ───────────────────────────────────────────────────────────────────
os.makedirs('outputs', exist_ok=True)
col_order = ['school'] + FEATURE_COLS + HS_TARGETS + ['HS_overall']
ml[col_order].to_csv(OUT_CSV, index=False)

print(f'\n{"="*60}')
print(f'  School-level feature matrix saved -> {OUT_CSV}')
print(f'  Schools:  {len(ml)}')
print(f'  Features: {len(FEATURE_COLS)}')
print(f'    Spatial:       {len([c for c in SPATIAL_FEATURES if c in ml.columns])}')
print(f'    Environmental: {len([c for c in ENV_FEATURES if c in ml.columns])}')
print(f'    Crash stats:   4  (count, severity rate, peak-hour %, avg speed zone)')
print(f'  Targets:  {len(HS_TARGETS)}  (HS1–HS10)')
print(f'{"="*60}')
print()
print('  Feature → HS indicator mapping:')
print('    footpath_pct_*         → HS1  (pedestrians)')
print('    crossings/signals      → HS2  (easy to cross)')
print('    tree/shelter/green     → HS3  (shade + shelter)')
print('    bench/park             → HS4  (rest places)')
print('    avg_speed/arterial_pct → HS5  (not too noisy) + HS9 (feel relaxed)')
print('    cycle/pt_stops         → HS6  (active travel choice)')
print('    crime_rate_per_100k    → HS7  (feel safe)')
print('    amenity/cafe           → HS8  (things to do)')
print('    aqi_pm25               → HS10 (clean air)')
print()
print('  Next: python ml_model.py')
