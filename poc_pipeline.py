import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
import folium
from folium.plugins import HeatMap
import os
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
CSV_FILE    = 'school_data.csv'
OUT_DIR     = 'outputs'
SPATIAL_CSV = os.path.join(OUT_DIR, 'spatial_features.csv')
ENV_CSV     = os.path.join(OUT_DIR, 'environmental_features.csv')
os.makedirs(OUT_DIR, exist_ok=True)

# 10 Healthy Streets indicators (Lucy Saunders / TfL framework)
HS_INDICATORS = [
    ('HS1',  'Pedestrians from\nall walks of life'),
    ('HS2',  'Easy to\ncross'),
    ('HS3',  'Shade and\nshelter'),
    ('HS4',  'Places to stop\nand rest'),
    ('HS5',  'Not too\nnoisy'),
    ('HS6',  'People choose to\nwalk / cycle / PT'),
    ('HS7',  'People\nfeel safe'),
    ('HS8',  'Things to\nsee and do'),
    ('HS9',  'People\nfeel relaxed'),
    ('HS10', 'Clean\nair'),
]
HS_CODES  = [h[0] for h in HS_INDICATORS]
HS_LABELS = [h[1] for h in HS_INDICATORS]

# ══════════════════════════════════════════════════════════
# STEP 1 — LOAD AND CLEAN
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  300,000 Streets — Healthy Streets Pipeline")
print("="*60)
print("\n[1/7] Loading and cleaning data...")

df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()

df = df.rename(columns={
    'School name'                                                    : 'School',
    'Overall hazard severity at this location'                       : 'Severity',
    'Footpath Accessibility Score — FAS (0 to 10)'             : 'FAS',
    'Crossing Safety Score — CSS (0 to 10)'                    : 'CSS',
    'Environmental Exposure Indicator — EEI (0 to 10)'         : 'EEI',
    'Street or location being assessed'                              : 'Street',
    'Latitude (decimal degrees)'                                     : 'Latitude',
    'Longitude (decimal degrees)'                                    : 'Longitude',
    'Approximate distance from school gate (metres)'                 : 'Distance_gate',
    'Footpath present?'                                              : 'Footpath_present',
    'Footpath width (metres)'                                        : 'Footpath_width',
    'Footpath continuity along this segment'                         : 'Continuity',
    'Footpath condition rating'                                      : 'FP_condition',
    'Kerb ramps present at intersections?'                           : 'Kerb_ramps',
    'Obstructions on footpath?'                                      : 'Obstructions',
    'Pedestrian crossing present at this location?'                  : 'Crossing_present',
    'Distance of nearest crossing from school gate (metres)'         : 'Crossing_dist',
    'Crossing visibility rating'                                     : 'Visibility',
    'Crossing condition / maintenance rating'                        : 'Cross_condition',
    'Tactile ground surface indicators (yellow bumps)?'              : 'Tactile',
    'Pedestrian signal or countdown timer?'                          : 'Signal',
    'Posted speed limit (km/h)'                                      : 'Speed_limit',
    'School zone active at this location?'                           : 'School_zone',
    'Number of traffic lanes'                                        : 'Lanes',
    'Estimated traffic volume during school hours'                   : 'Traffic_volume',
    'Heavy vehicles or trucks present?'                              : 'Heavy_vehicles',
    'Traffic calming measures present?'                              : 'Traffic_calming',
    'On-street parking conflicts with pedestrians?'                  : 'Parking_conflict',
    'Street lighting quality'                                        : 'Lighting',
    'Cycling infrastructure present?'                                : 'Cycling_infra',
    'Hazard types observed at this location (select all that apply)' : 'Hazard_types',
    'Detailed hazard description'                                    : 'Hazard_desc',
    'Recommended intervention type'                                  : 'Rec_type',
    'Recommendation priority level'                                  : 'Priority',
    'Estimated cost level'                                           : 'Cost_level',
    'Suggested implementation timeframe'                             : 'Timeframe',
    'Detailed intervention description'                              : 'Rec_desc',
    'Expected benefit of this intervention'                          : 'Benefit',
    'Primary data source used for this observation'                  : 'Data_source',
    'Google Street View image date (if used)'                        : 'SV_date',
})

df['School_short'] = df['School'].map({
    'Reservoir High School'            : 'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School'              : 'Preston HS',
}).fillna(df['School'])

def _clean_sev(s):
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'

df['Sev_obs'] = df['Severity'].apply(_clean_sev)
print(f"      Loaded {len(df)} rows  |  Schools: {df['School'].unique().tolist()}")

# ══════════════════════════════════════════════════════════
# STEP 2 — LOAD SUPPLEMENTARY DATA
# ══════════════════════════════════════════════════════════
print("\n[2/7] Loading supplementary data...")

# ── Spatial features (OSM-derived, from spatial_features.py) ──
_sf = None
_school_map = {
    'Reservoir High School'            : 'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School'              : 'Preston HS',
}
if os.path.exists(SPATIAL_CSV):
    _sf = pd.read_csv(SPATIAL_CSV).set_index('school_name')
    print(f"      Spatial features loaded  ({len(_sf)} schools, {len(_sf.columns)} columns)")
else:
    print("      (spatial_features.csv not found — HS3/HS4/HS6/HS8 will be NaN)")

def _spatial(school_full):
    if _sf is None:
        return {}
    short = _school_map.get(school_full, school_full)
    if short in _sf.index:
        return _sf.loc[short].to_dict()
    if school_full in _sf.index:
        return _sf.loc[school_full].to_dict()
    return {}

# ── Environmental features (AQI + crime, from environmental_features.py) ──
_ef = None
if os.path.exists(ENV_CSV):
    _ef = pd.read_csv(ENV_CSV).set_index('school_name')
    print(f"      Environmental features loaded  ({len(_ef)} schools)")
else:
    print("      (environmental_features.csv not found — run environmental_features.py for AQI/crime)")
    print("      Using suburb-level fallback values for HS7 / HS10")

# Fallback suburb-level AQI and crime (Crime Statistics Victoria 2023-24; EPA AirWatch Alphington)
_ENV_FALLBACK = {
    'Reservoir High School':             {'aqi_pm25': 8.2,  'crime_rate_per_100k': 850},
    'William Ruthven Secondary College': {'aqi_pm25': 7.1,  'crime_rate_per_100k': 580},
    'Preston High School':               {'aqi_pm25': 7.8,  'crime_rate_per_100k': 720},
}

def _env(school_full):
    if _ef is not None:
        short = _school_map.get(school_full, school_full)
        if short in _ef.index:
            return _ef.loc[short].to_dict()
        if school_full in _ef.index:
            return _ef.loc[school_full].to_dict()
    return _ENV_FALLBACK.get(school_full, {})

