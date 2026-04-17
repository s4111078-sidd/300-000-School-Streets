import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import folium
import os
import warnings
warnings.filterwarnings('ignore')

# CONFIG — change filename here when CSV changes
CSV_FILE = 'school_data.csv'
OUT_DIR  = 'outputs'
os.makedirs(OUT_DIR, exist_ok=True)

# STEP 1 — LOAD AND CLEAN
print("\n" + "="*55)
print("  300,000 Streets — POC Pipeline")
print("="*55)
print("\n[1/5] Loading and cleaning data...")

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

df['FAS'] = pd.to_numeric(df['FAS'], errors='coerce')
df['CSS'] = pd.to_numeric(df['CSS'], errors='coerce')
df['EEI'] = pd.to_numeric(df['EEI'], errors='coerce')

def clean_severity(s):
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'

df['Sev_clean']     = df['Severity'].apply(clean_severity)
df['Overall_score'] = (df['FAS'] + df['CSS'] + df['EEI']) / 3

print(f"      Loaded {len(df)} rows from {CSV_FILE}")
print(f"      Schools: {df['School'].unique().tolist()}")
print()
print("      SCORES CONFIRMED:")
print(df[['School_short', 'FAS', 'CSS', 'EEI', 'Sev_clean']].to_string(index=False))

 # STEP 2 — CHART 1: SAFETY SCORES
print("\n[2/5] Generating Chart 1 — Safety Scores...")

schools  = df['School_short'].tolist()
fas_vals = df['FAS'].tolist()
css_vals = df['CSS'].tolist()
eei_vals = df['EEI'].tolist()
x        = np.arange(len(schools))
width    = 0.22

