"""
HS1 — Pedestrians from all walks of life.
Scores footpath accessibility and inclusivity (0–10).
Reference: Healthy Streets framework (Lucy Saunders / TfL).
"""


def compute_hs1(row) -> float:
    pts = 0.0

    p = str(row.get('Footpath_present', ''))
    if   'both sides' in p:                                   pts += 3.0
    elif 'one side'   in p:                                   pts += 2.0
    elif 'partial'    in p.lower() or 'broken' in p.lower(): pts += 1.0

    try:
        w = float(row['Footpath_width'])
        if   w >= 2.0: pts += 2.0
        elif w >= 1.5: pts += 1.5
        elif w >= 1.2: pts += 1.0
        elif w >= 1.0: pts += 0.5
    except (ValueError, TypeError):
        pass

    c = str(row.get('Continuity', ''))
    if   '100%'     in c: pts += 2.0
    elif '75 to 99' in c: pts += 1.5
    elif '50 to 74' in c: pts += 1.0

    try:
        pts += (float(row['FP_condition']) / 5.0) * 2.0
    except (ValueError, TypeError):
        pass

    k = str(row.get('Kerb_ramps', ''))
    if   'all nearby' in k.lower(): pts += 0.5
    elif 'some'       in k.lower(): pts += 0.25

    o = str(row.get('Obstructions', ''))
    if   'no obstruction' in o.lower(): pts += 0.5
    elif 'minor'          in o.lower(): pts += 0.25

    return min(round(pts, 1), 10.0)