# ── CIS — Level of Traffic Stress cycling infrastructure ──
CIS_MAP = {
    'Yes — separated bike lane':         9.0,
    'Yes — shared path or greenway':     8.0,
    'Yes — painted bike lane (on-road)': 4.5,
    'Yes — advisory lane / shared road': 2.0,
    'No cycling infrastructure':         1.0,
}

def _cis(val):
    if pd.isna(val):
        return np.nan
    v = str(val).strip()
    for key, score in CIS_MAP.items():
        if key.lower() in v.lower():
            return score
    return 1.0 if 'no cycling' in v.lower() else 2.0

# ══════════════════════════════════════════════════════════
# HEALTHY STREETS INDICATOR SCORING FUNCTIONS
# ══════════════════════════════════════════════════════════

def _hs1_pedestrians(row):
    """Pedestrians from all walks of life — footpath accessibility & inclusivity."""
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
    except (ValueError, TypeError): pass
    c = str(row.get('Continuity', ''))
    if   '100%'     in c: pts += 2.0
    elif '75 to 99' in c: pts += 1.5
    elif '50 to 74' in c: pts += 1.0
    try:
        pts += (float(row['FP_condition']) / 5.0) * 2.0
    except (ValueError, TypeError): pass
    k = str(row.get('Kerb_ramps', ''))
    if   'all nearby' in k.lower(): pts += 0.5
    elif 'some'       in k.lower(): pts += 0.25
    o = str(row.get('Obstructions', ''))
    if   'no obstruction' in o.lower(): pts += 0.5
    elif 'minor'          in o.lower(): pts += 0.25
    return min(round(pts, 1), 10.0)


def _hs2_easy_to_cross(row):
    """Easy to cross — crossing quality, distance, visibility, signals."""
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
    except (ValueError, TypeError): pass
    try:
        pts += (float(row['Visibility']) / 5.0) * 2.0
    except (ValueError, TypeError): pass
    t = str(row.get('Tactile', ''))
    if   'both sides' in t.lower(): pts += 1.0
    elif 'one side'   in t.lower(): pts += 0.5
    s = str(row.get('Signal', ''))
    if 'countdown' in s.lower(): pts += 1.0
    elif 'yes' in s.lower() and 'no pedestrian' not in s.lower() and 'not applicable' not in s.lower():
        pts += 0.5
    return min(round(pts, 1), 10.0)


def _hs3_shade_shelter(row, sp):
    """Shade and shelter — trees, canopy, bus shelters, green space."""
    pts = 0.0
    tree_count = sp.get('tree_count_100m', np.nan)
    if pd.notna(tree_count):
        if   tree_count >= 15: pts += 5.0
        elif tree_count >= 8:  pts += 3.5
        elif tree_count >= 3:  pts += 2.0
        elif tree_count >= 1:  pts += 1.0
    shelter_count = sp.get('shelter_count_200m', np.nan)
    if pd.notna(shelter_count) and shelter_count > 0:
        pts += 2.0
    green_pct = sp.get('green_pct_400m', np.nan)
    if pd.notna(green_pct):
        if   green_pct >= 20: pts += 3.0
        elif green_pct >= 10: pts += 2.0
        elif green_pct >= 5:  pts += 1.0
    return min(round(pts, 1), 10.0) if pts > 0 else np.nan


def _hs4_rest(row, sp):
    """Places to stop and rest — benches, shelters, parks."""
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


def _hs5_not_noisy(row):
    """Not too noisy — traffic volume, speed, heavy vehicles, lanes."""
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
    except (ValueError, TypeError): pass
    h = str(row.get('Heavy_vehicles', '')).lower()
    if   'frequent' in h: pts -= 2.0
    elif 'occasion' in h: pts -= 1.0
    l = str(row.get('Lanes', '')).lower()
    if   '3 or more' in l: pts -= 1.0
    elif '2 lanes'   in l: pts -= 0.5
    return min(max(round(pts, 1), 0.0), 10.0)


def _hs6_active_travel(row, sp):
    """People choose to walk, cycle and use PT — CIS, CYS, PT stop access."""
    cis = _cis(row.get('Cycling_infra'))
    # CYS from spatial features
    cys = np.nan
    if sp:
        pct       = sp.get('cycle_pct_400m', np.nan)
        protected = sp.get('protected_cycle_length_400m', np.nan)
        signals   = sp.get('signals_400m', np.nan)
        density   = sp.get('crossing_density_400m', np.nan)
        avg_spd   = sp.get('avg_speed_400m', np.nan)
        cys = 0.0
        if pd.notna(pct):
            if   pct >= 40: cys += 4
            elif pct >= 25: cys += 3
            elif pct >= 15: cys += 2
            elif pct >= 5:  cys += 1
        if pd.notna(protected):
            if   protected >= 300: cys += 3
            elif protected >= 100: cys += 2
            elif protected > 0:    cys += 1
        if pd.notna(signals) and signals >= 3:   cys += 1
        if pd.notna(density) and density >= 1.0: cys += 1
        if pd.notna(avg_spd) and avg_spd <= 40:  cys += 1
        cys = round(min(cys, 10.0), 1)
    # PT stop access
    pt_score = np.nan
    pt_stops = sp.get('pt_stops_400m', np.nan)
    if pd.notna(pt_stops):
        pt_score = min(pt_stops / 5.0 * 10.0, 10.0)

    parts, weights = [], []
    if pd.notna(cis):    parts.append(cis * 0.35);    weights.append(0.35)
    if pd.notna(cys):    parts.append(cys * 0.45);    weights.append(0.45)
    if pd.notna(pt_score): parts.append(pt_score * 0.20); weights.append(0.20)
    if not parts:
        return np.nan
    return round(sum(parts) / sum(weights), 1)


def _hs7_feel_safe(row, ev):
    """People feel safe — lighting quality + crime rate."""
    pts = 0.0
    # Lighting (0–4 pts)
    lit = str(row.get('Lighting', '')).lower()
    if   'good' in lit or 'well lit' in lit: pts += 4.0
    elif 'adequate' in lit:                  pts += 2.5
    elif 'poor' in lit or 'dim' in lit:      pts += 1.0
    # Personal safety hazard noted (0–2 pts)
    hazards = str(row.get('Hazard_types', '')).lower()
    if 'personal safety' not in hazards and 'crime' not in hazards:
        pts += 2.0
    # Crime rate (0–4 pts)
    crime_rate = ev.get('crime_rate_per_100k', np.nan)
    if pd.notna(crime_rate):
        if   crime_rate <= 300:  pts += 4.0
        elif crime_rate <= 600:  pts += 3.0
        elif crime_rate <= 900:  pts += 2.0
        elif crime_rate <= 1200: pts += 1.0
    return min(round(pts, 1), 10.0)


