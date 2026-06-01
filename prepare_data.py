"""
prepare_data.py — build docs/data/data.json from pipeline outputs.

Run this after python run_all.py to refresh the dashboard.
"""
import sys
import json
import shutil
import importlib.util
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent
OUTPUTS    = ROOT / 'outputs'
DASH_DATA  = ROOT / 'docs' / 'data'
CHARTS_DIR = DASH_DATA / 'charts'

REQUIRED_FILES = {
    'hs_scores':       OUTPUTS / 'hs_scores.csv',
    'recommendations': OUTPUTS / 'recommendations.csv',
    'ml_predictions':  OUTPUTS / 'ml_predictions.csv',
    'seifa':           OUTPUTS / 'seifa_darebin.csv',
    'config':          ROOT / 'config.py',
}

CHART_FILES = [
    'chart1_safety_scores.png',
    'chart2_hazard_severity.png',
    'chart3_score_breakdown.png',
    'chart_hs_correlation.png',
    'chart_hs_prediction.png',
    'chart_feature_importance.png',
    'chart_equity_seifa.png',
    'chart_crash_trends.png',
    'chart4_demographics.png',
]

HS_NAMES = {
    'HS1':  'Pedestrians',
    'HS2':  'Easy to cross',
    'HS3':  'Shade and shelter',
    'HS4':  'Rest places',
    'HS5':  'Not too noisy',
    'HS6':  'Active travel',
    'HS7':  'Feel safe',
    'HS8':  'Things to do',
    'HS9':  'Feel relaxed',
    'HS10': 'Clean air',
}
HS_CODES = list(HS_NAMES.keys())


def check_required_files():
    missing = [str(p) for p in REQUIRED_FILES.values() if not p.exists()]
    if missing:
        sys.exit(
            '\n[ERROR] Missing source files — run the pipeline first:\n'
            + '\n'.join(f'  {p}' for p in missing)
        )


def load_config_gates():
    spec = importlib.util.spec_from_file_location('config', REQUIRED_FILES['config'])
    cfg  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg.SCHOOL_GATES, cfg.SCHOOL_SHORT_NAMES


def compute_severity(row):
    hs2     = row.get('HS2')
    hs1     = row.get('HS1')
    hs5     = row.get('HS5')
    overall = row.get('HS_overall')

    if pd.notna(hs2) and hs2 < 4.0:  return 'Major'
    if pd.notna(hs1) and hs1 < 4.0:  return 'Major'
    if pd.notna(hs5) and hs5 < 3.0:  return 'Major'

    all_vals = [row.get(c) for c in HS_CODES]
    low = sum(1 for v in all_vals if pd.notna(v) and v < 6.0)
    if low >= 2:                            return 'Moderate'
    if pd.notna(overall) and overall < 5.0: return 'Moderate'

    return 'Minor'


def build_schools(gates, short_names, hs_df, rec_df, seifa_df):
    schools = []

    for full_name, gate_info in gates.items():
        short = short_names.get(full_name, full_name)

        row_full  = hs_df[hs_df['School'] == full_name]
        row_short = hs_df[hs_df['School_short'] == short] if 'School_short' in hs_df.columns else pd.DataFrame()
        row = row_full if not row_full.empty else row_short
        if row.empty:
            print(f'[WARN] No HS scores for {full_name} — skipping')
            continue
        row = row.iloc[0]

        hs_scores = {code: round(float(row[code]), 2) for code in HS_CODES if code in row.index}
        overall   = round(float(row['HS_overall']), 2) if 'HS_overall' in row.index else None
        severity  = compute_severity(dict(row))

        school_recs = rec_df[
            (rec_df['School'] == full_name) | (rec_df['School'] == short)
        ].copy()

        priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
        school_recs['_prio_sort'] = school_recs['Priority'].map(priority_order).fillna(9)
        school_recs = school_recs.sort_values('_prio_sort')

        key_hazard         = school_recs.iloc[0]['Hazard']         if not school_recs.empty else ''
        key_recommendation = school_recs.iloc[0]['Recommendation'] if not school_recs.empty else ''

        recs_list = [
            {
                'indicator':      r['HS_indicator'],
                'hazard':         r['Hazard'],
                'recommendation': r['Recommendation'],
                'priority':       r['Priority'],
                'cost':           r['Cost'],
                'timeframe':      r['Timeframe'],
            }
            for _, r in school_recs.iterrows()
        ]

        seifa_row  = seifa_df[seifa_df['School'] == full_name]
        seifa_data = {}
        if not seifa_row.empty:
            sr = seifa_row.iloc[0]
            seifa_data = {
                'irsd_score':           round(float(sr['IRSD_Score_Weighted']), 1),
                'irsd_decile':          round(float(sr['IRSD_Decile']), 1),
                'disadvantage_level':   str(sr['Disadvantage_Level']),
                'suburb':               str(sr['Suburb']),
                'catchment_population': int(sr['Catchment_Population']) if 'Catchment_Population' in sr.index else None,
                'implication':          str(sr['Implication']) if 'Implication' in sr.index else '',
            }

        schools.append({
            'name':               full_name,
            'short_name':         short,
            'lat':                float(gate_info['lat']),
            'lng':                float(gate_info['lon']),
            'address':            gate_info.get('addr', ''),
            'severity':           severity,
            'overall_score':      overall,
            'hs_scores':          hs_scores,
            'key_hazard':         key_hazard,
            'key_recommendation': key_recommendation,
            'seifa':              seifa_data,
            'recommendations':    recs_list,
        })

    return schools


