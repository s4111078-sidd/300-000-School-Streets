"""
Scenario engine — loads the trained Ridge model and predicts how HS indicator
scores would change after one or more physical interventions.

Strategy:
  Use actual HS scores as the baseline (they match ground truth exactly).
  Apply the MODEL's predicted DELTA (scenario − baseline) to those actual scores.
  This ensures the baseline is always correct and the delta is model-driven.

  scenario_score[i] = actual_score[i] + (model(X_scenario)[i] − model(X_baseline)[i])
  Result is clamped to [0, 10].
"""

import os
import pickle
import numpy as np
import pandas as pd

from src.scenarios.interventions import INTERVENTIONS
from src.scoring.severity import compute_severity

_MODEL_PATH    = os.path.join('outputs', 'hs_predictor.pkl')
_FEATURES_CSV  = os.path.join('outputs', 'ml_school_features.csv')
_HS_SCORES_CSV = os.path.join('outputs', 'hs_scores.csv')

HS_CODES = ['HS1', 'HS2', 'HS3', 'HS4', 'HS5', 'HS6', 'HS7', 'HS8', 'HS9', 'HS10']


def _load_model():
    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"Trained model not found at {_MODEL_PATH}\n"
            "Run  python ml_model.py  first."
        )
    return pickle.load(open(_MODEL_PATH, 'rb'))


def _load_features(school: str) -> pd.Series:
    if not os.path.exists(_FEATURES_CSV):
        raise FileNotFoundError(
            f"Feature matrix not found at {_FEATURES_CSV}\n"
            "Run  python feature_engineering.py  first."
        )
    df = pd.read_csv(_FEATURES_CSV)
    row = df[df['school'] == school]
    if row.empty:
        available = df['school'].tolist()
        raise ValueError(
            f"School '{school}' not found in feature matrix.\n"
            f"Available: {available}"
        )
    return row.iloc[0]


def _load_actual_scores(school: str) -> dict:
    if not os.path.exists(_HS_SCORES_CSV):
        raise FileNotFoundError(
            f"HS scores not found at {_HS_SCORES_CSV}\n"
            "Run  python main.py  first."
        )
    df = pd.read_csv(_HS_SCORES_CSV)
    # match on short name or full name
    row = df[df['School_short'] == school]
    if row.empty:
        row = df[df['School'] == school]
    if row.empty:
        available = df['School_short'].tolist()
        raise ValueError(
            f"School '{school}' not found in hs_scores.csv.\n"
            f"Available: {available}"
        )
    return row.iloc[0][HS_CODES + ['HS_overall']].to_dict()


def run_scenario(
    school: str,
    intervention_keys: list,
    model_path: str  = _MODEL_PATH,
    features_csv: str = _FEATURES_CSV,
    hs_scores_csv: str = _HS_SCORES_CSV,
) -> dict:
    """
    Run a what-if scenario for a school.

    Parameters
    ----------
    school            : short school name  (e.g. 'Preston HS')
    intervention_keys : list of keys from INTERVENTIONS
                        (e.g. ['pedestrian_crossing', 'speed_reduction'])

    Returns
    -------
    dict with keys:
        school          : str
        interventions   : list of applied intervention labels
        baseline        : dict  HS1–HS10 + HS_overall + severity (actual scores)
        scenario        : dict  HS1–HS10 + HS_overall + severity (predicted)
        deltas          : dict  HS1–HS10 + HS_overall (scenario − baseline)
        feature_changes : dict  feature → (before, after)
        cost_summary    : list  of (label, cost, timeframe) tuples
    """
    # Validate interventions
    bad = [k for k in intervention_keys if k not in INTERVENTIONS]
    if bad:
        raise ValueError(f"Unknown interventions: {bad}. "
                         f"Available: {list(INTERVENTIONS.keys())}")

    bundle = _load_model()
    pipe         = bundle['model']
    feature_cols = bundle['features']

    feat_row = _load_features(school)
    actual   = _load_actual_scores(school)

    # Build baseline feature vector (in model's expected column order)
    X_baseline = pd.DataFrame([feat_row[feature_cols].values],
                               columns=feature_cols).astype(float)

    # Apply deltas to build scenario feature vector
    X_scenario = X_baseline.copy()
    feature_changes = {}

    for key in intervention_keys:
        iv = INTERVENTIONS[key]
        for feat, delta in iv['deltas'].items():
            if feat not in X_scenario.columns:
                continue
            before = float(X_scenario[feat].iloc[0])
            after  = float(np.clip(before + delta,
                                   0,
                                   before * 3 + abs(delta) * 2))
            X_scenario[feat] = after
            # Keep track of the largest change per feature across all interventions
            if feat not in feature_changes or abs(after - before) > abs(feature_changes[feat][1] - feature_changes[feat][0]):
                feature_changes[feat] = (before, after)

    # Model predictions (delta method)
    pred_baseline = pipe.predict(X_baseline)[0]   # shape (10,)
    pred_scenario = pipe.predict(X_scenario)[0]
    model_delta   = pred_scenario - pred_baseline  # predicted HS change

    # Apply delta to actual scores
    scenario_hs = {}
    delta_hs    = {}
    for i, code in enumerate(HS_CODES):
        base_val = float(actual[code])
        new_val  = float(np.clip(base_val + model_delta[i], 0.0, 10.0))
        scenario_hs[code] = round(new_val, 2)
        delta_hs[code]    = round(new_val - base_val, 2)

    # Overall scores
    baseline_overall = round(float(actual['HS_overall']), 2)
    scenario_overall = round(float(np.mean(list(scenario_hs.values()))), 2)
    delta_overall    = round(scenario_overall - baseline_overall, 2)

    # Severity
    baseline_row = {**{c: float(actual[c]) for c in HS_CODES},
                    'HS_overall': baseline_overall}
    scenario_row = {**scenario_hs, 'HS_overall': scenario_overall}

    baseline_sev = compute_severity(baseline_row)
    scenario_sev = compute_severity(scenario_row)

    cost_summary = [
        (INTERVENTIONS[k]['label'],
         INTERVENTIONS[k]['cost'],
         INTERVENTIONS[k]['timeframe'])
        for k in intervention_keys
    ]

    return {
        'school'         : school,
        'interventions'  : [INTERVENTIONS[k]['label'] for k in intervention_keys],
        'baseline'       : {**{c: round(float(actual[c]), 2) for c in HS_CODES},
                             'HS_overall': baseline_overall,
                             'severity'  : baseline_sev},
        'scenario'       : {**scenario_hs,
                             'HS_overall': scenario_overall,
                             'severity'  : scenario_sev},
        'deltas'         : {**delta_hs, 'HS_overall': delta_overall},
        'feature_changes': feature_changes,
        'cost_summary'   : cost_summary,
    }