def _hs8_things_to_do(row, sp):
    """Things to see and do — amenities, parks, cafes within 400m."""
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


def _hs9_feel_relaxed(row):
    """People feel relaxed — traffic calming, school zone, low lanes, no parking conflict."""
    pts = 0.0
    # Traffic calming (0–2)
    tc = str(row.get('Traffic_calming', '')).lower()
    if 'no traffic calming' not in tc and tc not in ('', 'nan'):
        pts += 2.0
    # School zone (0–2)
    sz = str(row.get('School_zone', '')).lower()
    if   'enforced' in sz:                           pts += 2.0
    elif 'present'  in sz and 'no school' not in sz: pts += 1.0
    # Parking conflicts (0–2)
    pc = str(row.get('Parking_conflict', '')).lower()
    if 'no parking' in pc:
        pts += 2.0
    # Lane count (0–2)
    l = str(row.get('Lanes', '')).lower()
    if   '1 lane'    in l: pts += 2.0
    elif '2 lanes'   in l: pts += 1.0
    # Footpath condition proxy (0–2)
    try:
        pts += (float(row.get('FP_condition', 3)) / 5.0) * 2.0
    except (ValueError, TypeError):
        pts += 1.0
    return min(round(pts, 1), 10.0)


def _hs10_clean_air(row, ev, sp):
    """Clean air — AQI score adjusted for arterial road exposure."""
    aqi = ev.get('aqi_pm25', np.nan)
    if pd.notna(aqi):
        if   aqi <= 12:  pts = 10.0   # Good (US EPA AQI Good)
        elif aqi <= 35:  pts = 7.0    # Moderate
        elif aqi <= 55:  pts = 5.0    # Unhealthy for sensitive groups
        elif aqi <= 150: pts = 2.0    # Unhealthy
        else:            pts = 0.0
    else:
        pts = 6.0   # assume moderate air quality if no data
    # Arterial road penalty (high traffic = more NO2/PM2.5)
    art_pct = sp.get('arterial_pct_400m', np.nan)
    if pd.notna(art_pct):
        if   art_pct >= 40: pts -= 2.0
        elif art_pct >= 25: pts -= 1.0
    return min(max(round(pts, 1), 0.0), 10.0)


# ── Severity classification based on HS indicators ────────
def _hs_severity(row):
    hs1, hs2, hs5, hs9 = row['HS1'], row['HS2'], row['HS5'], row['HS9']
    overall = row['HS_overall']
    # Major: any core pedestrian indicator critically low
    if pd.notna(hs2) and hs2 < 3.0: return 'Major'
    if pd.notna(hs1) and hs1 < 3.0: return 'Major'
    if pd.notna(hs5) and hs5 < 2.0: return 'Major'
    # Moderate: overall below threshold or two indicators below 5
    low = sum(1 for v in [hs1, hs2, hs5, hs9] if pd.notna(v) and v < 5.0)
    if low >= 2: return 'Moderate'
    if pd.notna(overall) and overall < 5.0: return 'Moderate'
    if pd.notna(hs2) and hs2 < 5.0: return 'Moderate'
    return 'Minor'


# ══════════════════════════════════════════════════════════
# STEP 3 — APPLY SCORING
# ══════════════════════════════════════════════════════════
print("\n[3/7] Computing Healthy Streets scores...")

for _, row in df.iterrows():
    sp = _spatial(row['School'])
    ev = _env(row['School'])
    df.loc[_, 'HS1']  = _hs1_pedestrians(row)
    df.loc[_, 'HS2']  = _hs2_easy_to_cross(row)
    df.loc[_, 'HS3']  = _hs3_shade_shelter(row, sp)
    df.loc[_, 'HS4']  = _hs4_rest(row, sp)
    df.loc[_, 'HS5']  = _hs5_not_noisy(row)
    df.loc[_, 'HS6']  = _hs6_active_travel(row, sp)
    df.loc[_, 'HS7']  = _hs7_feel_safe(row, ev)
    df.loc[_, 'HS8']  = _hs8_things_to_do(row, sp)
    df.loc[_, 'HS9']  = _hs9_feel_relaxed(row)
    df.loc[_, 'HS10'] = _hs10_clean_air(row, ev, sp)

df['HS_overall'] = df[HS_CODES].mean(axis=1, skipna=True).round(1)
df['Sev_clean']  = df.apply(_hs_severity, axis=1)

print("\n      HEALTHY STREETS SCORES:")
print(f"      {'School':<22} " + " ".join(f"{c:>5}" for c in HS_CODES) + f"  {'Overall':>7}  {'Severity'}")
print("      " + "─" * 110)
for _, row in df.iterrows():
    scores = " ".join(
        f"{row[c]:>5.1f}" if pd.notna(row[c]) else "  N/A" for c in HS_CODES
    )
    print(f"      {row['School_short']:<22} {scores}  {row['HS_overall']:>7.1f}  {row['Sev_clean']}")

nan_indicators = [c for c in HS_CODES if df[c].isna().all()]
if nan_indicators:
    print(f"\n      Note: {nan_indicators} are NaN — run spatial_features.py / environmental_features.py to populate")

# ══════════════════════════════════════════════════════════
# STEP 4 — CHART 1: HEALTHY STREETS RADAR CHART
# ══════════════════════════════════════════════════════════
print("\n[4/7] Generating Charts...")

SCHOOL_COLOURS = {
    'Reservoir HS':     '#1A476E',
    'William Ruthven SC': '#1A8FC1',
    'Preston HS':       '#C0392B',
}
DEFAULT_COLOURS = ['#1A476E', '#1A8FC1', '#C0392B', '#27AE60', '#8E44AD']

N = len(HS_CODES)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')

# Draw background rings
for ring in [2, 4, 6, 8, 10]:
    ax.plot(angles, [ring] * (N + 1), color='#DDDDDD', linewidth=0.6, linestyle='-', zorder=0)
    ax.text(angles[0], ring + 0.2, str(ring), ha='center', va='bottom', fontsize=7, color='#AAAAAA')

# Threshold ring at 6
ax.plot(angles, [6] * (N + 1), color='#C0392B', linewidth=1.2, linestyle='--', alpha=0.6, zorder=1)

