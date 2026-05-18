"""
HS6 — People choose to walk, cycle and use PT.
Combines cycling infrastructure level (CIS), cycling safety (CYS from OSM),
and PT stop access (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd

from config import CIS_MAP


def _cis(val) -> float:
    if pd.isna(val):
        return np.nan
    v = str(val).strip()
    for key, score in CIS_MAP.items():
        if key.lower() in v.lower():
            return score
    return 1.0 if 'no cycling' in v.lower() else 2.0


def compute_hs6(row, sp: dict) -> float:
    cis = _cis(row.get('Cycling_infra'))

    cys = np.nan
    if sp:
        pct       = sp.get('cycle_pct_400m', np.nan)
        protected = sp.get('protected_cycle_length_400m', np.nan)
        signals   = sp.get('signals_400m', np.nan)
        density   = sp.get('crossing_density_400m', np.nan)
        avg_spd   = sp.get('avg_speed_400m', np.nan)
        cys = 0.0
        if pd.notna(pct):
            if   pct >= 40: cys += 4
            elif pct >= 25: cys += 3
            elif pct >= 15: cys += 2
            elif pct >= 5:  cys += 1
        if pd.notna(protected):
            if   protected >= 300: cys += 3
            elif protected >= 100: cys += 2
            elif protected > 0:    cys += 1
        if pd.notna(signals) and signals >= 3:   cys += 1
        if pd.notna(density) and density >= 1.0: cys += 1
        if pd.notna(avg_spd) and avg_spd <= 40:  cys += 1
        cys = round(min(cys, 10.0), 1)

    pt_score = np.nan
    pt_stops = sp.get('pt_stops_400m', np.nan) if sp else np.nan
    if pd.notna(pt_stops):
        pt_score = min(pt_stops / 5.0 * 10.0, 10.0)

    parts, weights = [], []
    if pd.notna(cis):      parts.append(cis * 0.35);      weights.append(0.35)
    if pd.notna(cys):      parts.append(cys * 0.45);      weights.append(0.45)
    if pd.notna(pt_score): parts.append(pt_score * 0.20); weights.append(0.20)
    if not parts:
        return np.nan
    return round(sum(parts) / sum(weights), 1)
