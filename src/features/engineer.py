"""
Feature Engineering — School Streets ML Pipeline.

Reads crash_data_statewide.csv and produces ml_features.csv for model training.

Base features (20 across 6 groups):
  Time:       hour, day_of_week, month, is_weekend, is_school_hours
  Speed:      speed_zone_num, is_high_speed_zone
  Road class: road_geometry_code
  Geometry:   no_of_vehicles
  Lighting:   light_condition_code, is_dark
  School:     dist_to_gate_m, near_school_400m

Spatial features (from spatial_features.csv if present):
  ~36 OSM-derived features per school at 200m / 400m / 800m buffers

Target: serious_or_fatal (SEVERITY == 1 fatal or 2 serious injury)
"""
import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from src.scoring.cys import compute_cys


def build_ml_features(
    in_csv: str = None,
    spatial_csv: str = None,
    school_data_csv: str = 'school_data.csv',
    out_csv: str = None,
) -> str:
    """
    Build ML feature matrix from statewide crash data.

    Args:
        in_csv:          path to crash_data_statewide.csv (default: outputs/crash_data_statewide.csv)
        spatial_csv:     path to spatial_features.csv     (default: outputs/spatial_features.csv)
        school_data_csv: path to school_data.csv for manual CYS lookup
        out_csv:         output path for ml_features.csv  (default: outputs/ml_features.csv)

    Returns:
        str: path to saved ml_features.csv
    """
    if in_csv      is None: in_csv      = os.path.join('outputs', 'crash_data_statewide.csv')
    if spatial_csv is None: spatial_csv = os.path.join('outputs', 'spatial_features.csv')
    if out_csv     is None: out_csv     = os.path.join('outputs', 'ml_features.csv')

    print('\n' + '='*60)
    print('  Feature Engineering — ML Pipeline')
    print('='*60)
    print(f'\nReading {in_csv}...')
    df = pd.read_csv(in_csv, low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    if 'NEAREST_SCHOOL' in df.columns:
        df['nearest_school'] = df['NEAREST_SCHOOL']
    if 'DIST_TO_GATE_M' in df.columns:
        df['dist_to_gate_m'] = df['DIST_TO_GATE_M']
    print(f'  {len(df):,} crashes loaded')

    # ── Target variable ────────────────────────────────────────────────────────
    df['SEVERITY'] = pd.to_numeric(df['SEVERITY'], errors='coerce')
    df['serious_or_fatal'] = df['SEVERITY'].isin([1, 2]).astype(int)
    print(f'  Target: {df["serious_or_fatal"].sum():,} serious/fatal ({df["serious_or_fatal"].mean()*100:.1f}%)')

    # ── Time features ──────────────────────────────────────────────────────────
    df['ACCIDENT_DATE'] = pd.to_datetime(df['ACCIDENT_DATE'], dayfirst=True, errors='coerce')

    def _parse_hour(t):
        t = str(t).strip().zfill(4)
        try:
            if ':' in t:
                return int(t.split(':')[0])
            return int(t[:2])
        except Exception:
            return np.nan

    if 'ACCIDENT_TIME' in df.columns:
        df['hour'] = df['ACCIDENT_TIME'].apply(_parse_hour)
    else:
        df['hour'] = np.nan

    df['day_of_week']     = df['ACCIDENT_DATE'].dt.dayofweek
    df['month']           = df['ACCIDENT_DATE'].dt.month
    df['is_weekend']      = (df['day_of_week'] >= 5).astype(int)
    df['is_school_hours'] = (
        (df['day_of_week'] < 5) &
        (df['hour'].between(7, 9) | df['hour'].between(14, 17))
    ).astype(int)

    # ── Speed zone ─────────────────────────────────────────────────────────────
    df['speed_zone_num']     = pd.to_numeric(df.get('SPEED_ZONE', pd.Series(dtype=str)), errors='coerce')
    df['is_high_speed_zone'] = (df['speed_zone_num'] >= 60).astype(int)

    # ── Road class and geometry ────────────────────────────────────────────────
    df['road_geometry_code'] = pd.to_numeric(df.get('ROAD_GEOMETRY', pd.Series(dtype=str)), errors='coerce')
    df['no_of_vehicles']     = pd.to_numeric(df.get('NO_OF_VEHICLES', pd.Series(dtype=str)), errors='coerce')

    # ── Lighting ───────────────────────────────────────────────────────────────
    df['light_condition_code'] = pd.to_numeric(df.get('LIGHT_CONDITION', pd.Series(dtype=str)), errors='coerce')
    df['is_dark']              = (df['light_condition_code'] > 1).astype(int)

    # ── School proximity ───────────────────────────────────────────────────────
    df['dist_to_gate_m']   = pd.to_numeric(df.get('DIST_TO_GATE_M', pd.Series(dtype=str)), errors='coerce')
    df['near_school_400m'] = (df['dist_to_gate_m'] <= 400).astype(int)

    # ── CYS — 3-tier loading ───────────────────────────────────────────────────
    # Tier 1: manual column in school_data.csv
    # Tier 2: compute from spatial_features.csv via src.scoring.cys.compute_cys
    # Tier 3: NaN
    df['cys_score'] = np.nan

    if os.path.exists(school_data_csv):
        sd = pd.read_csv(school_data_csv)
        sd.columns = sd.columns.str.strip()
        _cys_col  = next((c for c in sd.columns if 'CYS' in c.upper() or 'CYCLING SAFETY' in c.upper()), None)
        _name_col = next((c for c in sd.columns if 'SCHOOL' in c.upper() and 'NAME' in c.upper()), None) or \
                    next((c for c in sd.columns if 'SCHOOL' in c.upper()), None)
        if _cys_col and _name_col:
            cys_map = sd.groupby(_name_col)[_cys_col].mean().to_dict()
            df['cys_score'] = df['nearest_school'].map(cys_map)
            print(f'  CYS: manual scores joined from {school_data_csv}')

    if df['cys_score'].isna().all() and os.path.exists(spatial_csv):
        _short_map = {
            'Reservoir High School':             'Reservoir HS',
            'William Ruthven Secondary College': 'William Ruthven SC',
            'Preston High School':               'Preston HS',
        }
        sf = pd.read_csv(spatial_csv)
        cys_map = {srow['school_name']: compute_cys(srow.to_dict()) for _, srow in sf.iterrows()}
        df['cys_score'] = df['nearest_school'].map(
            lambda n: cys_map.get(_short_map.get(n, n), np.nan)
        )
        filled = df['cys_score'].notna().sum()
        print(f'  CYS: computed from spatial_features.csv ({filled:,} crashes matched)')

    # ── Assemble base feature matrix ───────────────────────────────────────────
    BASE_FEATURES = [
        'hour', 'day_of_week', 'month', 'is_weekend', 'is_school_hours',
        'speed_zone_num', 'is_high_speed_zone',
        'road_geometry_code',
        'no_of_vehicles',
        'light_condition_code', 'is_dark',
        'dist_to_gate_m', 'near_school_400m',
        'cys_score',
    ]

    id_cols = ['ACCIDENT_NO', 'nearest_school', 'serious_or_fatal']
    ml = df[id_cols + BASE_FEATURES].copy()

    # ── Optional: merge spatial features ──────────────────────────────────────
    spatial_feature_cols = []
    if os.path.exists(spatial_csv):
        print(f'\nMerging spatial features from {spatial_csv}...')
        sf = pd.read_csv(spatial_csv)
        spatial_feature_cols = [c for c in sf.columns if c not in {'school_name', 'gate_lat', 'gate_lon'}]
        ml = ml.merge(
            sf.rename(columns={'school_name': 'nearest_school'}),
            on='nearest_school',
            how='left',
        )
        ml.drop(columns=['gate_lat', 'gate_lon'], inplace=True, errors='ignore')
        print(f'  Added {len(spatial_feature_cols)} spatial features')
    else:
        print(f'\n  (spatial_features.csv not found — run spatial_features.py first for richer features)')

    # ── Save ───────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(out_csv) or '.', exist_ok=True)
    ml.to_csv(out_csv, index=False)

    print(f'\n{"="*60}')
    print(f'  Feature matrix saved -> {out_csv}')
    print(f'  Rows: {len(ml):,}  |  Base features: {len(BASE_FEATURES)}  |  Spatial: {len(spatial_feature_cols)}')
    print(f'  Target balance: {df["serious_or_fatal"].mean()*100:.1f}% serious/fatal')
    print(f'{"="*60}')
    return out_csv


if __name__ == '__main__':
    build_ml_features()
