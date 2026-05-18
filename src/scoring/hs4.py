"""
HS4 — Places to stop and rest.
Scores benches, shelters, parks within 400m (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd


def compute_hs4(row, sp: dict) -> float:
    pts = 0.0

    bench_count = sp.get('bench_count_200m', np.nan)
    if pd.notna(bench_count):
        if   bench_count >= 5: pts += 4.0
        elif bench_count >= 3: pts += 3.0
        elif bench_count >= 1: pts += 2.0

    shelter_count = sp.get('shelter_count_200m', np.nan)
    if pd.notna(shelter_count) and shelter_count > 0:
        pts += 2.0

    park_count = sp.get('park_count_400m', np.nan)
    if pd.notna(park_count):
        if   park_count >= 3: pts += 3.0
        elif park_count >= 1: pts += 1.5

    cafe_count = sp.get('cafe_count_400m', np.nan)
    if pd.notna(cafe_count) and cafe_count > 0:
        pts += min(cafe_count * 0.3, 1.0)

    return min(round(pts, 1), 10.0) if pts > 0 else np.nan