def build_ml_results(ml_df):
    results = []
    for code in HS_CODES:
        pred_col   = f'{code}_pred'
        actual_col = f'{code}_actual'
        if pred_col not in ml_df.columns or actual_col not in ml_df.columns:
            continue
        mae = float(np.mean(np.abs(ml_df[pred_col] - ml_df[actual_col])))
        results.append({
            'indicator': code,
            'name':      HS_NAMES[code],
            'mae':       round(mae, 3),
        })
    results.sort(key=lambda x: x['mae'])
    return results


def build_scenarios(schools):
    """Pre-compute all 10 interventions for each school."""
    try:
        from src.scenarios.engine import run_scenario
        from src.scenarios.interventions import INTERVENTIONS
    except ImportError as e:
        print(f'[WARN] Cannot import scenario engine ({e}) — skipping scenarios')
        return {}

    scenarios = {}
    for school in schools:
        short = school['short_name']
        scenarios[short] = {}
        for key, iv in INTERVENTIONS.items():
            try:
                result = run_scenario(short, [key])
                scenarios[short][key] = {
                    'label':             iv['label'],
                    'cost':              iv['cost'],
                    'timeframe':         iv['timeframe'],
                    'hs_target':         iv.get('hs_target', ''),
                    'baseline_overall':  result['baseline']['HS_overall'],
                    'scenario_overall':  result['scenario']['HS_overall'],
                    'delta_overall':     result['deltas']['HS_overall'],
                    'baseline_severity': result['baseline']['severity'],
                    'scenario_severity': result['scenario']['severity'],
                    'deltas':   {c: result['deltas'][c]   for c in HS_CODES},
                    'baseline': {c: result['baseline'][c] for c in HS_CODES},
                    'scenario': {c: result['scenario'][c] for c in HS_CODES},
                }
            except Exception as e:
                print(f'[WARN] Scenario {short}/{key}: {e}')
    return scenarios


def build_crash_geojson():
    """Convert crash_data_darebin.csv to GeoJSON FeatureCollection."""
    path = OUTPUTS / 'crash_data_darebin.csv'
    if not path.exists():
        return None
    df = pd.read_csv(path)
    sev_label = {1: 'Fatal', 2: 'Serious injury', 3: 'Other injury'}
    features = []
    for _, r in df.iterrows():
        lat = r.get('LATITUDE')
        lon = r.get('LONGITUDE')
        if pd.isna(lat) or pd.isna(lon):
            continue
        sev = int(r['SEVERITY']) if pd.notna(r.get('SEVERITY')) else 3
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [round(float(lon), 5), round(float(lat), 5)]},
            'properties': {
                'id':           str(r.get('ACCIDENT_NO', '')),
                'date':         str(r.get('ACCIDENT_DATE', '')),
                'time':         str(r.get('ACCIDENT_TIME', '')),
                'severity':     sev,
                'severity_label': sev_label.get(sev, 'Injury'),
                'type':         str(r.get('ACCIDENT_TYPE_DESC', '')),
                'speed_zone':   int(r['SPEED_ZONE']) if pd.notna(r.get('SPEED_ZONE')) and str(r.get('SPEED_ZONE')) != '999' else None,
                'school':       str(r.get('nearest_school', '')),
                'dist_m':       round(float(r['dist_to_gate_m']), 0) if pd.notna(r.get('dist_to_gate_m')) else None,
                'killed':       int(r.get('NO_PERSONS_KILLED', 0)),
                'injured_serious': int(r.get('NO_PERSONS_INJ_2', 0)),
                'light':        str(r.get('LIGHT_CONDITION', '')),
                'road_geometry': str(r.get('ROAD_GEOMETRY_DESC', '')),
                'day':          str(r.get('DAY_WEEK_DESC', '')),
            }
        })
    return {'type': 'FeatureCollection', 'features': features}


