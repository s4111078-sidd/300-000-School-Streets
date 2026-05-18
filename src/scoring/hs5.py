"""
HS5 — Not too noisy.
Scores traffic volume, speed, heavy vehicles, lane count (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""


def compute_hs5(row) -> float:
    pts = 10.0

    v = str(row.get('Traffic_volume', '')).lower()
    if   'very high' in v or 'major arterial' in v: pts -= 4.0
    elif 'high'      in v:                          pts -= 3.0
    elif 'moderate'  in v:                          pts -= 1.5

    try:
        speed = float(''.join(c for c in str(row.get('Speed_limit', '')) if c.isdigit()) or '50')
        if   speed >= 70: pts -= 2.0
        elif speed >= 60: pts -= 1.0
        elif speed >= 50: pts -= 0.5
    except (ValueError, TypeError):
        pass

    h = str(row.get('Heavy_vehicles', '')).lower()
    if   'frequent'  in h: pts -= 2.0
    elif 'occasion'  in h: pts -= 1.0

    l = str(row.get('Lanes', '')).lower()
    if   '3 or more' in l: pts -= 1.0
    elif '2 lanes'   in l: pts -= 0.5

    return min(max(round(pts, 1), 0.0), 10.0)