for i, (_, row) in enumerate(df.iterrows()):
    school = row['School_short']
    colour = SCHOOL_COLOURS.get(school, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
    values = [row[c] if pd.notna(row[c]) else 0 for c in HS_CODES]
    values += values[:1]
    ax.plot(angles, values, color=colour, linewidth=2.5, zorder=3, label=school)
    ax.fill(angles, values, color=colour, alpha=0.10, zorder=2)
    # Dot at each vertex
    for ang, val, code in zip(angles[:-1], values[:-1], HS_CODES):
        if row[code] > 0:
            ax.scatter(ang, val, color=colour, s=50, zorder=4)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(HS_LABELS, size=10, fontweight='bold', color='#333333')
ax.set_ylim(0, 10)
ax.set_yticks([])
ax.spines['polar'].set_color('#CCCCCC')

# Legend
legend = ax.legend(
    loc='upper right', bbox_to_anchor=(1.35, 1.15),
    fontsize=11, framealpha=0.9,
    title='School', title_fontsize=11,
)
ax.set_title('Healthy Streets Assessment\n10-Indicator Radar Chart', fontsize=14,
             fontweight='bold', pad=24, color='#1A476E')

# Annotate threshold
ax.text(angles[1], 6.6, 'Good threshold\n(6.0)', ha='left', va='center',
        fontsize=8, color='#C0392B', style='italic')

plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=8, color='#888888')
out_radar = os.path.join(OUT_DIR, 'chart1_hs_radar.png')
plt.savefig(out_radar, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_radar}")

# ── Chart 2: HS Bar Chart — per-indicator comparison across schools ────────────
fig, axes = plt.subplots(2, 5, figsize=(18, 8), sharey=True)
fig.patch.set_facecolor('white')
axes = axes.flatten()

schools_list = df['School_short'].tolist()
x = np.arange(len(schools_list))
width = 0.55

for ax_i, (code, label) in enumerate(zip(HS_CODES, HS_LABELS)):
    ax = axes[ax_i]
    ax.set_facecolor('#FAFAFA')
    vals = [df.loc[r, code] if pd.notna(df.loc[r, code]) else 0 for r in df.index]
    bar_cols = []
    for v in vals:
        if   v >= 7.0: bar_cols.append('#27AE60')
        elif v >= 5.0: bar_cols.append('#F39C12')
        elif v > 0:    bar_cols.append('#C0392B')
        else:          bar_cols.append('#CCCCCC')
    bars = ax.bar(x, vals, width, color=bar_cols, edgecolor='white')
    for bar, v, r in zip(bars, vals, df.index):
        label_v = f'{v:.1f}' if pd.notna(df.loc[r, code]) else 'N/A'
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.15,
                label_v, ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.axhline(y=6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(schools_list, fontsize=8, rotation=15, ha='right')
    ax.set_ylim(0, 12)
    ax.set_title(f'{code}\n{label.replace(chr(10), " ")}', fontsize=9, fontweight='bold', pad=6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.5)
    ax.set_axisbelow(True)

axes[0].set_ylabel('Score  (0 = worst  |  10 = best)', fontsize=10)
axes[5].set_ylabel('Score  (0 = worst  |  10 = best)', fontsize=10)
legend_els = [
    mpatches.Patch(color='#27AE60', label='Good (≥7.0)'),
    mpatches.Patch(color='#F39C12', label='Moderate (5–6.9)'),
    mpatches.Patch(color='#C0392B', label='Poor (<5.0)'),
    mpatches.Patch(color='#CCCCCC', label='No data'),
]
fig.legend(handles=legend_els, loc='lower center', ncol=4, fontsize=9,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.02))
fig.suptitle('Healthy Streets — 10-Indicator Score Comparison by School',
             fontsize=14, fontweight='bold', y=1.01)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out_bar = os.path.join(OUT_DIR, 'chart2_hs_scores.png')
plt.savefig(out_bar, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_bar}")

# ── Chart 3: Per-school HS breakdown ──────────────────────────────────────────
n_schools = len(df)
fig, axes = plt.subplots(1, n_schools, figsize=(9 * n_schools, 7), sharey=True)
fig.patch.set_facecolor('white')
if n_schools == 1:
    axes = [axes]

short_labels = [l.replace('\n', ' ') for l in HS_LABELS]

for ax, (_, row) in zip(axes, df.iterrows()):
    school = row['School_short']
    sev    = row['Sev_clean']
    colour = SCHOOL_COLOURS.get(school, '#1A476E')
    vals, bar_cols = [], []
    for code in HS_CODES:
        v = row[code]
        vals.append(float(v) if pd.notna(v) else 0)
        if pd.isna(v):    bar_cols.append('#DDDDDD')
        elif v >= 7.0:    bar_cols.append('#27AE60')
        elif v >= 5.0:    bar_cols.append('#F39C12')
        else:             bar_cols.append('#C0392B')
    bars = ax.bar(short_labels, vals, color=bar_cols, edgecolor='white', width=0.6)
    for bar, raw, code in zip(bars, vals, HS_CODES):
        label_v = f'{raw:.1f}' if pd.notna(row[code]) else 'N/A'
        ax.text(bar.get_x() + bar.get_width() / 2, raw + 0.15,
                label_v, ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.axhline(y=6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_ylim(0, 12)
    ax.set_xticklabels(short_labels, rotation=35, ha='right', fontsize=9)
    ax.set_title(f'{school}\nHS Overall: {row["HS_overall"]:.1f}', fontsize=11, fontweight='bold')
    sev_c = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}.get(sev, '#888888')
    ax.text(0.5, 0.97, f'Severity: {sev}', transform=ax.transAxes,
            ha='center', va='top', fontsize=9, fontweight='bold', color=sev_c,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=sev_c, linewidth=1.5))
    ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

axes[0].set_ylabel('Score  (0 = worst  |  10 = best)', fontsize=11)
legend_els2 = [
    mpatches.Patch(color='#27AE60', label='Good (≥7.0)'),
    mpatches.Patch(color='#F39C12', label='Moderate (5.0–6.9)'),
    mpatches.Patch(color='#C0392B', label='Poor (<5.0)'),
    mpatches.Patch(color='#DDDDDD', label='No data yet'),
]
fig.legend(handles=legend_els2, loc='lower center', ncol=4, fontsize=9,
           framealpha=0.9, bbox_to_anchor=(0.5, -0.06))
fig.suptitle('Healthy Streets — Per-School Breakdown (10 Indicators)', fontsize=14, fontweight='bold', y=1.02)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out_breakdown = os.path.join(OUT_DIR, 'chart3_hs_breakdown.png')
plt.savefig(out_breakdown, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_breakdown}")

