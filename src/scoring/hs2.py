"""
HS2 — Easy to cross.
Scores crossing quality, distance, visibility, and signals (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""


def compute_hs2(row) -> float:
    pts = 0.0

    ct = str(row.get('Crossing_present', ''))
    if   'signal' in ct.lower() or 'traffic light' in ct.lower(): pts += 4.0
    elif 'raised' in ct.lower():                                   pts += 3.0
    elif 'zebra'  in ct.lower() or 'marked' in ct.lower():        pts += 2.5
    elif 'refuge' in ct.lower():                                   pts += 2.0
    elif 'informal' in ct.lower() or 'unmarked' in ct.lower():    pts += 0.5

    try:
        d = float(row['Crossing_dist'])
        if   d <=  30: pts += 2.0
        elif d <=  75: pts += 1.5
        elif d <= 150: pts += 1.0
        elif d <= 250: pts += 0.5
    except (ValueError, TypeError):
        pass

    try:
        pts += (float(row['Visibility']) / 5.0) * 2.0
    except (ValueError, TypeError):
        pass

    t = str(row.get('Tactile', ''))
    if   'both sides' in t.lower(): pts += 1.0
    elif 'one side'   in t.lower(): pts += 0.5

    s = str(row.get('Signal', ''))
    if 'countdown' in s.lower():
        pts += 1.0
    elif 'yes' in s.lower() and 'no pedestrian' not in s.lower() and 'not applicable' not in s.lower():
        pts += 0.5

    return min(round(pts, 1), 10.0)