def build_heatmap_points():
    """Return [[lat, lon, intensity]] for Leaflet.heat using statewide crash data filtered to Darebin LGA."""
    statewide = OUTPUTS / 'crash_data_statewide.csv'
    if statewide.exists():
        df = pd.read_csv(statewide, usecols=lambda c: c in [
            'LATITUDE', 'LONGITUDE', 'SEVERITY', 'LGA_NAME'])
        if 'LGA_NAME' in df.columns:
            df = df[df['LGA_NAME'].str.upper().str.contains('DAREBIN', na=False)]
        else:
            # fallback: bounding box around Darebin
            df = df[
                df['LATITUDE'].between(-37.80, -37.66) &
                df['LONGITUDE'].between(144.97, 145.08)
            ]
    else:
        df = pd.read_csv(OUTPUTS / 'crash_data_darebin.csv', usecols=lambda c: c in [
            'LATITUDE', 'LONGITUDE', 'SEVERITY'])
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])
    points = []
    for _, r in df.iterrows():
        sev = int(r.get('SEVERITY', 3))
        intensity = round((4 - sev) / 3.0, 2)   # fatal→1.0, serious→0.67, minor→0.33
        points.append([round(float(r['LATITUDE']), 5), round(float(r['LONGITUDE']), 5), intensity])
    return points


def build_network_geojson():
    """Read walk_400m and cycling_400m from networks.gpkg → GeoJSON."""
    path = OUTPUTS / 'networks.gpkg'
    if not path.exists():
        return {'walk': None, 'cycling': None}
    try:
        import geopandas as gpd
        result = {}
        for layer_key, layer_name in [('walk', 'walk_400m'), ('cycling', 'cycling_400m')]:
            try:
                gdf = gpd.read_file(path, layer=layer_name, engine='pyogrio')
                gdf = gdf.to_crs('EPSG:4326')
                features = []
                for _, row in gdf.iterrows():
                    geom = row.geometry
                    if geom is None or geom.is_empty:
                        continue
                    geom_json = geom.__geo_interface__
                    # Round coordinates to 5dp to reduce file size
                    def round_coords(coords):
                        if isinstance(coords[0], (int, float)):
                            return [round(coords[0], 5), round(coords[1], 5)]
                        return [round_coords(c) for c in coords]
                    geom_json['coordinates'] = round_coords(geom_json['coordinates'])
                    features.append({
                        'type': 'Feature',
                        'geometry': geom_json,
                        'properties': {
                            'school': str(row.get('school_name', '')),
                            'highway': str(row.get('highway', '')),
                        }
                    })
                result[layer_key] = {'type': 'FeatureCollection', 'features': features}
                print(f'[OK] {layer_name}: {len(features)} edges')
            except Exception as e:
                print(f'[WARN] Could not read {layer_name}: {e}')
                result[layer_key] = None
        return result
    except ImportError:
        print('[WARN] geopandas not available — skipping network GeoJSON')
        return {'walk': None, 'cycling': None}


def build_spatial_stats():
    """Return per-school OSM feature counts for map tooltips."""
    path = OUTPUTS / 'spatial_features.csv'
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    result = {}
    want = ['crossings_400m', 'signals_400m', 'tree_count_100m', 'shelter_count_200m',
            'bench_count_200m', 'pt_stops_400m', 'cycle_pct_400m', 'footpath_pct_400m',
            'green_pct_400m', 'arterial_pct_400m']
    for _, row in df.iterrows():
        school = str(row.get('school_name', row.get('school_short', '')))
        result[school] = {col: round(float(row[col]), 1) if col in row.index and pd.notna(row[col]) else None
                          for col in want}
    return result


def build_stats(schools):
    """Build summary stats for the hero banner."""
    major_count = sum(1 for s in schools if s['severity'] == 'Major')

    stats = {
        'schools_assessed': len(schools),
        'major_hazards':    major_count,
        'equity_r':         0.84,
        'peak_crash_hour':  '17:00',
        'crash_darebin':    0,
        'crash_schools':    0,
    }

    darebin_path = OUTPUTS / 'crash_data_darebin.csv'
    if darebin_path.exists():
        df = pd.read_csv(darebin_path)
        stats['crash_darebin'] = len(df)
        if 'dist_to_gate_m' in df.columns:
            stats['crash_schools'] = int((df['dist_to_gate_m'] <= 400).sum())

    return stats


