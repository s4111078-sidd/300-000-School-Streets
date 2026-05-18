"""
HS-based severity classification.
Derives Major / Moderate / Minor from HS indicator scores.
"""
import pandas as pd


def compute_severity(row) -> str:
    hs1, hs2, hs5, hs9 = row.get('HS1'), row.get('HS2'), row.get('HS5'), row.get('HS9')
    overall = row.get('HS_overall')

    if pd.notna(hs2) and hs2 < 3.0: return 'Major'
    if pd.notna(hs1) and hs1 < 3.0: return 'Major'
    if pd.notna(hs5) and hs5 < 2.0: return 'Major'

    low = sum(1 for v in [hs1, hs2, hs5, hs9] if pd.notna(v) and v < 5.0)
    if low >= 2: return 'Moderate'
    if pd.notna(overall) and overall < 5.0: return 'Moderate'
    if pd.notna(hs2) and hs2 < 5.0: return 'Moderate'

    return 'Minor'
