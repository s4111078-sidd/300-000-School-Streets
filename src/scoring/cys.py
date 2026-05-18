"""
CYS — Cycling safety score (0–10), derived from OSM spatial features.

Used by src/features/engineer.py as a standalone signal in the ML feature
matrix. The same logic is embedded inside compute_hs6() for the HS scoring
pipeline — this module avoids duplication by exposing it independently.
"""
import numpy as np
import pandas as pd


def compute_cys(row: dict) -> float:
    """
    Compute a cycling safety score (0–10) from a spatial_features row.

    Args:
        row: dict with OSM-derived keys (from spatial_features.csv).

    Returns:
        float in [0, 10], or np.nan if no relevant data is present.
    """
    pct       = row.get('cycle_pct_400m', np.nan)
    protected = row.get('protected_cycle_length_400m', np.nan)
    signals   = row.get('signals_400m', np.nan)
    density   = row.get('crossing_density_400m', np.nan)
    avg_spd   = row.get('avg_speed_400m', np.nan)

    has_data = any(pd.notna(v) for v in [pct, protected, signals, density, avg_spd])
    if not has_data:
        return np.nan

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

    return round(min(cys, 10.0), 1)
