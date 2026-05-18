"""
300,000 Streets — Healthy Streets Pipeline (modular entry point)

Run:  python main.py

Outputs (all in outputs/):
  chart1_hs_radar.png        — Healthy Streets 10-indicator radar chart
  chart2_hs_scores.png       — Per-indicator bar chart comparison
  chart3_hs_breakdown.png    — Per-school HS score breakdown
  map_interactive.html        — Interactive hazard map (open in browser)
  map_heatmap.html            — KDE heatmap (open in browser)
  heatmap.png                 — Static heatmap for QGIS import
  recommendations.csv         — Auto-generated HS-based recommendations
  hs_scores.csv               — School-level HS1–HS10 scores

Prerequisite scripts (run once to populate outputs/):
  python spatial_features.py          -> outputs/spatial_features.csv
  python environmental_features.py    -> outputs/environmental_features.csv
  python crash_analysis.py            -> outputs/crash_data_*.csv
"""
import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from config import (
    CSV_FILE, OUT_DIR, SPATIAL_CSV, ENV_CSV, HS_CSV,
    HS_INDICATORS, HS_CODES, HS_LABELS, SCHOOL_SHORT_NAMES,
)
from src.data.loader              import load_school_data
from src.scoring                  import (
    compute_hs1, compute_hs2, compute_hs3, compute_hs4, compute_hs5,
    compute_hs6, compute_hs7, compute_hs8, compute_hs9, compute_hs10,
    compute_severity,
)
from src.recommendations.engine   import run_recommendations
from src.visualisation.heatmap    import build_kde_heatmap
from src.visualisation.interactive_map import build_interactive_map

OUT_DIR_STR = str(OUT_DIR)
os.makedirs(OUT_DIR_STR, exist_ok=True)

_FOOTER = '300,000 Streets  |  Regen Melbourne × RMIT University'
SCHOOL_COLOURS = {
    'Reservoir HS':       '#1A476E',
    'William Ruthven SC': '#1A8FC1',
    'Preston HS':         '#C0392B',
}

# ── Fallback env values if environmental_features.csv not available ────────────
_ENV_FALLBACK = {
    'Reservoir High School':             {'aqi_pm25': 8.2,  'crime_rate_per_100k': 850},
    'William Ruthven Secondary College': {'aqi_pm25': 7.1,  'crime_rate_per_100k': 580},
    'Preston High School':               {'aqi_pm25': 7.8,  'crime_rate_per_100k': 720},
}

print("\n" + "="*60)
print("  300,000 Streets — Healthy Streets Pipeline")
print("="*60)

# ══════════════════════════════════════════════════════════
# STEP 1 — LOAD DATA
# ══════════════════════════════════════════════════════════
print("\n[1/6] Loading and cleaning data...")

df = load_school_data(str(CSV_FILE))
print(f"      Loaded {len(df)} rows  |  Schools: {df['School'].unique().tolist()}")

# Spatial features (OSM-derived)
_sf = None
if SPATIAL_CSV.exists():
    _sf = pd.read_csv(SPATIAL_CSV).set_index('school_name')
    print(f"      Spatial features loaded  ({len(_sf)} schools, {len(_sf.columns)} cols)")
else:
    print("      (spatial_features.csv not found — HS3/HS4/HS6/HS8 will be NaN)")

def _spatial(school_full: str) -> dict:
    if _sf is None:
        return {}
    short = SCHOOL_SHORT_NAMES.get(school_full, school_full)
    if short in _sf.index:
        return _sf.loc[short].to_dict()
    if school_full in _sf.index:
        return _sf.loc[school_full].to_dict()
    return {}

# Environmental features (AQI + crime)
_ef = None
if ENV_CSV.exists():
    _ef = pd.read_csv(ENV_CSV).set_index('school_name')
    print(f"      Environmental features loaded  ({len(_ef)} schools)")
else:
    print("      (environmental_features.csv not found — using suburb-level fallbacks)")

def _env(school_full: str) -> dict:
    if _ef is not None:
        short = SCHOOL_SHORT_NAMES.get(school_full, school_full)
        if short in _ef.index:
            return _ef.loc[short].to_dict()
        if school_full in _ef.index:
            return _ef.loc[school_full].to_dict()
    return _ENV_FALLBACK.get(school_full, {})

# ══════════════════════════════════════════════════════════
# STEP 2 — APPLY HS SCORING
# ══════════════════════════════════════════════════════════
print("\n[2/6] Computing Healthy Streets scores...")

