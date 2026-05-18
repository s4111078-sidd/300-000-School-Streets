"""
HS3 — Shade and shelter.
Scores trees, canopy, bus shelters, green space (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd


def compute_hs3(row, sp: dict) -> float:
    pts = 0.0

    tree_count = sp.get('tree_count_100m', np.nan)
    if pd.notna(tree_count):
        if   tree_count >= 15: pts += 5.0
        elif tree_count >= 8:  pts += 3.5
        elif tree_count >= 3:  pts += 2.0
        elif tree_count >= 1:  pts += 1.0

    shelter_count = sp.get('shelter_count_200m', np.nan)
    if pd.notna(shelter_count) and shelter_count > 0:
        pts += 2.0

    green_pct = sp.get('green_pct_400m', np.nan)
    if pd.notna(green_pct):
        if   green_pct >= 20: pts += 3.0
        elif green_pct >= 10: pts += 2.0
        elif green_pct >= 5:  pts += 1.0

    return min(round(pts, 1), 10.0) if pts > 0 else np.nan
