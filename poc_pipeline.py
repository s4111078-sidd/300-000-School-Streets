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
# CONFIG — change filename here when CSV changes
# ══════════════════════════════════════════════════════════
CSV_FILE = 'school_data.csv'
OUT_DIR  = 'outputs'
os.makedirs(OUT_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════
# STEP 1 — LOAD AND CLEAN
# ══════════════════════════════════════════════════════════
print("\n" + "="*55)
print("  300,000 Streets — POC Pipeline")
print("="*55)
print("\n[1/6] Loading and cleaning data...")

df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()

df = df.rename(columns={
    'School name'                                                    : 'School',
    'Overall hazard severity at this location'                       : 'Severity',
    'Footpath Accessibility Score \u2014 FAS (0 to 10)'             : 'FAS',
    'Crossing Safety Score \u2014 CSS (0 to 10)'                    : 'CSS',
    'Environmental Exposure Indicator \u2014 EEI (0 to 10)'         : 'EEI',
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

# ── PRESERVE OBSERVER-ENTERED VALUES FOR AUDIT ────────────
df['FAS_obs'] = pd.to_numeric(df['FAS'], errors='coerce')
df['CSS_obs'] = pd.to_numeric(df['CSS'], errors='coerce')
df['EEI_obs'] = pd.to_numeric(df['EEI'], errors='coerce')

def _clean_sev(s):
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'

df['Sev_obs'] = df['Severity'].apply(_clean_sev)

# ── COMPUTE FAS FROM SUB-INDICATORS ───────────────────────
# AS 1428.1-2009 (min footpath width 1.5m); Scoring Framework v1.0 s.2
def _fas(row):
    pts = 0.0
    p = str(row.get('Footpath_present', ''))
    if   'both sides' in p:                                    pts += 3.0
    elif 'one side'   in p:                                    pts += 2.0
    elif 'partial'    in p.lower() or 'broken' in p.lower():  pts += 1.0

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
    if   'all nearby' in k.lower(): pts += 0.50
    elif 'some'       in k.lower(): pts += 0.25

    o = str(row.get('Obstructions', ''))
    if   'no obstruction' in o.lower(): pts += 0.50
    elif 'minor'          in o.lower(): pts += 0.25

    return min(round(pts, 1), 10.0)

# ── COMPUTE CSS FROM SUB-INDICATORS ───────────────────────
# Austroads Guide to Traffic Management Part 13; AS 1742.10; Scoring Framework v1.0 s.3
def _css(row):
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
    except (ValueError, TypeError): pass  # 'None' or no crossing = 0 pts

    try:
        pts += (float(row['Visibility']) / 5.0) * 2.0
    except (ValueError, TypeError): pass

    t = str(row.get('Tactile', ''))
    if   'both sides' in t.lower(): pts += 1.00
    elif 'one side'   in t.lower(): pts += 0.50

    s = str(row.get('Signal', ''))
    if   'countdown'  in s.lower(): pts += 1.0
    elif ('yes'       in s.lower()
          and 'no pedestrian'  not in s.lower()
          and 'not applicable' not in s.lower()): pts += 0.5

    return min(round(pts, 1), 10.0)

# ── COMPUTE EEI FROM SUB-INDICATORS ───────────────────────
# TAC Victoria speed-injury severity data; VicRoads School Zone Guidelines; Scoring Framework v1.0 s.4
def _eei(row):
    pts = 10.0
    try:
        speed = float(''.join(c for c in str(row.get('Speed_limit', '')) if c.isdigit()) or '50')
        if   speed >= 70: pts -= 3.0
        elif speed >= 60: pts -= 2.0
        elif speed >= 50: pts -= 1.0
    except (ValueError, TypeError): pts -= 1.0

    v = str(row.get('Traffic_volume', '')).lower()
    if   'very high' in v or 'major arterial' in v: pts -= 3.0
    elif 'high'      in v:                          pts -= 2.0
    elif 'moderate'  in v:                          pts -= 1.0

    l = str(row.get('Lanes', '')).lower()
    if   '3 or more' in l: pts -= 1.5
    elif '2 lanes'   in l: pts -= 0.5

    h = str(row.get('Heavy_vehicles', '')).lower()
    if   'frequent' in h: pts -= 1.0
    elif 'occasion' in h: pts -= 0.5

    tc = str(row.get('Traffic_calming', '')).lower()
    if 'no traffic calming' not in tc and tc not in ('', 'nan'):
        pts += 0.5

    sz = str(row.get('School_zone', '')).lower()
    if   'enforced' in sz:                              pts += 1.0
    elif 'present'  in sz and 'no school' not in sz:   pts += 0.5

    return min(max(round(pts, 1), 0.0), 10.0)

# ── COMPUTE CYS FROM OSM CYCLING NETWORK (spatial_features.csv) ───────────────
# Rubric (0–10 total):
#   cycle_pct_400m       : 0-4 pts  (share of cycling edges in walk network)
#   protected_400m       : 0-3 pts  (metres of separated / track infrastructure)
#   signals_400m ≥ 3     : +1 pt    (controlled crossings for cyclists)
#   crossing_density ≥ 1 : +1 pt    (at-grade crossings per km of walk path)
#   avg_speed_400m ≤ 40  : +1 pt    (low-speed environment)

_SPATIAL_CSV = os.path.join('outputs', 'spatial_features.csv')
_school_map  = {
    'Reservoir High School'            : 'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School'              : 'Preston HS',
}

def compute_cys(sf_row):
    score = 0.0
    pct = sf_row.get('cycle_pct_400m', np.nan)
    if pd.notna(pct):
        if   pct >= 40: score += 4
        elif pct >= 25: score += 3
        elif pct >= 15: score += 2
        elif pct >= 5:  score += 1
    protected = sf_row.get('protected_cycle_length_400m', np.nan)
    if pd.notna(protected):
        if   protected >= 300: score += 3
        elif protected >= 100: score += 2
        elif protected > 0:    score += 1
    signals = sf_row.get('signals_400m', np.nan)
    density = sf_row.get('crossing_density_400m', np.nan)
    if pd.notna(signals) and signals >= 3:   score += 1
    if pd.notna(density) and density >= 1.0: score += 1
    avg_speed = sf_row.get('avg_speed_400m', np.nan)
    if pd.notna(avg_speed) and avg_speed <= 40: score += 1
    return round(min(score, 10.0), 1)

def _load_cys(school_full_name):
    short = _school_map.get(school_full_name, school_full_name)
    if os.path.exists(_SPATIAL_CSV):
        try:
            sf = pd.read_csv(_SPATIAL_CSV)
            match = sf[sf['school_name'] == short]
            if not match.empty:
                return compute_cys(match.iloc[0].to_dict())
        except Exception:
            pass
    return np.nan

_CYS_MANUAL_COL = 'Cycling Safety Score — CYS (0 to 10)'
if _CYS_MANUAL_COL in df.columns:
    df['CYS'] = pd.to_numeric(df[_CYS_MANUAL_COL], errors='coerce')
    print('      CYS: using manual scores from school_data.csv')
else:
    df['CYS'] = df['School'].apply(_load_cys)
    print('      CYS: computed from OSM spatial features')

# ── COMPUTE CIS FROM INFRASTRUCTURE TYPE ──────────────────
# LTS (Mekuria, Furth & Nixon 2012); VicRoads TEM Vol. 3 Part 218
CIS_MAP = {
    'Yes — separated bike lane':          9.0,  # LTS 1 — suitable for children
    'Yes — shared path or greenway':      8.0,  # LTS 1 — off-road, no vehicle conflict
    'Yes — painted bike lane (on-road)':  4.5,  # LTS 2–3 — not appropriate for school children per VicRoads TEM Part 218
    'Yes — advisory lane / shared road':  2.0,  # LTS 3–4 — clearly inadequate for children
    'No cycling infrastructure':          1.0,  # LTS 4 equivalent — absence of any provision
}

def _cis(val):
    if pd.isna(val):
        return np.nan
    v = str(val).strip()
    for key, score in CIS_MAP.items():
        if key.lower() in v.lower():
            return score
    return 1.0 if 'no cycling' in v.lower() else 2.0

# ── COMPUTE SEVERITY FROM FRAMEWORK RULES ─────────────────
# Rules: 300,000 Streets Scoring Framework v1.0, Section 5
def _severity(row):
    fas, css, eei = row['FAS'], row['CSS'], row['EEI']
    try:    dist_gate  = float(row.get('Distance_gate', 9999) or 9999)
    except: dist_gate  = 9999
    try:    cross_dist = float(row.get('Crossing_dist', 9999) or 9999)
    except: cross_dist = 9999
    try:    speed = float(''.join(c for c in str(row.get('Speed_limit', '')) if c.isdigit()) or '50')
    except: speed = 50
    no_zone = 'no school zone' in str(row.get('School_zone', '')).lower()

    if fas < 4.0:                      return 'Major'
    if css < 4.0:                      return 'Major'
    if eei < 4.0:                      return 'Major'
    if dist_gate <= 100 and css < 5.0: return 'Major'
    if no_zone and speed >= 60:        return 'Major'
    if fas < 6.0:                      return 'Moderate'
    if css < 6.0:                      return 'Moderate'
    if eei < 6.0:                      return 'Moderate'
    if no_zone:                        return 'Moderate'
    if cross_dist > 150:               return 'Moderate'
    return 'Minor'

# ── APPLY ALL SCORING FUNCTIONS ───────────────────────────
df['FAS'] = df.apply(_fas, axis=1)
df['CSS'] = df.apply(_css, axis=1)
df['EEI'] = df.apply(_eei, axis=1)
df['CIS'] = df['Cycling_infra'].apply(_cis)
df['Sev_clean']     = df.apply(_severity, axis=1)
df['Overall_score'] = df[['FAS', 'CSS', 'EEI', 'CIS', 'CYS']].mean(axis=1)

print(f"      Loaded {len(df)} rows from {CSV_FILE}")
print(f"      Schools: {df['School'].unique().tolist()}")
print()
print("      SCORE AUDIT — computed vs observer-entered:")
print(f"      {'School':<22} {'Dim':>4}  {'Computed':>8}  {'Observer':>8}  {'Δ':>4}")
print("      " + "─" * 54)
for _, row in df.iterrows():
    for dim in ['FAS', 'CSS', 'EEI']:
        comp = row[dim]
        obs  = row[f'{dim}_obs']
        delta = round(abs(comp - obs), 1) if pd.notna(obs) else 0.0
        flag  = '  ← MISMATCH' if delta > 0.2 else ''
        print(f"      {row['School_short']:<22} {dim:>4}  {comp:>8.1f}  {obs:>8.1f}  {delta:>4.1f}{flag}")
print()
print("      SEVERITY AUDIT:")
for _, row in df.iterrows():
    comp = row['Sev_clean']
    obs  = row['Sev_obs']
    flag = ' ✓' if comp == obs else '  ← MISMATCH'
    print(f"      {row['School_short']:<22}: computed={comp:<10} observer={obs}{flag}")
print()
print("      FINAL COMPUTED SCORES:")
print(df[['School_short', 'FAS', 'CSS', 'EEI', 'CIS', 'CYS', 'Sev_clean', 'Overall_score']]
      .rename(columns={'School_short': 'School', 'Sev_clean': 'Severity', 'Overall_score': 'Overall'})
      .to_string(index=False))

# ══════════════════════════════════════════════════════════
# STEP 2 — CHART 1: SAFETY SCORES
# ══════════════════════════════════════════════════════════
print("\n[2/6] Generating Chart 1 — Safety Scores...")

schools  = df['School_short'].tolist()
fas_vals = df['FAS'].tolist()
css_vals = df['CSS'].tolist()
eei_vals = df['EEI'].tolist()
cis_vals = df['CIS'].tolist()
cys_vals = df['CYS'].tolist()
x        = np.arange(len(schools))
width    = 0.15

fig, ax = plt.subplots(figsize=(13, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')

b1 = ax.bar(x - 2*width, fas_vals, width, label='Footpath Score (FAS)',        color='#1A1A1A', edgecolor='white')
b2 = ax.bar(x - 1*width, css_vals, width, label='Crossing Score (CSS)',         color='#555555', edgecolor='white')
b3 = ax.bar(x + 0*width, eei_vals, width, label='Environment Score (EEI)',     color='#999999', edgecolor='white')
b4 = ax.bar(x + 1*width, cis_vals, width, label='Cycling Infra Score (CIS)',   color='#27AE60', edgecolor='white')
b5 = ax.bar(x + 2*width, cys_vals, width, label='Cycling Safety Score (CYS)', color='#1A8FC1', edgecolor='white')

for bars in [b1, b2, b3, b4, b5]:
    for bar in bars:
        h = bar.get_height()
        if np.isnan(h):
            continue
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.15,
                f'{h:.1f}', ha='center', va='bottom',
                fontsize=9, fontweight='bold', color='#1A1A1A')

ax.axhline(y=6, color='#C0392B', linewidth=1, linestyle='--', alpha=0.7, zorder=0)
ax.text(len(schools) - 0.05, 6.15, 'Good threshold (6.0)',
        ha='right', fontsize=9, color='#C0392B', style='italic')
ax.set_xticks(x)
ax.set_xticklabels(schools, fontsize=12, fontweight='bold')
ax.set_ylabel('Score  (0 = worst   |   10 = best)', fontsize=11)
ax.set_ylim(0, 12)
ax.set_title('Average Safety Scores by School', fontsize=14, fontweight='bold', pad=14)
ax.legend(loc='upper left', fontsize=10, framealpha=0.8)
ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out1 = os.path.join(OUT_DIR, 'chart1_safety_scores.png')
plt.savefig(out1, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out1}")

# ══════════════════════════════════════════════════════════
# STEP 3 — CHART 2: HAZARD SEVERITY COUNT
# ══════════════════════════════════════════════════════════
print("\n[3/6] Generating Chart 2 — Hazard Severity...")

sev_order   = ['Major',   'Moderate', 'Minor']
sev_colours = ['#C0392B', '#D35400',  '#1E8449']
school_list = df['School_short'].unique()
counts      = {}
for school in school_list:
    sub = df[df['School_short'] == school]
    counts[school] = {s: int((sub['Sev_clean'] == s).sum()) for s in sev_order}

x2      = np.arange(len(school_list))
width2  = 0.4
bottoms = np.zeros(len(school_list))

fig, ax = plt.subplots(figsize=(11, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')

for sev, colour in zip(sev_order, sev_colours):
    vals = [counts[s][sev] for s in school_list]
    bars = ax.bar(x2, vals, width2, bottom=bottoms,
                  color=colour, edgecolor='white', linewidth=0.8, label=sev)
    for i, (bar, v) in enumerate(zip(bars, vals)):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bottoms[i] + v/2, str(v),
                    ha='center', va='center',
                    fontsize=13, fontweight='bold', color='white')
    bottoms = bottoms + np.array(vals, dtype=float)

for i, school in enumerate(school_list):
    total = sum(counts[school].values())
    ax.text(x2[i], bottoms[i] + 0.05, f'Total: {total}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_xticks(x2)
ax.set_xticklabels(school_list, fontsize=12, fontweight='bold')
ax.set_ylabel('Number of locations assessed', fontsize=11)
ax.set_ylim(0, max(bottoms) + 1.5)
ax.set_yticks(range(0, int(max(bottoms)) + 2))
ax.set_title('Hazard Severity Count by School', fontsize=14, fontweight='bold', pad=14)
ax.legend(loc='upper right', fontsize=10, framealpha=0.8,
          title='Severity level', title_fontsize=10)
ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out2 = os.path.join(OUT_DIR, 'chart2_hazard_severity.png')
plt.savefig(out2, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out2}")

# ══════════════════════════════════════════════════════════
# STEP 4 — CHART 3: SCORE BREAKDOWN PER SCHOOL
# ══════════════════════════════════════════════════════════
print("\n[4/6] Generating Chart 3 — Score Breakdown...")

metric_labels = ['Footpath\n(FAS)', 'Crossing\n(CSS)', 'Environment\n(EEI)', 'Cycling Infra\n(CIS)', 'Cycling Safety\n(CYS)']
n   = len(df)
fig, axes = plt.subplots(1, n, figsize=(8*n, 6), sharey=True)
fig.patch.set_facecolor('white')
if n == 1:
    axes = [axes]

for ax, (_, row) in zip(axes, df.iterrows()):
    raw_vals = [row['FAS'], row['CSS'], row['EEI'], row['CIS'], row['CYS']]
    school = row['School_short']
    sev    = row['Sev_clean']
    bar_colours = []
    plot_vals   = []
    for i, v in enumerate(raw_vals):
        if pd.isna(v):
            plot_vals.append(0)
            bar_colours.append('#CCCCCC')
        else:
            v = float(v)
            plot_vals.append(v)
            if i == 3:   # CIS — green palette
                bar_colours.append('#27AE60' if v >= 6 else '#D35400' if v >= 4 else '#C0392B')
            elif i == 4: # CYS — blue palette
                bar_colours.append('#1A8FC1' if v >= 6 else '#2980B9' if v >= 4 else '#1F618D')
            elif v < 4: bar_colours.append('#C0392B')
            elif v < 6: bar_colours.append('#D35400')
            elif v < 8: bar_colours.append('#888888')
            else:       bar_colours.append('#1A1A1A')
    b = ax.bar(metric_labels, plot_vals, color=bar_colours, edgecolor='white', width=0.5)
    for bar, raw_val, pv in zip(b, raw_vals, plot_vals):
        if pd.isna(raw_val):
            ax.text(bar.get_x() + bar.get_width()/2, 0.3,
                    'N/A', ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color='#888888')
        else:
            ax.text(bar.get_x() + bar.get_width()/2, pv + 0.15,
                    f'{float(raw_val):.1f}', ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color='#1A1A1A')
    ax.set_ylim(0, 12)
    ax.set_title(school, fontsize=11, fontweight='bold', pad=10)
    ax.axhline(y=6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.text(4.3, 6.15, '6.0', fontsize=8, color='#C0392B', va='bottom')
    ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    badge_c = {'Major':'#C0392B','Moderate':'#D35400','Minor':'#1E8449'}.get(sev,'#888888')
    ax.text(0.5, 0.97, f'Severity: {sev}', transform=ax.transAxes,
            ha='center', va='top', fontsize=9, fontweight='bold', color=badge_c,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=badge_c, linewidth=1.5))

axes[0].set_ylabel('Score  (0 = worst   |   10 = best)', fontsize=11)
legend_els = [
    mpatches.Patch(facecolor='#C0392B', label='Below 4.0 — Poor'),
    mpatches.Patch(facecolor='#D35400', label='4.0 to 5.9 — Moderate'),
    mpatches.Patch(facecolor='#888888', label='6.0 to 7.9 — Good'),
    mpatches.Patch(facecolor='#1A1A1A', label='8.0 to 10  — Excellent'),
]
fig.legend(handles=legend_els, loc='lower center', ncol=4,
           fontsize=9, framealpha=0.8, bbox_to_anchor=(0.5, -0.02))
fig.suptitle('Score Breakdown per School', fontsize=14, fontweight='bold', y=1.02)
plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
            ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out3 = os.path.join(OUT_DIR, 'chart3_score_breakdown.png')
plt.savefig(out3, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out3}")

# ══════════════════════════════════════════════════════════
# RECOMMENDATION ENGINE
# Runs before maps so interactive popups use auto-generated
# recommendations — not manually typed CSV fields
# ══════════════════════════════════════════════════════════

def generate_recommendation(row):
    """
    Applies 14 documented rules to one observation row.
    Returns a list of recommendation dicts — one per triggered rule.
    Rules are defined in: docs/300000_Streets_Recommendation_Rules.pdf
    """
    recs = []

    # Rule 1 — FOOTPATH_MISSING
    if row['Footpath_present'] in ['No footpath at all',
                                    'Partial or broken — gaps present']:
        recs.append({
            'hazard'        : 'Missing or broken footpath',
            'recommendation': 'Construct continuous concrete footpath minimum 1.8m wide',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 2 — FOOTPATH_NARROW
    if float(row['Footpath_width']) < 1.5:
        recs.append({
            'hazard'        : 'Footpath below minimum width standard (1.5m)',
            'recommendation': 'Widen footpath to minimum 1.5m — Australian Standard AS 1428.1',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 3 — CROSSING_ABSENT
    if row['Crossing_present'] in ['No crossing at all',
                                    'Yes — informal / unmarked only']:
        recs.append({
            'hazard'        : 'No formal pedestrian crossing present',
            'recommendation': 'Install raised zebra crossing with tactile pavers adjacent to school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 4 — CROSSING_TOO_FAR
    if float(row['Crossing_dist']) > 150:
        recs.append({
            'hazard'        : 'Nearest crossing too far from school gate',
            'recommendation': 'Install additional pedestrian crossing within 50m of school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 5 — TACTILE_MISSING
    if row['Tactile'] == 'No':
        recs.append({
            'hazard'        : 'No tactile ground surface indicators at crossing',
            'recommendation': 'Install tactile pavers on both sides of all crossings within 400m of gate',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 6 — NO_SCHOOL_ZONE
    if row['School_zone'] == 'No school zone at all':
        recs.append({
            'hazard'        : 'No school zone signage present on this street',
            'recommendation': 'Install school zone signs with 40km/h speed restriction on all approaches',
            'priority'      : 'High',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 7 — NO_TRAFFIC_CALMING
    if (row['Traffic_calming'] == 'No traffic calming at all' and
            '3 or more' in str(row['Lanes'])):
        recs.append({
            'hazard'        : 'No traffic calming on multi-lane road near school gate',
            'recommendation': 'Install speed humps or raised intersection table near school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 8 — NO_CYCLING_INFRA
    if row['Cycling_infra'] == 'No cycling infrastructure':
        recs.append({
            'hazard'        : 'No cycling infrastructure on school frontage road',
            'recommendation': 'Install painted bike lane or shared path along school frontage',
            'priority'      : 'Low',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Long-term — 1 to 3 years'
        })

    # Rule 15 — LOW_CYS (Cycling Safety Score below threshold)
    if pd.notna(row.get('CYS')) and float(row['CYS']) < 4:
        recs.append({
            'hazard'        : f'Poor cycling safety score (CYS {row["CYS"]:.1f}/10) — unsafe conditions for students cycling to school',
            'recommendation': 'Install separated cycling infrastructure (kerb-protected lane or shared path), improve surface condition, and add wayfinding signage',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })
    elif pd.notna(row.get('CYS')) and float(row['CYS']) < 6:
        recs.append({
            'hazard'        : f'Moderate cycling safety score (CYS {row["CYS"]:.1f}/10) — cycling route needs improvement',
            'recommendation': 'Add painted bike lanes, fix surface defects, and install parking-protected lane or flexible delineators where space allows',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 9 — POOR_LIGHTING
    if row['Lighting'] in ['Poor — dim or infrequent lights', 'No street lighting']:
        recs.append({
            'hazard'        : 'Poor street lighting on walking route to school',
            'recommendation': 'Install LED street lights at regular intervals along primary walking route',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 10 — VEGETATION_BLOCK
    if 'Vegetation' in str(row['Hazard_types']):
        recs.append({
            'hazard'        : 'Vegetation blocking footpath or crossing sightlines',
            'recommendation': 'Remove and regularly trim vegetation obstructing path and crossing visibility',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 11 — NO_KERB_RAMPS
    if 'No kerb ramps' in str(row['Kerb_ramps']):
        recs.append({
            'hazard'        : 'No kerb ramps at intersections within catchment zone',
            'recommendation': 'Install kerb ramps at all intersections within 400m of school gate',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 12 — HIGH_SPEED_ZONE
    if any(speed in str(row['Speed_limit']) for speed in ['60', '70', '80', '90', '100']):
        recs.append({
            'hazard'        : 'Speed limit exceeds school zone standard near school gate',
            'recommendation': 'Advocate for speed limit reduction to 40km/h and school zone establishment',
            'priority'      : 'High',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 13 — HEAVY_VEHICLE_ROUTE
    if 'frequent' in str(row['Heavy_vehicles']).lower():
        recs.append({
            'hazard'        : 'Frequent heavy vehicles travelling past school gate',
            'recommendation': 'Install heavy vehicle restriction signage and physical barriers during school hours',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Rule 14 — LOW_VISIBILITY_CROSSING
    if pd.notna(row['Visibility']) and float(row['Visibility']) < 3:
        recs.append({
            'hazard'        : 'Poor crossing visibility — approaching drivers cannot see pedestrians in time',
            'recommendation': 'Remove sightline obstructions, install raised crossing platform and advance warning signs',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    return recs


# Apply engine to every row in the dataset
all_recs = []
for _, row in df.iterrows():
    for rec in generate_recommendation(row):
        all_recs.append({
            'School'        : row['School'],
            'Location'      : row['Street'],
            'Severity'      : row['Sev_clean'],
            'FAS'           : row['FAS'],
            'CSS'           : row['CSS'],
            'EEI'           : row['EEI'],
            'CIS'           : row['CIS'],
            'Hazard'        : rec['hazard'],
            'Recommendation': rec['recommendation'],
            'Priority'      : rec['priority'],
            'Cost'          : rec['cost'],
            'Timeframe'     : rec['timeframe'],
        })

rec_df  = pd.DataFrame(all_recs)
rec_out = os.path.join(OUT_DIR, 'recommendations.csv')
rec_df.to_csv(rec_out, index=False)

print(f"\n  Recommendations generated: {len(rec_df)} total")
print(rec_df[['School', 'Hazard', 'Priority']].to_string(index=False))
print(f"\n  Saved -> {rec_out}")

# ══════════════════════════════════════════════════════════
# STEP 5 — INTERACTIVE MAP
# ══════════════════════════════════════════════════════════
print("\n[5/6] Generating Interactive Map...")

centre_lat = df['Latitude'].mean()
centre_lon = df['Longitude'].mean()
m = folium.Map(location=[centre_lat, centre_lon],
               zoom_start=14, tiles='CartoDB positron', control_scale=True)

school_gates = {
    'Reservoir High School':            {'lat': -37.7224,  'lon': 145.0294,  'addr': '855 Plenty Rd, Reservoir VIC 3073'},
    'William Ruthven Secondary College':{'lat': -37.69654, 'lon': 145.00299, 'addr': '60 Merrilands Rd, Reservoir VIC 3073'},
    'Preston High School':              {'lat': -37.7417,  'lon': 145.0071,  'addr': '2-16 Cooma St, Preston VIC 3072'},
}
folium_sev = {'Major': 'red', 'Moderate': 'orange', 'Minor': 'green', 'Unknown': 'gray'}

for name, info in school_gates.items():
    folium.Marker(
        location=[info['lat'], info['lon']],
        popup=folium.Popup(
            f"<b>{name}</b><br>{info['addr']}<br><i>School gate</i>", max_width=240),
        tooltip=name,
        icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
    ).add_to(m)
    folium.Circle(
        location=[info['lat'], info['lon']], radius=400,
        color='#333333', weight=1.5, fill=True, fill_opacity=0.04,
        tooltip='400m buffer'
    ).add_to(m)
    folium.Circle(
        location=[info['lat'], info['lon']], radius=800,
        color='#888888', weight=1, fill=True, fill_opacity=0.02,
        tooltip='800m buffer', dash_array='6'
    ).add_to(m)

for _, row in df.iterrows():
    lat = row['Latitude']
    lon = row['Longitude']
    if pd.isna(lat) or pd.isna(lon):
        continue

    sev     = row['Sev_clean']
    hazards = str(row['Hazard_types']) if pd.notna(row['Hazard_types']) else 'Not recorded'

    # Use first auto-generated recommendation — not manual CSV field
    school_recs = rec_df[rec_df['School'] == row['School']]
    top_rec = school_recs.iloc[0]['Recommendation'] if len(school_recs) > 0 else 'Not recorded'
    top_pri = school_recs.iloc[0]['Priority']       if len(school_recs) > 0 else 'Not recorded'

    popup_html = f"""
    <div style="font-family:Arial;font-size:12px;min-width:230px">
      <b style="font-size:13px">{row['School']}</b><br>
      <span style="color:#666">{row['Street']}</span><br>
      <hr style="margin:5px 0">
      <b>Severity:</b>
      <span style="color:{folium_sev.get(sev,'gray')}">{sev}</span><br>
      <b>FAS:</b> {row['FAS']:.1f} &nbsp;
      <b>CSS:</b> {row['CSS']:.1f} &nbsp;
      <b>EEI:</b> {row['EEI']:.1f} &nbsp;
      <b>CIS:</b> {row['CIS']:.1f}<br>
      <hr style="margin:5px 0">
      <b>Hazards:</b><br>
      <span style="color:#555;font-size:11px">{hazards}</span><br>
      <hr style="margin:5px 0">
      <b>Top Recommendation:</b><br>
      <span style="font-size:11px">{top_rec}</span><br>
      <b>Priority:</b> {top_pri}
    </div>"""

    folium.CircleMarker(
        location=[lat, lon], radius=12,
        color='white', weight=2, fill=True,
        fill_color=folium_sev.get(sev, 'gray'), fill_opacity=0.9,
        popup=folium.Popup(popup_html, max_width=270),
        tooltip=f"{row['School_short']} — {row['Street']} ({sev})"
    ).add_to(m)

# ── Crash markers (optional — needs crash_analysis.py to have been run) ───────
crash_csv_path = os.path.join(OUT_DIR, 'crash_data_darebin.csv')
crash_count_interactive = 0
crash_df = pd.DataFrame()
lat_c = lon_c = None
if os.path.exists(crash_csv_path):
    crash_df = pd.read_csv(crash_csv_path, low_memory=False)
    crash_df.columns = crash_df.columns.str.strip()
    lat_c = next((c for c in crash_df.columns if c.upper() in ('LAT', 'LATITUDE', 'Y')), None)
    lon_c = next((c for c in crash_df.columns if c.upper() in ('LON', 'LONG', 'LONGITUDE', 'X')), None)
    if lat_c and lon_c:
        for _, cr in crash_df.dropna(subset=[lat_c, lon_c]).iterrows():
            school = cr.get('nearest_school', 'Unknown')
            dist   = cr.get('dist_to_gate_m', '')
            date   = cr.get('ACCIDENTDATE', '') or cr.get('accidentdate', '')
            folium.CircleMarker(
                location=[cr[lat_c], cr[lon_c]], radius=7,
                color='white', weight=1.5, fill=True,
                fill_color='#2980B9', fill_opacity=0.85,
                popup=folium.Popup(
                    f"<div style='font-family:Arial;font-size:12px'>"
                    f"<b>Road Crash</b><br>"
                    f"<b>School:</b> {school}<br>"
                    f"<b>Distance to gate:</b> {dist:.0f}m<br>" if isinstance(dist, float) else
                    f"<b>Distance to gate:</b> {dist}<br>"
                    f"<b>Date:</b> {date}<br>"
                    f"<span style='color:#2980B9'>Pedestrian/Cyclist involved</span>"
                    f"</div>", max_width=220),
                tooltip=f"Crash — {school} ({dist:.0f}m)" if isinstance(dist, float) else f"Crash — {school}"
            ).add_to(m)
            crash_count_interactive += 1
        print(f"      Added {crash_count_interactive} crash markers to interactive map")

# ── OSM Network layers (from spatial_features.py output) ──────────────────────
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
                if _geom.geom_type == 'LineString':
                    _parts = [list(_geom.coords)]
                elif _geom.geom_type == 'MultiLineString':
                    _parts = [list(g.coords) for g in _geom.geoms]
                else:
                    continue
                _w = _weight * 2 if (_is_cycling and _row.get('is_protected')) else _weight
                _c = '#0D4F8B'    if (_is_cycling and _row.get('is_protected')) else _colour
                for _coords in _parts:
                    folium.PolyLine(
                        [[c[1], c[0]] for c in _coords],
                        color=_c, weight=_w, opacity=_opacity,
                        tooltip=str(_row.get('highway', '')),
                    ).add_to(_fg)
            _fg.add_to(m)
            _net_added += 1
        folium.LayerControl(collapsed=False).add_to(m)
        print(f"      Added {_net_added} network layers to interactive map")
    except Exception as _e:
        print(f"      (Network layers skipped: {_e})")
else:
    print("      (networks.gpkg not found — run spatial_features.py to add network layers)")

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:12px 16px;border-radius:8px;
     border:1px solid #ccc;font-family:Arial;font-size:12px;">
  <b>300,000 Streets</b><br>
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
  <span style="color:#999;font-size:10px">Click any point for details</span>
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))
out_map = os.path.join(OUT_DIR, 'map_interactive.html')
m.save(out_map)
print(f"      Saved -> {out_map}")

# ══════════════════════════════════════════════════════════
# STEP 6 — KDE HEATMAP (pure numpy — no scipy required)
# ══════════════════════════════════════════════════════════
print("\n[6/6] Generating KDE Heatmap...")

coords = df[['Latitude', 'Longitude', 'Sev_clean']].dropna(subset=['Latitude', 'Longitude'])

if len(coords) < 2:
    print("      Not enough points for heatmap — need at least 2 observations")
    print("      Heatmap will improve automatically as more data is collected")
else:
    lats    = coords['Latitude'].values.astype(float)
    lons    = coords['Longitude'].values.astype(float)

    def sev_weight(s):
        if s == 'Major':    return 3.0
        if s == 'Moderate': return 2.0
        return 1.0

    weights = coords['Sev_clean'].apply(sev_weight).values

    # Build density grid using pure numpy Gaussian kernel
    lat_min, lat_max = lats.min() - 0.012, lats.max() + 0.012
    lon_min, lon_max = lons.min() - 0.012, lons.max() + 0.012

    grid_lon, grid_lat = np.meshgrid(
        np.linspace(lon_min, lon_max, 300),
        np.linspace(lat_min, lat_max, 300)
    )

    bandwidth = 0.008
    density   = np.zeros_like(grid_lat)
    for i in range(len(lats)):
        d2 = ((grid_lat - lats[i]) / bandwidth) ** 2 + \
             ((grid_lon - lons[i]) / bandwidth) ** 2
        density += weights[i] * np.exp(-0.5 * d2)

    density = (density - density.min()) / (density.max() - density.min() + 1e-10)

    # ── Static PNG for QGIS import ─────────────────────────
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'hazard', ['#1E8449', '#F4D03F', '#D35400', '#C0392B'], N=256
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('white')
    im = ax.imshow(density,
                   extent=[lon_min, lon_max, lat_min, lat_max],
                   origin='lower', cmap=cmap, alpha=0.75, aspect='auto')

    sev_dot_colours = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}
    for _, row in df.dropna(subset=['Latitude', 'Longitude']).iterrows():
        c = sev_dot_colours.get(row['Sev_clean'], '#888888')
        ax.scatter(row['Longitude'], row['Latitude'],
                   c=c, s=140, zorder=5, edgecolors='white', linewidths=1.8)
        ax.annotate(row['School_short'],
                    (row['Longitude'], row['Latitude']),
                    textcoords='offset points', xytext=(8, 4),
                    fontsize=8, fontweight='bold', color='#1A1A1A',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.8, edgecolor='none'))

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Hazard Density (weighted by severity)', fontsize=9, color='#444444')
    cbar.ax.tick_params(labelsize=8)
    ax.set_title('Hazard Density Heatmap — School Catchment Zones',
                 fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Longitude', fontsize=9, color='#666666')
    ax.set_ylabel('Latitude',  fontsize=9, color='#666666')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()
    heatmap_out = os.path.join(OUT_DIR, 'heatmap.png')
    plt.savefig(heatmap_out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"      Saved -> {heatmap_out}")

    # ── GeoTIFF for PyQGIS import ──────────────────────────
    kde_tif = os.path.join(OUT_DIR, 'kde_heatmap.tif')
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS as RioCRS
        transform = from_bounds(lon_min, lat_min, lon_max, lat_max, 300, 300)
        with rasterio.open(
            kde_tif, 'w', driver='GTiff',
            height=300, width=300, count=1, dtype='float32',
            crs=RioCRS.from_epsg(4326), transform=transform, nodata=0.0,
        ) as dst:
            dst.write(density[::-1].astype('float32'), 1)  # flip: matplotlib origin=lower
        print(f"      Saved -> {kde_tif}  (georeferenced — ready for PyQGIS)")
    except ImportError:
        print("      NOTE: rasterio not installed — kde_heatmap.tif not saved")
        print("            Run: pip install rasterio")

    # ── Interactive heatmap HTML ───────────────────────────
    heat_data = [[float(lats[i]), float(lons[i]), float(weights[i])]
                 for i in range(len(lats))]

    m2 = folium.Map(location=[lats.mean(), lons.mean()],
                    zoom_start=14, tiles='CartoDB positron', control_scale=True)

    HeatMap(heat_data, min_opacity=0.4, radius=50, blur=30,
            gradient={'0.2': '#1E8449', '0.5': '#F4D03F',
                      '0.75': '#D35400', '1.0': '#C0392B'}
            ).add_to(m2)

    for name, info in school_gates.items():
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=folium.Popup(f"<b>{name}</b><br>{info['addr']}", max_width=220),
            tooltip=name,
            icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
        ).add_to(m2)
        folium.Circle(
            location=[info['lat'], info['lon']], radius=400,
            color='#333333', weight=1.5, fill=True, fill_opacity=0.04,
            tooltip='400m buffer'
        ).add_to(m2)

    for _, row in df.iterrows():
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            continue

        sev     = row['Sev_clean']
        hazards = str(row['Hazard_types']) if pd.notna(row['Hazard_types']) else 'Not recorded'

        # Use auto-generated recommendation — not manual CSV field
        school_recs = rec_df[rec_df['School'] == row['School']]
        top_rec = school_recs.iloc[0]['Recommendation'] if len(school_recs) > 0 else 'Not recorded'
        top_pri = school_recs.iloc[0]['Priority']       if len(school_recs) > 0 else 'Not recorded'

        popup_html = f"""
        <div style="font-family:Arial;font-size:12px;min-width:230px">
          <b style="font-size:13px">{row['School']}</b><br>
          <span style="color:#666">{row['Street']}</span><br>
          <hr style="margin:5px 0">
          <b>Severity:</b>
          <span style="color:{folium_sev.get(sev,'gray')}">{sev}</span><br>
          <b>FAS:</b> {row['FAS']:.1f} &nbsp;
          <b>CSS:</b> {row['CSS']:.1f} &nbsp;
          <b>EEI:</b> {row['EEI']:.1f}<br>
          <hr style="margin:5px 0">
          <b>Hazards:</b><br>
          <span style="color:#555;font-size:11px">{hazards}</span><br>
          <hr style="margin:5px 0">
          <b>Top Recommendation:</b><br>
          <span style="font-size:11px">{top_rec}</span><br>
          <b>Priority:</b> {top_pri}
        </div>"""

        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=10, color='white', weight=2,
            fill=True, fill_color=folium_sev.get(sev, 'gray'), fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=270),
            tooltip=f"{row['School_short']} — {row['Street']} ({sev})"
        ).add_to(m2)

    # ── Crash markers on heatmap ──────────────────────────────
    if os.path.exists(crash_csv_path) and lat_c and lon_c:
        for _, cr in crash_df.dropna(subset=[lat_c, lon_c]).iterrows():
            school = cr.get('nearest_school', 'Unknown')
            dist   = cr.get('dist_to_gate_m', '')
            folium.CircleMarker(
                location=[cr[lat_c], cr[lon_c]], radius=6,
                color='white', weight=1.5, fill=True,
                fill_color='#2980B9', fill_opacity=0.85,
                tooltip=f"Crash — {school}"
            ).add_to(m2)

    legend_html2 = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
         background:white;padding:12px 16px;border-radius:8px;
         border:1px solid #ccc;font-family:Arial;font-size:12px;">
      <b>300,000 Streets</b><br>
      <span style="color:#666;font-size:11px">Hazard Heatmap</span><br><br>
      <span style="color:#C0392B">&#9632;</span> High density<br>
      <span style="color:#D35400">&#9632;</span> Medium density<br>
      <span style="color:#F4D03F">&#9632;</span> Low density<br>
      <span style="color:#1E8449">&#9632;</span> Minimal<br>
      <span style="color:#D35400">&#9679;</span> Moderate hazard<br>
      <span style="color:#1E8449">&#9679;</span> Minor hazard<br>
      <span style="color:#2980B9">&#9679;</span> Road crash (ped/cyc)<br>
      &#9711; 400m buffer<br><br>
      <span style="color:#999;font-size:10px">Weighted by severity</span>
    </div>"""
    m2.get_root().html.add_child(folium.Element(legend_html2))
    heatmap_html = os.path.join(OUT_DIR, 'map_heatmap.html')
    m2.save(heatmap_html)
    print(f"      Saved -> {heatmap_html}")
    print("      Open map_heatmap.html in browser — interactive heatmap")
    print("      heatmap.png ready for QGIS import")

# ══════════════════════════════════════════════════════════
# DONE — final summary
# ══════════════════════════════════════════════════════════
print("\n" + "="*55)
print("  ALL OUTPUTS SAVED TO /outputs/")
print("="*55)
print("  chart1_safety_scores.png    — Safety scores bar chart")
print("  chart2_hazard_severity.png  — Hazard severity count")
print("  chart3_score_breakdown.png  — Per school score breakdown")
print("  map_interactive.html        — Interactive map (open in browser)")
print("  map_heatmap.html            — KDE heatmap (open in browser)")
print("  heatmap.png                 — Static heatmap for QGIS import")
print("  recommendations.csv         — Auto-generated recommendations")
print("="*55)
print("\n  Final computed scores (FAS/CSS/EEI computed from sub-indicators):")
print(df[['School_short', 'FAS', 'CSS', 'EEI', 'CIS', 'Sev_clean', 'Overall_score']]
      .rename(columns={'School_short': 'School', 'Sev_clean': 'Severity',
                       'Overall_score': 'Overall'})
      .to_string(index=False))
print("\n  Observer-entered scores (for audit):")
print(df[['School_short', 'FAS_obs', 'CSS_obs', 'EEI_obs']]
      .rename(columns={'School_short': 'School', 'FAS_obs': 'FAS', 'CSS_obs': 'CSS', 'EEI_obs': 'EEI'})
      .to_string(index=False))
print("\n  To update: replace CSV and re-run python poc_pipeline.py\n")

# ══════════════════════════════════════════════════════════
# STEP 7 — DEMOGRAPHICS ANALYSIS
# ══════════════════════════════════════════════════════════
print("\n[7/7] Generating Demographics Analysis...")

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
    colours = ['#1A5276', '#C0392B', '#D35400', '#1E8449']

    for ax, (metric, vals), colour in zip(axes, metrics.items(), colours):
        bars = ax.bar(suburbs, vals, color=colour,
                      edgecolor='white', width=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + max(vals)*0.02,
                    str(val), ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color='#1A1A1A')
        ax.set_title(metric, fontsize=9, fontweight='bold',
                     color='#1A1A1A', pad=8)
        ax.set_ylim(0, max(vals) * 1.3)
        ax.set_xticklabels(suburbs, fontsize=9, fontweight='bold')
        ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')

    fig.suptitle(
        'Suburb Demographics — City of Darebin  (ABS Census 2021)',
        fontsize=13, fontweight='bold', y=1.02)
    plt.figtext(0.99, 0.01,
                '300,000 Streets  |  Source: ABS Census 2021',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()

    demo_chart = os.path.join(OUT_DIR, 'chart4_demographics.png')
    plt.savefig(demo_chart, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"      Saved -> {demo_chart}")

    # Print key insights
    print("\n      KEY INSIGHTS:")
    for _, row in demo_df.iterrows():
        children = round(row['Total population'] *
                         row['% children aged 5-17'] / 100)
        print(f"      {row['Suburb']}:")
        print(f"        ~{children:,} school-age children")
        print(f"        ${row['Median weekly household income ($)']:,}/week median income")
        print(f"        {row['% households no car']}% households have no car")
        print(f"        {row['% working full time (35hrs+)']}% parents working full time")

except FileNotFoundError:
    print(f"      WARNING: {demo_file} not found — skipping")
    print("      Copy demographics_darebin.csv to FYP folder")