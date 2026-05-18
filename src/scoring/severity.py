"""
HS-based severity classification.
Derives Major / Moderate / Minor from HS indicator scores.

Thresholds align with the Healthy Streets framework where 6.0 is the
"good" threshold — any indicator below 6.0 signals a deficiency.
"""
import pandas as pd

_ALL_CODES = ['HS1', 'HS2', 'HS3', 'HS4', 'HS5', 'HS6', 'HS7', 'HS8', 'HS9', 'HS10']


def compute_severity(row) -> str:
    hs1     = row.get('HS1')
    hs2     = row.get('HS2')
    hs5     = row.get('HS5')
    overall = row.get('HS_overall')

    # Major: any critical safety indicator in crisis range
    if pd.notna(hs2) and hs2 < 3.0: return 'Major'
    if pd.notna(hs1) and hs1 < 3.0: return 'Major'
    if pd.notna(hs5) and hs5 < 2.0: return 'Major'

    # Moderate: 2+ indicators below the HS "good" threshold (6.0)
    all_vals = [row.get(c) for c in _ALL_CODES]
    low = sum(1 for v in all_vals if pd.notna(v) and v < 6.0)
    if low >= 2: return 'Moderate'
    if pd.notna(overall) and overall < 5.0: return 'Moderate'

    return 'Minor'