# ── Chart 4: Hazard Severity ───────────────────────────────────────────────────
sev_order   = ['Major', 'Moderate', 'Minor']
sev_colours = ['#C0392B', '#D35400', '#1E8449']
school_list = df['School_short'].unique()
counts      = {s: {sv: int((df[df['School_short'] == s]['Sev_clean'] == sv).sum())
                   for sv in sev_order} for s in school_list}
x2, bottoms = np.arange(len(school_list)), np.zeros(len(school_list))
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')
for sev, colour in zip(sev_order, sev_colours):
    vals = [counts[s][sev] for s in school_list]
    bars = ax.bar(x2, vals, 0.4, bottom=bottoms, color=colour, edgecolor='white', label=sev)
    for i, (bar, v) in enumerate(zip(bars, vals)):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bottoms[i] + v / 2,
                    str(v), ha='center', va='center', fontsize=13, fontweight='bold', color='white')
    bottoms += np.array(vals, dtype=float)
for i, school in enumerate(school_list):
    ax.text(x2[i], bottoms[i] + 0.05, f'Total: {sum(counts[school].values())}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_xticks(x2)
ax.set_xticklabels(school_list, fontsize=12, fontweight='bold')
ax.set_ylim(0, max(bottoms) + 1.5)
ax.set_title('Hazard Severity Count by School', fontsize=14, fontweight='bold', pad=14)
ax.legend(loc='upper right', fontsize=10, framealpha=0.8, title='HS Severity', title_fontsize=10)
ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out_sev = os.path.join(OUT_DIR, 'chart4_severity.png')
plt.savefig(out_sev, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_sev}")

# ── Chart 5: Demographics ─────────────────────────────────────────────────────
demo_file = 'demographics_darebin.csv'
try:
    demo_df = pd.read_csv(demo_file)
    suburbs = demo_df['Suburb'].tolist()
    metrics = {
        'Median Weekly\nHousehold Income ($)': demo_df['Median weekly household income ($)'].tolist(),
        '% Households\nWith No Car':           demo_df['% households no car'].tolist(),
        '% Using Public\nTransport to Work':   demo_df['% public transport to work'].tolist(),
        '% Working\nFull Time (35hrs+)':       demo_df['% working full time (35hrs+)'].tolist(),
    }
    fig, axes = plt.subplots(1, 4, figsize=(14, 5))
    fig.patch.set_facecolor('white')
    for ax, (metric, vals), colour in zip(axes, metrics.items(), ['#1A5276','#C0392B','#D35400','#1E8449']):
        bars = ax.bar(suburbs, vals, color=colour, edgecolor='white', width=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.02,
                    str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax.set_title(metric, fontsize=9, fontweight='bold', pad=8)
        ax.set_ylim(0, max(vals) * 1.3)
        ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')
    fig.suptitle('Suburb Demographics — City of Darebin  (ABS Census 2021)',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.figtext(0.99, 0.01, '300,000 Streets  |  Source: ABS Census 2021',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()
    out_demo = os.path.join(OUT_DIR, 'chart5_demographics.png')
    plt.savefig(out_demo, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"      Saved -> {out_demo}")
except FileNotFoundError:
    print("      (demographics_darebin.csv not found — skipping chart 5)")

# ══════════════════════════════════════════════════════════
# STEP 5 — HS RECOMMENDATION ENGINE
# Each rule references the HS indicator it addresses
# ══════════════════════════════════════════════════════════
print("\n[5/7] Generating Healthy Streets recommendations...")

def generate_hs_recommendations(row):
    """
    Gap-based recommendation engine aligned to the 10 Healthy Streets indicators.
    Each rule: triggered condition → intervention → HS indicator improved → expected score delta.
    """
    recs = []

    def add(indicator, hazard, recommendation, priority, cost, timeframe, delta):
        recs.append({
            'hs_indicator'  : indicator,
            'hazard'        : hazard,
            'recommendation': recommendation,
            'priority'      : priority,
            'cost'          : cost,
            'timeframe'     : timeframe,
            'expected_delta': delta,
        })

    # ── HS1: Pedestrians from all walks of life ───────────────────────
    if row['Footpath_present'] in ['No footpath at all', 'Partial or broken — gaps present']:
        add('HS1', 'Missing or broken footpath',
            'Construct continuous concrete footpath minimum 1.8m wide',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+3.0')

    try:
        if float(row['Footpath_width']) < 1.5:
            add('HS1', 'Footpath below minimum width (1.5m)',
                'Widen footpath to minimum 1.5m — AS 1428.1',
                'Medium', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+1.5')
    except (ValueError, TypeError): pass

    if 'No kerb ramps' in str(row.get('Kerb_ramps', '')):
        add('HS1', 'No kerb ramps at intersections',
            'Install kerb ramps at all intersections within 400m of school gate',
            'Medium', 'Low — under $20,000', 'Short-term — within 1 year', '+0.5')

    if 'Vegetation' in str(row.get('Hazard_types', '')):
        add('HS1', 'Vegetation blocking footpath sightlines',
            'Remove and regularly trim vegetation obstructing path and crossing visibility',
            'Medium', 'Low — under $20,000', 'Short-term — within 1 year', '+0.5')

    # ── HS2: Easy to cross ────────────────────────────────────────────
    if row['Crossing_present'] in ['No crossing at all', 'Yes — informal / unmarked only']:
        add('HS2', 'No formal pedestrian crossing present',
            'Install raised zebra crossing with tactile pavers adjacent to school gate',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+4.0')

    try:
        if float(row['Crossing_dist']) > 150:
            add('HS2', 'Nearest crossing too far from school gate (>150m)',
                'Install additional pedestrian crossing within 50m of school gate',
                'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+2.0')
    except (ValueError, TypeError): pass

    if row.get('Tactile') == 'No':
        add('HS2', 'No tactile ground surface indicators at crossing',
            'Install tactile pavers on both sides of all crossings within 400m',
            'Medium', 'Low — under $20,000', 'Short-term — within 1 year', '+1.0')

    try:
        if pd.notna(row.get('Visibility')) and float(row['Visibility']) < 3:
            add('HS2', 'Poor crossing visibility',
                'Remove sightline obstructions; install raised platform and advance warning signs',
                'Medium', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+2.0')
    except (ValueError, TypeError): pass

    # ── HS3: Shade and shelter ────────────────────────────────────────
    if pd.notna(row.get('HS3')) and row['HS3'] < 5.0:
        add('HS3', f'Low shade and shelter score (HS3 = {row["HS3"]:.1f}/10)',
            'Plant street trees at 8m spacing along school frontage; install bus shelter with seating near gate',
            'Medium', 'Medium — $20,000–$200,000', 'Medium-term — 1–2 years', '+3.0')

    # ── HS4: Places to stop and rest ─────────────────────────────────
    if pd.notna(row.get('HS4')) and row['HS4'] < 4.0:
        add('HS4', f'Insufficient seating and rest places near school gate (HS4 = {row["HS4"]:.1f}/10)',
            'Install minimum 3 benches within 200m of school gate; add bus shelter seating',
            'Low', 'Low — under $20,000', 'Short-term — within 1 year', '+3.0')

    # ── HS5: Not too noisy ────────────────────────────────────────────
    if pd.notna(row.get('HS5')) and row['HS5'] < 5.0:
        add('HS5', f'High noise environment near school gate (HS5 = {row["HS5"]:.1f}/10)',
            'Advocate for heavy vehicle restriction during school hours; install noise barrier vegetation',
            'Medium', 'Medium — $20,000–$200,000', 'Medium-term — 1–2 years', '+1.5')

    if any(speed in str(row.get('Speed_limit', '')) for speed in ['60', '70', '80']):
        add('HS5', 'Speed limit exceeds school zone standard (>40km/h)',
            'Install school zone signs with 40km/h restriction on all approaches',
            'High', 'Low — under $20,000', 'Short-term — within 1 year', '+2.0')

    # ── HS6: People choose to walk / cycle / PT ───────────────────────
    if row.get('Cycling_infra') == 'No cycling infrastructure':
        add('HS6', 'No cycling infrastructure on school frontage road',
            'Install painted bike lane or shared path along school frontage (LTS 2–3 minimum)',
            'Medium', 'Medium — $20,000–$200,000', 'Medium-term — 1–3 years', '+2.0')

    if pd.notna(row.get('HS6')) and row['HS6'] < 5.0:
        add('HS6', f'Low active travel choice score (HS6 = {row["HS6"]:.1f}/10)',
            'Upgrade cycling infrastructure to separated lanes (LTS 1); improve PT stop access within 400m',
            'Medium', 'High — over $200,000', 'Long-term — 3–5 years', '+2.5')

    # ── HS7: People feel safe ─────────────────────────────────────────
    if row.get('Lighting') in ['Poor — dim or infrequent lights', 'No street lighting']:
        add('HS7', 'Poor street lighting on walking route to school',
            'Install LED street lights at regular intervals along primary walking route',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+2.0')

    if pd.notna(row.get('HS7')) and row['HS7'] < 5.0:
        add('HS7', f'Low personal safety score (HS7 = {row["HS7"]:.1f}/10)',
            'Improve lighting, clear sightlines, and coordinate with Victoria Police on local crime prevention strategy',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+2.0')

    # ── HS8: Things to see and do ─────────────────────────────────────
    if pd.notna(row.get('HS8')) and row['HS8'] < 4.0:
        add('HS8', f'Low activity and amenity score near school gate (HS8 = {row["HS8"]:.1f}/10)',
            'Encourage street activation: add public art, community notice boards, and improve park access routes',
            'Low', 'Low — under $20,000', 'Medium-term — 1–2 years', '+1.5')

    # ── HS9: People feel relaxed ──────────────────────────────────────
    if row.get('Traffic_calming') == 'No traffic calming at all' and '3 or more' in str(row.get('Lanes', '')):
        add('HS9', 'No traffic calming on multi-lane road near school gate',
            'Install speed humps or raised intersection table near school gate',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+2.0')

    if row.get('School_zone') == 'No school zone at all':
        add('HS9', 'No school zone signage present',
            'Install school zone signs with 40km/h speed restriction and flashing lights on all approaches',
            'High', 'Low — under $20,000', 'Short-term — within 1 year', '+2.0')

    if 'parking conflicts' in str(row.get('Parking_conflict', '')).lower() and \
       'no parking' not in str(row.get('Parking_conflict', '')).lower():
        add('HS9', 'On-street parking conflicts with pedestrians at school gate',
            'Install no-stopping zone (8am–4pm school days) within 20m of gate; add kerb extension',
            'Medium', 'Low — under $20,000', 'Short-term — within 1 year', '+1.0')

    # ── HS10: Clean air ───────────────────────────────────────────────
    if pd.notna(row.get('HS10')) and row['HS10'] < 6.0:
        add('HS10', f'Below-standard air quality near school gate (HS10 = {row["HS10"]:.1f}/10)',
            'Plant dense tree buffer between road and footpath; advocate for reduced heavy vehicle access during school hours',
            'Medium', 'Medium — $20,000–$200,000', 'Medium-term — 1–3 years', '+1.5')

    if 'frequent' in str(row.get('Heavy_vehicles', '')).lower():
        add('HS10', 'Frequent heavy vehicles past school gate (diesel PM2.5 exposure)',
            'Install heavy vehicle restriction signage and physical barriers during school hours',
            'High', 'Medium — $20,000–$200,000', 'Short-term — within 1 year', '+1.0')

    return recs


all_recs = []
for _, row in df.iterrows():
    for rec in generate_hs_recommendations(row):
        all_recs.append({
            'School'          : row['School'],
            'Location'        : row['Street'],
            'HS_Overall'      : row['HS_overall'],
            'Severity'        : row['Sev_clean'],
            **{c: row[c] for c in HS_CODES},
            'HS_Indicator'    : rec['hs_indicator'],
            'Hazard'          : rec['hazard'],
            'Recommendation'  : rec['recommendation'],
            'Priority'        : rec['priority'],
            'Cost'            : rec['cost'],
            'Timeframe'       : rec['timeframe'],
            'Expected_Score_Delta': rec['expected_delta'],
        })

rec_df  = pd.DataFrame(all_recs)
rec_out = os.path.join(OUT_DIR, 'recommendations.csv')
rec_df.to_csv(rec_out, index=False)
print(f"      {len(rec_df)} recommendations generated across {rec_df['School'].nunique()} schools")
print(f"      Saved -> {rec_out}")

hs_out = os.path.join(OUT_DIR, 'hs_scores.csv')
df[['School', 'School_short', *HS_CODES, 'HS_overall']].to_csv(hs_out, index=False)
print(f"      HS scores saved  -> {hs_out}")

# ══════════════════════════════════════════════════════════
# STEP 6 — INTERACTIVE MAP (updated with HS scores)
# ══════════════════════════════════════════════════════════
print("\n[6/7] Generating Interactive Map...")

centre_lat = df['Latitude'].mean()
centre_lon = df['Longitude'].mean()
m = folium.Map(location=[centre_lat, centre_lon],
               zoom_start=14, tiles='CartoDB positron', control_scale=True)

school_gates = {
    'Reservoir High School':             {'lat': -37.7224,  'lon': 145.0294,  'addr': '855 Plenty Rd, Reservoir VIC 3073'},
    'William Ruthven Secondary College': {'lat': -37.69654, 'lon': 145.00299, 'addr': '60 Merrilands Rd, Reservoir VIC 3073'},
    'Preston High School':               {'lat': -37.7417,  'lon': 145.0071,  'addr': '2-16 Cooma St, Preston VIC 3072'},
}
folium_sev = {'Major': 'red', 'Moderate': 'orange', 'Minor': 'green', 'Unknown': 'gray'}

for name, info in school_gates.items():
    folium.Marker(
        location=[info['lat'], info['lon']],
        popup=folium.Popup(f"<b>{name}</b><br>{info['addr']}<br><i>School gate</i>", max_width=240),
        tooltip=name,
        icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
    ).add_to(m)
    for radius, colour, dash in [(400, '#333333', None), (800, '#888888', '6')]:
        folium.Circle(
            location=[info['lat'], info['lon']], radius=radius,
            color=colour, weight=1.5, fill=True, fill_opacity=0.03,
            tooltip=f'{radius}m buffer', dash_array=dash
        ).add_to(m)

for _, row in df.iterrows():
    lat, lon = row['Latitude'], row['Longitude']
    if pd.isna(lat) or pd.isna(lon):
        continue
    sev = row['Sev_clean']
    school_recs = rec_df[rec_df['School'] == row['School']]
    top_rec = school_recs.iloc[0]['Recommendation'] if len(school_recs) > 0 else 'No recommendation'
    top_ind = school_recs.iloc[0]['HS_Indicator']   if len(school_recs) > 0 else ''
    top_pri = school_recs.iloc[0]['Priority']       if len(school_recs) > 0 else ''

    hs_rows = ''.join(
        f"<b>{c}:</b> {row[c]:.1f}&nbsp;&nbsp;" if pd.notna(row[c]) else f"<b>{c}:</b> N/A&nbsp;&nbsp;"
        for c in HS_CODES[:5]
    ) + '<br>' + ''.join(
        f"<b>{c}:</b> {row[c]:.1f}&nbsp;&nbsp;" if pd.notna(row[c]) else f"<b>{c}:</b> N/A&nbsp;&nbsp;"
        for c in HS_CODES[5:]
    )

    popup_html = f"""
    <div style="font-family:Arial;font-size:12px;min-width:260px">
      <b style="font-size:13px">{row['School']}</b><br>
      <span style="color:#666">{row['Street']}</span><br>
      <hr style="margin:5px 0">
      <b>HS Overall:</b> {row['HS_overall']:.1f}/10 &nbsp;
      <b>Severity:</b> <span style="color:{folium_sev.get(sev,'gray')}">{sev}</span><br>
      <hr style="margin:5px 0">
      <span style="font-size:11px">{hs_rows}</span>
      <hr style="margin:5px 0">
      <b>Top Issue ({top_ind}):</b><br>
      <span style="font-size:11px">{top_rec}</span><br>
      <b>Priority:</b> {top_pri}
    </div>"""

    folium.CircleMarker(
        location=[lat, lon], radius=12,
        color='white', weight=2, fill=True,
        fill_color=folium_sev.get(sev, 'gray'), fill_opacity=0.9,
        popup=folium.Popup(popup_html, max_width=290),
        tooltip=f"{row['School_short']} — {row['Street']} ({sev})"
    ).add_to(m)

# ── Crash markers ─────────────────────────────────────────
crash_csv_path = os.path.join(OUT_DIR, 'crash_data_darebin.csv')
crash_df = pd.DataFrame()
lat_c = lon_c = None
if os.path.exists(crash_csv_path):
    crash_df = pd.read_csv(crash_csv_path, low_memory=False)
    crash_df.columns = crash_df.columns.str.strip()
    lat_c = next((c for c in crash_df.columns if c.upper() in ('LAT','LATITUDE','Y')), None)
    lon_c = next((c for c in crash_df.columns if c.upper() in ('LON','LONG','LONGITUDE','X')), None)
    if lat_c and lon_c:
        cnt = 0
        for _, cr in crash_df.dropna(subset=[lat_c, lon_c]).iterrows():
            folium.CircleMarker(
                location=[cr[lat_c], cr[lon_c]], radius=7,
                color='white', weight=1.5, fill=True,
                fill_color='#2980B9', fill_opacity=0.85,
                tooltip=f"Crash — {cr.get('nearest_school','')}"
            ).add_to(m)
            cnt += 1
        print(f"      Added {cnt} crash markers")

# ── OSM Network layers ────────────────────────────────────
_NETWORKS_GPKG = os.path.join(OUT_DIR, 'networks.gpkg')
_net_layers = [
    ('walk_400m',    'Walk Network 400m',    '#27AE60', 2,   0.75, False),
    ('walk_800m',    'Walk Network 800m',    '#27AE60', 1.5, 0.5,  False),
    ('cycling_400m', 'Cycling Network 400m', '#1A8FC1', 2,   0.8,  True),
    ('cycling_800m', 'Cycling Network 800m', '#1A8FC1', 1.5, 0.6,  True),
    ('roads_400m',   'Arterial Roads 400m',  '#C0392B', 2.5, 0.7,  False),
    ('roads_800m',   'Arterial Roads 800m',  '#C0392B', 2,   0.5,  False),
]
if os.path.exists(_NETWORKS_GPKG):
    try:
        import geopandas as _gpd
        _net_added = 0
        for _key, _label, _colour, _weight, _opacity, _is_cycling in _net_layers:
            try:
                _gdf = _gpd.read_file(_NETWORKS_GPKG, layer=_key)
            except Exception:
                continue
            _fg = folium.FeatureGroup(name=_label, show=(_key.endswith('400m')))
            for _, _row in _gdf.iterrows():
                _geom = _row.geometry
                if _geom is None or _geom.is_empty:
                    continue
                if   _geom.geom_type == 'LineString':      _parts = [list(_geom.coords)]
                elif _geom.geom_type == 'MultiLineString': _parts = [list(g.coords) for g in _geom.geoms]
                else: continue
                _w = _weight * 2 if (_is_cycling and _row.get('is_protected')) else _weight
                _c = '#0D4F8B'    if (_is_cycling and _row.get('is_protected')) else _colour
                for _coords in _parts:
                    folium.PolyLine([[c[1], c[0]] for c in _coords],
                                    color=_c, weight=_w, opacity=_opacity).add_to(_fg)
            _fg.add_to(m)
            _net_added += 1
        folium.LayerControl(collapsed=False).add_to(m)
        print(f"      Added {_net_added} network layers")
    except Exception as _e:
        print(f"      (Network layers skipped: {_e})")

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:12px 16px;border-radius:8px;
     border:1px solid #ccc;font-family:Arial;font-size:12px;">
  <b>300,000 Streets — Healthy Streets</b><br>
  <span style="color:#666;font-size:11px">Hazard Severity</span><br><br>
  <span style="color:#C0392B">&#9679;</span> Major<br>
  <span style="color:#D35400">&#9679;</span> Moderate<br>
  <span style="color:#1E8449">&#9679;</span> Minor<br>
  <span style="color:#2980B9">&#9679;</span> Road crash (ped/cyc)<br>
  <span style="color:#333">&#9670;</span> School gate<br>
  &#9711; 400m / 800m buffer<br>
  <span style="color:#27AE60">&#9135;</span> Walk network<br>
  <span style="color:#1A8FC1">&#9135;</span> Cycling (thick = protected)<br>
  <span style="color:#C0392B">&#9135;</span> Arterial roads<br><br>
  <span style="color:#999;font-size:10px">Click markers for HS scores</span>
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))
out_map = os.path.join(OUT_DIR, 'map_interactive.html')
m.save(out_map)
print(f"      Saved -> {out_map}")

# ══════════════════════════════════════════════════════════
# STEP 7 — KDE HEATMAP
# ══════════════════════════════════════════════════════════
print("\n[7/7] Generating KDE Heatmap...")

coords = df[['Latitude', 'Longitude', 'Sev_clean']].dropna(subset=['Latitude', 'Longitude'])
if len(coords) >= 2:
    lats    = coords['Latitude'].values.astype(float)
    lons    = coords['Longitude'].values.astype(float)
    weights = coords['Sev_clean'].map({'Major': 3.0, 'Moderate': 2.0, 'Minor': 1.0}).values

    lat_min, lat_max = lats.min() - 0.012, lats.max() + 0.012
    lon_min, lon_max = lons.min() - 0.012, lons.max() + 0.012
    grid_lon, grid_lat = np.meshgrid(
        np.linspace(lon_min, lon_max, 300),
        np.linspace(lat_min, lat_max, 300)
    )
    bw = 0.008
    density = np.zeros_like(grid_lat)
    for i in range(len(lats)):
        d2 = ((grid_lat - lats[i]) / bw)**2 + ((grid_lon - lons[i]) / bw)**2
        density += weights[i] * np.exp(-0.5 * d2)
    density = (density - density.min()) / (density.max() - density.min() + 1e-10)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        'hs_hazard', ['#1E8449', '#F4D03F', '#D35400', '#C0392B'], N=256)
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('white')
    ax.imshow(density, extent=[lon_min, lon_max, lat_min, lat_max],
              origin='lower', cmap=cmap, alpha=0.75, aspect='auto')
    for _, row in df.dropna(subset=['Latitude', 'Longitude']).iterrows():
        c = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}.get(row['Sev_clean'], '#888888')
        ax.scatter(row['Longitude'], row['Latitude'], c=c, s=140, zorder=5, edgecolors='white', linewidths=1.8)
        ax.annotate(row['School_short'], (row['Longitude'], row['Latitude']),
                    textcoords='offset points', xytext=(8, 4), fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='none'))
    ax.set_title('Hazard Density Heatmap — Healthy Streets Assessment', fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Longitude', fontsize=9)
    ax.set_ylabel('Latitude', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne × RMIT University',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()
    heatmap_out = os.path.join(OUT_DIR, 'heatmap.png')
    plt.savefig(heatmap_out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"      Saved -> {heatmap_out}")

    # GeoTIFF
    kde_tif = os.path.join(OUT_DIR, 'kde_heatmap.tif')
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS as RioCRS
        transform = from_bounds(lon_min, lat_min, lon_max, lat_max, 300, 300)
        with rasterio.open(kde_tif, 'w', driver='GTiff', height=300, width=300,
                           count=1, dtype='float32', crs=RioCRS.from_epsg(4326),
                           transform=transform, nodata=0.0) as dst:
            dst.write(density[::-1].astype('float32'), 1)
        print(f"      Saved -> {kde_tif}")
    except ImportError:
        pass

    # Interactive heatmap HTML
    m2 = folium.Map(location=[lats.mean(), lons.mean()], zoom_start=14,
                    tiles='CartoDB positron', control_scale=True)
    HeatMap([[lats[i], lons[i], weights[i]] for i in range(len(lats))],
            min_opacity=0.4, radius=50, blur=30,
            gradient={'0.2': '#1E8449', '0.5': '#F4D03F', '0.75': '#D35400', '1.0': '#C0392B'}
            ).add_to(m2)
    for name, info in school_gates.items():
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=folium.Popup(f"<b>{name}</b>", max_width=200),
            tooltip=name,
            icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
        ).add_to(m2)
    m2.save(os.path.join(OUT_DIR, 'map_heatmap.html'))
    print(f"      Saved -> {os.path.join(OUT_DIR, 'map_heatmap.html')}")

# ══════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ALL OUTPUTS SAVED — Healthy Streets Framework")
print("="*60)
print("  chart1_hs_radar.png         — 10-indicator radar chart")
print("  chart2_hs_scores.png        — Per-indicator bar comparison")
print("  chart3_hs_breakdown.png     — Per-school breakdown")
print("  chart4_severity.png         — Hazard severity count")
print("  chart5_demographics.png     — Suburb demographics")
print("  map_interactive.html        — Interactive map (HS scores in popup)")
print("  map_heatmap.html            — KDE heatmap")
print("  heatmap.png                 — Static heatmap for QGIS")
print("  recommendations.csv         — HS-aligned recommendations")
print("  hs_scores.csv               — HS1–HS10 per school (input for feature_engineering.py)")
print("="*60)
print("\n  Run order for full pipeline:")
print("  1. python crash_analysis.py")
print("  2. python spatial_features.py      (adds HS3/HS4/HS6/HS8 OSM data)")
print("  3. python environmental_features.py (adds HS7 crime / HS10 AQI)")
print("  4. python poc_pipeline.py          (this script)")
print("  5. python feature_engineering.py")
print("  6. python ml_model.py")
print()
print("  Final Healthy Streets Scores:")
print(df[['School_short', *HS_CODES, 'HS_overall', 'Sev_clean']]
      .rename(columns={'School_short': 'School', 'HS_overall': 'Overall', 'Sev_clean': 'Severity'})
      .to_string(index=False))
