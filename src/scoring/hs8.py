"""
HS8 — Things to see and do.
Scores OSM amenities, parks, cafes within 400m (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd


def compute_hs8(row, sp: dict) -> float:
    pts = 0.0

    amenity_count = sp.get('amenity_count_400m', np.nan)
    if pd.notna(amenity_count):
        if   amenity_count >= 30: pts += 4.0
        elif amenity_count >= 15: pts += 3.0
        elif amenity_count >= 5:  pts += 2.0
        elif amenity_count >= 1:  pts += 1.0

    park_count = sp.get('park_count_400m', np.nan)
    if pd.notna(park_count):
        if   park_count >= 3: pts += 3.0
        elif park_count >= 1: pts += 2.0

    cafe_count = sp.get('cafe_count_400m', np.nan)
    if pd.notna(cafe_count):
        pts += min(cafe_count * 0.3, 3.0)

    return min(round(pts, 1), 10.0) if pts > 0 else np.nan