def copy_charts():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for fname in CHART_FILES:
        src = OUTPUTS / fname
        if src.exists():
            shutil.copy2(src, CHARTS_DIR / fname)
            copied.append(fname)
        else:
            missing.append(fname)
    return copied, missing


def main():
    print('-' * 60)
    print('prepare_data.py -- 300,000 Streets dashboard data builder')
    print('-' * 60)

    check_required_files()

    gates, short_names = load_config_gates()
    print(f'[OK] config.py  -> {len(gates)} school gates loaded')

    hs_df    = pd.read_csv(REQUIRED_FILES['hs_scores'])
    rec_df   = pd.read_csv(REQUIRED_FILES['recommendations'])
    ml_df    = pd.read_csv(REQUIRED_FILES['ml_predictions'])
    seifa_df = pd.read_csv(REQUIRED_FILES['seifa'])
    print(f'[OK] hs_scores.csv         -> {len(hs_df)} schools')
    print(f'[OK] recommendations.csv   -> {len(rec_df)} recommendations')
    print(f'[OK] ml_predictions.csv    -> {len(ml_df)} schools')
    print(f'[OK] seifa_darebin.csv     -> {len(seifa_df)} schools')

    DASH_DATA.mkdir(parents=True, exist_ok=True)

    schools    = build_schools(gates, short_names, hs_df, rec_df, seifa_df)
    ml_results = build_ml_results(ml_df)
    stats      = build_stats(schools)

    print('[..] Pre-computing scenarios (10 interventions × 3 schools)...')
    scenarios = build_scenarios(schools)
    if scenarios:
        total = sum(len(v) for v in scenarios.values())
        print(f'[OK] Scenarios computed     -> {total} results')

    print('[..] Building map layers (crashes, networks, heatmap)...')
    crash_geojson    = build_crash_geojson()
    heatmap_points   = build_heatmap_points()
    networks         = build_network_geojson()
    spatial_stats    = build_spatial_stats()
    print(f'[OK] Crash points: {len(crash_geojson["features"]) if crash_geojson else 0}')
    print(f'[OK] Heatmap points: {len(heatmap_points)}')

    data = {
        'generated_at':   datetime.utcnow().isoformat() + 'Z',
        'stats':          stats,
        'schools':        schools,
        'ml_results':     ml_results,
        'scenarios':      scenarios,
        'crash_geojson':  crash_geojson,
        'heatmap_points': heatmap_points,
        'networks':       networks,
        'spatial_stats':  spatial_stats,
        'charts': {
            'chart1':             'chart1_safety_scores.png',
            'chart1_caption':     'Safety scores — all 3 schools across 10 HS indicators',
            'chart2':             'chart2_hazard_severity.png',
            'chart2_caption':     'Per-indicator score comparison across schools',
            'chart3':             'chart3_score_breakdown.png',
            'chart3_caption':     'Per-school indicator breakdown',
            'correlation':        'chart_hs_correlation.png',
            'prediction':         'chart_hs_prediction.png',
            'feature_importance': 'chart_feature_importance.png',
            'equity':             'chart_equity_seifa.png',
            'crash_trends':       'chart_crash_trends.png',
            'demographics':       'chart4_demographics.png',
        },
    }

    out_path = DASH_DATA / 'data.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'[OK] data.json written  -> {out_path}')

    copied, missing = copy_charts()
    print(f'[OK] Charts copied      -> {len(copied)} files to docs/data/charts/')
    if missing:
        print(f'[WARN] Charts not found -> {", ".join(missing)}')

    print()
    print('-- Summary --------------------------------------------------')
    for s in schools:
        print(
            f"  {s['short_name']:<28}  severity={s['severity']:<10}"
            f"  overall={s['overall_score']}  recs={len(s['recommendations'])}"
        )
    print(f'  ML indicators evaluated:  {len(ml_results)}')
    print(f'  Scenarios pre-computed:   {sum(len(v) for v in scenarios.values())}')
    print(f'  Charts in docs/data/charts/: {len(copied)}')
    print('-' * 60)
    print('Done. Open docs/index.html in a browser (use a local server).')
    print('-' * 60)


if __name__ == '__main__':
    main()
