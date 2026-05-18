"""
HS7 — People feel safe.
Scores street lighting quality and local crime rate (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd


def compute_hs7(row, ev: dict) -> float:
    pts = 0.0

    lit = str(row.get('Lighting', '')).lower()
    if   'good' in lit or 'well lit' in lit: pts += 4.0
    elif 'adequate' in lit:                  pts += 2.5
    elif 'poor' in lit or 'dim' in lit:      pts += 1.0

    hazards = str(row.get('Hazard_types', '')).lower()
    if 'personal safety' not in hazards and 'crime' not in hazards:
        pts += 2.0

    crime_rate = ev.get('crime_rate_per_100k', np.nan)
    if pd.notna(crime_rate):
        if   crime_rate <= 300:  pts += 4.0
        elif crime_rate <= 600:  pts += 3.0
        elif crime_rate <= 900:  pts += 2.0
        elif crime_rate <= 1200: pts += 1.0

    return min(round(pts, 1), 10.0)
