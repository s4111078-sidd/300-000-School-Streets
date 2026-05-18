"""
HS9 — People feel relaxed.
Scores traffic calming, school zone, lane count, parking conflicts (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""


def compute_hs9(row) -> float:
    pts = 0.0

    tc = str(row.get('Traffic_calming', '')).lower()
    if 'no traffic calming' not in tc and tc not in ('', 'nan'):
        pts += 2.0

    sz = str(row.get('School_zone', '')).lower()
    if   'enforced' in sz:                            pts += 2.0
    elif 'present'  in sz and 'no school' not in sz: pts += 1.0

    pc = str(row.get('Parking_conflict', '')).lower()
    if 'no parking' in pc:
        pts += 2.0

    l = str(row.get('Lanes', '')).lower()
    if   '1 lane'  in l: pts += 2.0
    elif '2 lanes' in l: pts += 1.0

    try:
        pts += (float(row.get('FP_condition', 3)) / 5.0) * 2.0
    except (ValueError, TypeError):
        pts += 1.0

    return min(round(pts, 1), 10.0)
