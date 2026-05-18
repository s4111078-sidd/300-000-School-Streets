"""
HS10 — Clean air.
Scores AQI (PM2.5) adjusted for arterial road exposure (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""
import numpy as np
import pandas as pd


def compute_hs10(row, ev: dict, sp: dict) -> float:
    aqi = ev.get('aqi_pm25', np.nan)
    if pd.notna(aqi):
        if   aqi <= 12:  pts = 10.0   # US EPA AQI Good
        elif aqi <= 35:  pts = 7.0    # Moderate
        elif aqi <= 55:  pts = 5.0    # Unhealthy for sensitive groups
        elif aqi <= 150: pts = 2.0    # Unhealthy
        else:            pts = 0.0
    else:
        pts = 6.0   # assume moderate if no data

    art_pct = sp.get('arterial_pct_400m', np.nan) if sp else np.nan
    if pd.notna(art_pct):
        if   art_pct >= 40: pts -= 2.0
        elif art_pct >= 25: pts -= 1.0

    return min(max(round(pts, 1), 0.0), 10.0)