for idx, row in df.iterrows():
    sp = _spatial(row['School'])
    ev = _env(row['School'])
    df.loc[idx, 'HS1']  = compute_hs1(row)
    df.loc[idx, 'HS2']  = compute_hs2(row)
    df.loc[idx, 'HS3']  = compute_hs3(row, sp)
    df.loc[idx, 'HS4']  = compute_hs4(row, sp)
    df.loc[idx, 'HS5']  = compute_hs5(row)
    df.loc[idx, 'HS6']  = compute_hs6(row, sp)
    df.loc[idx, 'HS7']  = compute_hs7(row, ev)
    df.loc[idx, 'HS8']  = compute_hs8(row, sp)
    df.loc[idx, 'HS9']  = compute_hs9(row)
    df.loc[idx, 'HS10'] = compute_hs10(row, ev, sp)

df['HS_overall'] = df[HS_CODES].mean(axis=1, skipna=True).round(1)
df['Sev_clean']  = df.apply(compute_severity, axis=1)

# School-level summary (mean per school for HS scores CSV)
school_hs = (df.groupby(['School', 'School_short'])[HS_CODES + ['HS_overall']]
               .mean().round(2).reset_index())
school_hs.to_csv(str(HS_CSV), index=False)
print(f"      HS scores saved -> {HS_CSV}")

print(f"\n      {'School':<22} " + " ".join(f"{c:>5}" for c in HS_CODES) + f"  {'Overall':>7}")
print("      " + "─" * 100)
for _, row in school_hs.iterrows():
    scores = " ".join(f"{row[c]:>5.1f}" if pd.notna(row[c]) else "  N/A" for c in HS_CODES)
    print(f"      {row['School_short']:<22} {scores}  {row['HS_overall']:>7.1f}")

# ══════════════════════════════════════════════════════════
# STEP 3 — CHART 1: RADAR CHART
# ══════════════════════════════════════════════════════════
print("\n[3/6] Generating charts...")

N      = len(HS_CODES)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')

for ring in [2, 4, 6, 8, 10]:
    ax.plot(angles, [ring] * (N + 1), color='#DDDDDD', linewidth=0.6, zorder=0)
    ax.text(angles[0], ring + 0.2, str(ring), ha='center', va='bottom', fontsize=7, color='#AAAAAA')

ax.plot(angles, [6] * (N + 1), color='#C0392B', linewidth=1.2, linestyle='--', alpha=0.6, zorder=1)
ax.text(angles[1], 6.6, 'Good threshold\n(6.0)', ha='left', va='center',
        fontsize=8, color='#C0392B', style='italic')

for i, (_, row) in enumerate(school_hs.iterrows()):
    school = row['School_short']
    colour = list(SCHOOL_COLOURS.values())[i % len(SCHOOL_COLOURS)]
    colour = SCHOOL_COLOURS.get(school, colour)
    values = [row[c] if pd.notna(row[c]) else 0 for c in HS_CODES] + [row[HS_CODES[0]] if pd.notna(row[HS_CODES[0]]) else 0]
    ax.plot(angles, values, color=colour, linewidth=2.5, zorder=3, label=school)
    ax.fill(angles, values, color=colour, alpha=0.10, zorder=2)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(HS_LABELS, size=10, fontweight='bold', color='#333333')
ax.set_ylim(0, 10)
ax.set_yticks([])
ax.spines['polar'].set_color('#CCCCCC')
ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.15), fontsize=11,
          framealpha=0.9, title='School', title_fontsize=11)
ax.set_title('Healthy Streets Assessment\n10-Indicator Radar Chart',
             fontsize=14, fontweight='bold', pad=24, color='#1A476E')
plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
out_radar = os.path.join(OUT_DIR_STR, 'chart1_hs_radar.png')
plt.savefig(out_radar, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_radar}")

# ── Chart 2: Per-indicator bar chart ──────────────────────────────────────────
schools_list = school_hs['School_short'].tolist()
x_pos = np.arange(len(schools_list))

fig, axes = plt.subplots(2, 5, figsize=(18, 8), sharey=True)
fig.patch.set_facecolor('white')
axes = axes.flatten()