fig, ax = plt.subplots(figsize=(11, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('#FAFAFA')

b1 = ax.bar(x - width, fas_vals, width, label='Footpath Score (FAS)',    color='#1A1A1A', edgecolor='white')
b2 = ax.bar(x,         css_vals, width, label='Crossing Score (CSS)',     color='#666666', edgecolor='white')
b3 = ax.bar(x + width, eei_vals, width, label='Environment Score (EEI)', color='#AAAAAA', edgecolor='white')

for bars in [b1, b2, b3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.15,
                f'{h:.1f}', ha='center', va='bottom',
                fontsize=10, fontweight='bold', color='#1A1A1A')

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

# STEP 3 — CHART 2: HAZARD SEVERITY COUNT
print("\n[3/5] Generating Chart 2 — Hazard Severity...")

sev_order   = ['Major',   'Moderate', 'Minor']
sev_colours = ['#C0392B', '#D35400',  '#1E8449']
school_list = df['School_short'].unique()

counts  = {}
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

# STEP 4 — CHART 3: SCORE BREAKDOWN PER SCHOOL
print("\n[4/5] Generating Chart 3 — Score Breakdown...")

metric_labels = ['Footpath\n(FAS)', 'Crossing\n(CSS)', 'Environment\n(EEI)']
n   = len(df)
fig, axes = plt.subplots(1, n, figsize=(6*n, 6), sharey=True)
fig.patch.set_facecolor('white')
if n == 1:
    axes = [axes]

for ax, (_, row) in zip(axes, df.iterrows()):
    vals   = [float(row['FAS']), float(row['CSS']), float(row['EEI'])]
    school = row['School_short']
    sev    = row['Sev_clean']
    bar_colours = []
    for v in vals:
        if   v < 4: bar_colours.append('#C0392B')
        elif v < 6: bar_colours.append('#D35400')
        elif v < 8: bar_colours.append('#888888')
        else:       bar_colours.append('#1A1A1A')
    b = ax.bar(metric_labels, vals, color=bar_colours, edgecolor='white', width=0.5)
    for bar, val in zip(b, vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.15,
                f'{val:.1f}', ha='center', va='bottom',
                fontsize=12, fontweight='bold', color='#1A1A1A')
    ax.set_ylim(0, 12)
    ax.set_title(school, fontsize=11, fontweight='bold', pad=10)
    ax.axhline(y=6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.text(2.3, 6.15, '6.0', fontsize=8, color='#C0392B', va='bottom')
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

 # STEP 5 — INTERACTIVE MAP
print("\n[5/5] Generating Interactive Map...")

centre_lat = df['Latitude'].mean()
centre_lon = df['Longitude'].mean()
m = folium.Map(location=[centre_lat, centre_lon],
               zoom_start=14, tiles='CartoDB positron', control_scale=True)

school_gates = {
    'Reservoir High School':            {'lat':-37.7224,   'lon':145.0294,  'addr':'855 Plenty Rd, Reservoir VIC 3073'},
    'William Ruthven Secondary College':{'lat':-37.69654,  'lon':145.00299, 'addr':'60 Merrilands Rd, Reservoir VIC 3073'},
    'Preston High School':              {'lat':-37.7417,   'lon':145.0071,  'addr':'2-16 Cooma St, Preston VIC 3072'},
}
folium_sev = {'Major':'red','Moderate':'orange','Minor':'green','Unknown':'gray'}

for name, info in school_gates.items():
    folium.Marker(
        location=[info['lat'], info['lon']],
        popup=folium.Popup(f"<b>{name}</b><br>{info['addr']}<br><i>School gate</i>", max_width=240),
        tooltip=name,
        icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
    ).add_to(m)
    folium.Circle(location=[info['lat'],info['lon']], radius=400,
                  color='#333333', weight=1.5, fill=True, fill_opacity=0.04,
                  tooltip='400m buffer').add_to(m)
    folium.Circle(location=[info['lat'],info['lon']], radius=800,
                  color='#888888', weight=1, fill=True, fill_opacity=0.02,
                  tooltip='800m buffer', dash_array='6').add_to(m)

for _, row in df.iterrows():
    lat = row['Latitude']
    lon = row['Longitude']
    if pd.isna(lat) or pd.isna(lon):
        continue
    sev    = row['Sev_clean']
    school = row['School']
    street = row['Street']
    fas    = row['FAS']
    css    = row['CSS']
    eei    = row['EEI']
    hazards = str(row['Hazard_types']) if pd.notna(row['Hazard_types']) else 'Not recorded'
    rec     = str(row['Rec_type'])     if pd.notna(row['Rec_type'])     else 'Not recorded'
    pri     = str(row['Priority'])     if pd.notna(row['Priority'])     else 'Not recorded'
    popup_html = f"""
    <div style="font-family:Arial;font-size:12px;min-width:230px">
      <b style="font-size:13px">{school}</b><br>
      <span style="color:#666">{street}</span><br>
      <hr style="margin:5px 0">
      <b>Severity:</b> <span style="color:{folium_sev.get(sev,'gray')}">{sev}</span><br>
      <b>FAS:</b> {fas:.1f} &nbsp; <b>CSS:</b> {css:.1f} &nbsp; <b>EEI:</b> {eei:.1f}<br>
      <hr style="margin:5px 0">
      <b>Hazards:</b><br><span style="color:#555;font-size:11px">{hazards}</span><br>
      <hr style="margin:5px 0">
      <b>Recommendation:</b><br><span style="font-size:11px">{rec}</span><br>
      <b>Priority:</b> {pri}
    </div>"""
    folium.CircleMarker(
        location=[lat, lon], radius=12,
        color='white', weight=2, fill=True,
        fill_color=folium_sev.get(sev,'gray'), fill_opacity=0.9,
        popup=folium.Popup(popup_html, max_width=270),
        tooltip=f"{school} - {street} ({sev})"
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:12px 16px;border-radius:8px;
     border:1px solid #ccc;font-family:Arial;font-size:12px;">
  <b>300,000 Streets</b><br>
  <span style="color:#666;font-size:11px">Hazard Severity</span><br><br>
  <span style="color:#C0392B">&#9679;</span> Major<br>
  <span style="color:#D35400">&#9679;</span> Moderate<br>
  <span style="color:#1E8449">&#9679;</span> Minor<br>
  <span style="color:#333">&#9670;</span> School gate<br>
  &#9711; 400m / 800m buffer<br><br>
  <span style="color:#999;font-size:10px">Click any point for details</span>
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))
out_map = os.path.join(OUT_DIR, 'map_interactive.html')
m.save(out_map)
print(f"      Saved -> {out_map}")


# ── AUTOMATIC RECOMMENDATION ENGINE ───────────────────────

def generate_recommendation(row):
    recs = []

    # Footpath rules
    if row['Footpath_present'] in ['No footpath at all',
                                    'Partial or broken — gaps present']:
        recs.append({
            'hazard'        : 'Missing or broken footpath',
            'recommendation': 'Construct continuous concrete footpath minimum 1.8m wide',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    if float(row['Footpath_width']) < 1.5:
        recs.append({
            'hazard'        : 'Footpath below minimum width standard',
            'recommendation': 'Widen footpath to minimum 1.5m standard',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Crossing rules
    if row['Crossing_present'] in ['No crossing at all',
                                    'Yes — informal / unmarked only']:
        recs.append({
            'hazard'        : 'No formal pedestrian crossing',
            'recommendation': 'Install raised zebra crossing with tactile pavers',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    if float(row['Crossing_dist']) > 150:
        recs.append({
            'hazard'        : 'Nearest crossing too far from school gate',
            'recommendation': 'Install additional pedestrian crossing within 50m of school gate — existing crossing at 200m is too far for safe student use',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    if row['Tactile'] == 'No':
        recs.append({
            'hazard'        : 'No tactile indicators at crossing',
            'recommendation': 'Install tactile ground surface indicators on both sides',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # School zone rules
    if row['School_zone'] == 'No school zone at all':
        recs.append({
            'hazard'        : 'No school zone signage present',
            'recommendation': 'Install school zone signs with 40km/h speed restriction',
            'priority'      : 'High',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Traffic calming rules
    if (row['Traffic_calming'] == 'No traffic calming at all' and
        '3 or more' in str(row['Lanes'])):
        recs.append({
            'hazard'        : 'No traffic calming on multi-lane road near school',
            'recommendation': 'Install speed humps or raised intersection near school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Cycling rules
    if row['Cycling_infra'] == 'No cycling infrastructure':
        recs.append({
            'hazard'        : 'No cycling infrastructure present',
            'recommendation': 'Install painted bike lane or shared path along school frontage',
            'priority'      : 'Low',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Long-term — 1 to 3 years'
        })

    # Lighting rules
    if row['Lighting'] in ['Poor — dim or infrequent lights', 'No street lighting']:
        recs.append({
            'hazard'        : 'Poor street lighting on walking route',
            'recommendation': 'Install LED street lights along walking route to school',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    # Vegetation rules
    if 'Vegetation' in str(row['Hazard_types']):
        recs.append({
            'hazard'        : 'Vegetation blocking footpath or crossing sightlines',
            'recommendation': 'Remove and trim vegetation obstructing pedestrian path and crossing visibility',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year'
        })

    return recs


# Apply to all rows and build recommendations dataframe
all_recs = []
for _, row in df.iterrows():
    recs = generate_recommendation(row)
    for rec in recs:
        all_recs.append({
            'School'        : row['School'],
            'Location'      : row['Street'],
            'Severity'      : row['Sev_clean'],
            'FAS'           : row['FAS'],
            'CSS'           : row['CSS'],
            'Hazard'        : rec['hazard'],
            'Recommendation': rec['recommendation'],
            'Priority'      : rec['priority'],
            'Cost'          : rec['cost'],
            'Timeframe'     : rec['timeframe'],
        })

rec_df = pd.DataFrame(all_recs)

# Save recommendations to CSV
rec_out = os.path.join(OUT_DIR, 'recommendations.csv')
rec_df.to_csv(rec_out, index=False)

print(f"\n  Recommendations generated: {len(rec_df)} total")
print(rec_df[['School','Hazard','Priority']].to_string(index=False))
print(f"\n  Saved -> {rec_out}")
 # DONE
print("\n" + "="*55)
print("  ALL OUTPUTS SAVED TO /outputs/")
print("="*55)
print("  chart1_safety_scores.png    - Bar chart")
print("  chart2_hazard_severity.png  - Severity count")
print("  chart3_score_breakdown.png  - Per school breakdown")
print("  map_interactive.html        - Open in browser")
print("="*55)
print("\n  Final scores:")
print(df[['School_short','FAS','CSS','EEI','Sev_clean','Overall_score']]
      .rename(columns={'School_short':'School','Sev_clean':'Severity',
                       'Overall_score':'Overall'})
      .to_string(index=False))
print("\n  To update: replace CSV and re-run python poc_pipeline.py\n")