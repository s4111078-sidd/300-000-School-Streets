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
    """Import config.py and return SCHOOL_GATES dict."""
    spec = importlib.util.spec_from_file_location('config', REQUIRED_FILES['config'])
    cfg  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg.SCHOOL_GATES, cfg.SCHOOL_SHORT_NAMES


def compute_severity(row):
    hs2     = row.get('HS2')
    hs1     = row.get('HS1')
    hs5     = row.get('HS5')
    overall = row.get('HS_overall')

    if pd.notna(hs2) and hs2 < 3.0:  return 'Major'
    if pd.notna(hs1) and hs1 < 3.0:  return 'Major'
    if pd.notna(hs5) and hs5 < 2.0:  return 'Major'

    all_vals = [row.get(c) for c in HS_CODES]
    low = sum(1 for v in all_vals if pd.notna(v) and v < 6.0)
    if low >= 2:                       return 'Moderate'
    if pd.notna(overall) and overall < 5.0: return 'Moderate'

    return 'Minor'


def build_schools(gates, short_names, hs_df, rec_df, seifa_df):
    schools = []

    # Build a reverse map: short_name -> full_name
    short_to_full = {v: k for k, v in short_names.items()}

    for full_name, gate_info in gates.items():
        short = short_names.get(full_name, full_name)

        # HS scores row — hs_scores.csv may use full name or short name
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

        # Recommendations for this school (match on full name or short name)
        school_recs = rec_df[
            (rec_df['School'] == full_name) | (rec_df['School'] == short)
        ].copy()

        priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
        school_recs['_prio_sort'] = school_recs['Priority'].map(priority_order).fillna(9)
        school_recs = school_recs.sort_values('_prio_sort')

        key_hazard         = school_recs.iloc[0]['Hazard']        if not school_recs.empty else ''
        key_recommendation = school_recs.iloc[0]['Recommendation'] if not school_recs.empty else ''

        recs_list = [
            {
                'indicator':       r['HS_indicator'],
                'hazard':          r['Hazard'],
                'recommendation':  r['Recommendation'],
                'priority':        r['Priority'],
                'cost':            r['Cost'],
                'timeframe':       r['Timeframe'],
            }
            for _, r in school_recs.iterrows()
        ]

        # SEIFA — match on full name
        seifa_row = seifa_df[seifa_df['School'] == full_name]
        seifa_data = {}
        if not seifa_row.empty:
            sr = seifa_row.iloc[0]
            seifa_data = {
                'irsd_score':        round(float(sr['IRSD_Score_Weighted']), 1),
                'irsd_decile':       round(float(sr['IRSD_Decile']), 1),
                'disadvantage_level': str(sr['Disadvantage_Level']),
                'suburb':            str(sr['Suburb']),
                'catchment_population': int(sr['Catchment_Population']) if 'Catchment_Population' in sr.index else None,
                'implication':       str(sr['Implication']) if 'Implication' in sr.index else '',
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
    # Sort by MAE ascending
    results.sort(key=lambda x: x['mae'])
    return results


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

    hs_df   = pd.read_csv(REQUIRED_FILES['hs_scores'])
    rec_df  = pd.read_csv(REQUIRED_FILES['recommendations'])
    ml_df   = pd.read_csv(REQUIRED_FILES['ml_predictions'])
    seifa_df = pd.read_csv(REQUIRED_FILES['seifa'])
    print(f'[OK] hs_scores.csv         -> {len(hs_df)} schools')
    print(f'[OK] recommendations.csv   -> {len(rec_df)} recommendations')
    print(f'[OK] ml_predictions.csv    -> {len(ml_df)} schools')
    print(f'[OK] seifa_darebin.csv     -> {len(seifa_df)} schools')

    DASH_DATA.mkdir(parents=True, exist_ok=True)

    schools    = build_schools(gates, short_names, hs_df, rec_df, seifa_df)
    ml_results = build_ml_results(ml_df)

    data = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'schools':      schools,
        'ml_results':   ml_results,
        'charts': {
            'chart1':            'chart1_safety_scores.png',
            'chart1_caption':    'Safety scores — all 3 schools across 10 HS indicators',
            'chart2':            'chart2_hazard_severity.png',
            'chart2_caption':    'Per-indicator score comparison across schools',
            'chart3':            'chart3_score_breakdown.png',
            'chart3_caption':    'Per-school indicator breakdown',
            'correlation':       'chart_hs_correlation.png',
            'prediction':        'chart_hs_prediction.png',
            'feature_importance':'chart_feature_importance.png',
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
        rec_count = len(s['recommendations'])
        print(
            f"  {s['short_name']:<28}  severity={s['severity']:<10}"
            f"  overall={s['overall_score']}  recs={rec_count}"
        )
    print(f'  ML indicators evaluated: {len(ml_results)}')
    print(f'  Charts in docs/data/charts/: {len(copied)}')
    print('-' * 60)
    print('Done. Open docs/index.html in a browser.')
    print('-' * 60)


if __name__ == '__main__':
    main()