for ax_i, (code, label) in enumerate(zip(HS_CODES, HS_LABELS)):
    ax = axes[ax_i]
    ax.set_facecolor('#FAFAFA')
    vals = [school_hs.loc[r, code] if pd.notna(school_hs.loc[r, code]) else 0
            for r in school_hs.index]
    bar_cols = ['#27AE60' if v >= 7 else ('#F39C12' if v >= 5 else ('#C0392B' if v > 0 else '#CCCCCC'))
                for v in vals]
    bars = ax.bar(x_pos, vals, 0.55, color=bar_cols, edgecolor='white')
    for bar, v, r in zip(bars, vals, school_hs.index):
        lbl = f'{v:.1f}' if pd.notna(school_hs.loc[r, code]) else 'N/A'
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.15,
                lbl, ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.axhline(y=6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(schools_list, fontsize=8, rotation=15, ha='right')
    ax.set_ylim(0, 12)
    ax.set_title(f'{code}\n{label.replace(chr(10), " ")}', fontsize=9, fontweight='bold', pad=6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.5)
    ax.set_axisbelow(True)

axes[0].set_ylabel('Score  (0 = worst  |  10 = best)', fontsize=10)
axes[5].set_ylabel('Score  (0 = worst  |  10 = best)', fontsize=10)
fig.legend(handles=[
    mpatches.Patch(color='#27AE60', label='Good (≥7.0)'),
    mpatches.Patch(color='#F39C12', label='Moderate (5–6.9)'),
    mpatches.Patch(color='#C0392B', label='Poor (<5.0)'),
    mpatches.Patch(color='#CCCCCC', label='No data'),
], loc='lower center', ncol=4, fontsize=9, framealpha=0.9, bbox_to_anchor=(0.5, -0.02))
fig.suptitle('Healthy Streets — 10-Indicator Score Comparison by School',
             fontsize=14, fontweight='bold', y=1.01)
plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out_bar = os.path.join(OUT_DIR_STR, 'chart2_hs_scores.png')
plt.savefig(out_bar, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_bar}")

# ── Chart 3: Per-school breakdown ─────────────────────────────────────────────
short_labels = [l.replace('\n', ' ') for l in HS_LABELS]
n_schools    = len(school_hs)
fig, axes    = plt.subplots(1, n_schools, figsize=(9 * n_schools, 7), sharey=True)
fig.patch.set_facecolor('white')
if n_schools == 1:
    axes = [axes]

for ax, (_, row) in zip(axes, school_hs.iterrows()):
    school = row['School_short']
    colour = SCHOOL_COLOURS.get(school, '#1A476E')
    sev    = df[df['School_short'] == school]['Sev_clean'].mode()
    sev    = sev.iloc[0] if len(sev) else 'Unknown'
    vals = [float(row[c]) if pd.notna(row[c]) else 0 for c in HS_CODES]
    bar_cols = ['#DDDDDD' if pd.isna(row[c])
                else ('#27AE60' if row[c] >= 7 else ('#F39C12' if row[c] >= 5 else '#C0392B'))
                for c in HS_CODES]
    bars = ax.bar(short_labels, vals, color=bar_cols, edgecolor='white', width=0.6)
    for bar, v, c in zip(bars, vals, HS_CODES):
        lbl = f'{v:.1f}' if pd.notna(row[c]) else 'N/A'
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.15,
                lbl, ha='center', va='bottom', fontsize=9, fontweight='bold')
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
plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
plt.tight_layout()
out_breakdown = os.path.join(OUT_DIR_STR, 'chart3_hs_breakdown.png')
plt.savefig(out_breakdown, dpi=150, bbox_inches='tight')
plt.close()
print(f"      Saved -> {out_breakdown}")

# ══════════════════════════════════════════════════════════
# STEP 4 — RECOMMENDATIONS
# ══════════════════════════════════════════════════════════
print("\n[4/6] Generating recommendations...")
rec_df  = run_recommendations(df)
rec_out = os.path.join(OUT_DIR_STR, 'recommendations.csv')
rec_df.to_csv(rec_out, index=False)
print(f"      {len(rec_df)} recommendations generated -> {rec_out}")

# ══════════════════════════════════════════════════════════
# STEP 5 — INTERACTIVE MAP
# ══════════════════════════════════════════════════════════
print("\n[5/6] Generating interactive map...")
try:
    out_map = build_interactive_map(df, rec_df, OUT_DIR_STR)
    print(f"      Saved -> {out_map}")
except Exception as e:
    print(f"      Warning: map failed — {e}")

# ══════════════════════════════════════════════════════════
# STEP 6 — KDE HEATMAP
# ══════════════════════════════════════════════════════════
print("\n[6/6] Generating KDE heatmap...")
try:
    build_kde_heatmap(df, rec_df, OUT_DIR_STR)
    print(f"      Saved -> outputs/map_heatmap.html + heatmap.png")
except Exception as e:
    print(f"      Warning: heatmap failed — {e}")

# ══════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ALL OUTPUTS SAVED TO outputs/")
print("="*60)
print("  chart1_hs_radar.png      — HS radar chart")
print("  chart2_hs_scores.png     — per-indicator comparison")
print("  chart3_hs_breakdown.png  — per-school breakdown")
print("  map_interactive.html      — interactive hazard map")
print("  map_heatmap.html          — KDE heatmap")
print("  recommendations.csv       — HS-based recommendations")
print("  hs_scores.csv             — school-level HS1–HS10 scores")
print("="*60)
print("\n  Next steps:")
print("    python feature_engineering.py  -> outputs/ml_school_features.csv")
print("    python ml_model.py             -> HS score prediction (Ridge LOO-CV)")
print("    python seifa_analysis.py       -> SEIFA disadvantage analysis")
print()
