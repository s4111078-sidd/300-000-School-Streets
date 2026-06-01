"""
crash_trend_analysis.py
-----------------------
Deep-dives into VicRoads crash data (2021–2025) to reveal:
  1. Year-on-year ped/cyc crash trends across Darebin LGA
  2. School-hours vs off-peak breakdown for each of our 3 schools
  3. Severity profile per school (Fatal / Serious / Minor)
  4. Time-of-day distribution — when crashes happen

Output: outputs/chart_crash_trends.png

Run:    python crash_trend_analysis.py

Data source:
  outputs/crash_data_statewide.csv  (VicRoads open data, last 5 years)
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

OUT_DIR = 'outputs'
_FOOTER = '300,000 Streets  |  Regen Melbourne × RMIT University  |  Source: VicRoads Open Data'

SCHOOL_COLOURS = {
    'Reservoir HS':       '#1A476E',
    'William Ruthven SC': '#1A8FC1',
    'Preston HS':         '#C0392B',
}

SEV_COLOURS = {
    'Fatal':   '#7B241C',
    'Serious': '#C0392B',
    'Minor':   '#D35400',
}

# Normalise name variants in the raw data
SCHOOL_NAME_MAP = {
    'Preston HS':                       'Preston HS',
    'Reservoir HS':                     'Reservoir HS',
    'William Ruthven SC':               'William Ruthven SC',
    'William Ruthven Secondary College':'William Ruthven SC',
}

# School hours: Mon–Fri, 7:30–9:00 AM or 2:30–4:30 PM
def _is_school_hours(row):
    try:
        t  = pd.to_datetime(row['ACCIDENT_TIME'], format='%H:%M:%S')
        h, m = t.hour, t.minute
        wday = int(row['DAY_OF_WEEK'])        # 1=Sun, 2=Mon … 6=Fri, 7=Sat
        if wday in (1, 7):
            return False
        morning   = (h == 7 and m >= 30) or h == 8
        afternoon = (h == 14 and m >= 30) or h in (15, 16) or (h == 16 and m == 0)
        return morning or afternoon
    except Exception:
        return False


def _severity_label(code):
    if code == 1:
        return 'Fatal'
    elif code == 2:
        return 'Serious'
    else:
        return 'Minor'


def load_data():
    path = os.path.join(OUT_DIR, 'crash_data_statewide.csv')
    df = pd.read_csv(path, low_memory=False)
    df['year']         = pd.to_datetime(df['ACCIDENT_DATE'], errors='coerce').dt.year
    df['hour']         = pd.to_datetime(df['ACCIDENT_TIME'], format='%H:%M:%S',
                                        errors='coerce').dt.hour
    df['sev_label']    = df['SEVERITY'].apply(_severity_label)
    df['school_hours'] = df.apply(_is_school_hours, axis=1)

    # Darebin LGA subset
    darebin = df[df['LGA_NAME'].str.upper() == 'DAREBIN'].copy()

    # Our 3 schools subset (normalise name variants)
    our = df[df['nearest_school'].isin(SCHOOL_NAME_MAP.keys())].copy()
    our['school_short'] = our['nearest_school'].map(SCHOOL_NAME_MAP)

    return df, darebin, our


def plot_trends(darebin, our):
    years = sorted(darebin['year'].dropna().unique().astype(int))

    fig = plt.figure(figsize=(17, 12))
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.50, wspace=0.38)

    # ── Panel 1: Darebin LGA — crashes by year ──────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#FAFAFA')

    sev_order = ['Fatal', 'Serious', 'Minor']
    bottoms   = np.zeros(len(years))
    for sev in sev_order:
        vals = [int((darebin[(darebin['year'] == y) &
                             (darebin['sev_label'] == sev)]).shape[0])
                for y in years]
        bars = ax1.bar(years, vals, bottom=bottoms,
                       color=SEV_COLOURS[sev], edgecolor='white',
                       linewidth=0.8, label=sev)
        for bar, v, bot in zip(bars, vals, bottoms):
            if v > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, bot + v / 2,
                         str(v), ha='center', va='center',
                         fontsize=9, fontweight='bold', color='white')
        bottoms = bottoms + np.array(vals, dtype=float)

    for i, (yr, tot) in enumerate(zip(years, bottoms)):
        ax1.text(yr, tot + 0.5, str(int(tot)), ha='center', va='bottom',
                 fontsize=10, fontweight='bold', color='#1A1A1A')

    ax1.set_xticks(years)
    ax1.set_xlabel('Year', fontsize=10)
    ax1.set_ylabel('Ped / Cyc crashes', fontsize=10)
    ax1.set_title('Darebin LGA — Ped/Cyc Crashes by Year\n(all schools, 400 m buffer)',
                  fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, framealpha=0.8, title='Severity')
    ax1.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # ── Panel 2: Our 3 schools — crashes by year ────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#FAFAFA')

    school_order = ['Preston HS', 'Reservoir HS', 'William Ruthven SC']
    x      = np.arange(len(years))
    width  = 0.25
    offset = [-width, 0, width]

    for sc, off in zip(school_order, offset):
        vals = [int((our[(our['year'] == y) &
                         (our['school_short'] == sc)]).shape[0])
                for y in years]
        bars = ax2.bar(x + off, vals, width,
                       color=SCHOOL_COLOURS[sc], edgecolor='white',
                       label=sc, alpha=0.9)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2,
                         v + 0.05, str(v),
                         ha='center', va='bottom',
                         fontsize=9, fontweight='bold',
                         color=SCHOOL_COLOURS[sc])

    ax2.set_xticks(x)
    ax2.set_xticklabels(years)
    ax2.set_xlabel('Year', fontsize=10)
    ax2.set_ylabel('Ped / Cyc crashes', fontsize=10)
    ax2.set_title('Our 3 Schools — Crashes by Year\n(within 400 m of school gate)',
                  fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9, framealpha=0.8)
    ax2.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # ── Panel 3: School hours vs off-peak per school ────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor('#FAFAFA')

    x3    = np.arange(len(school_order))
    w3    = 0.35
    sh_c  = '#1A476E'
    off_c = '#BDC3C7'

    sh_vals  = [int(our[(our['school_short'] == sc) &  our['school_hours']].shape[0])
                for sc in school_order]
    off_vals = [int(our[(our['school_short'] == sc) & ~our['school_hours']].shape[0])
                for sc in school_order]

    b1 = ax3.bar(x3 - w3 / 2, sh_vals,  w3, label='School hours\n(7:30–9am / 2:30–4:30pm)',
                 color=sh_c, edgecolor='white')
    b2 = ax3.bar(x3 + w3 / 2, off_vals, w3, label='Outside school hours',
                 color=off_c, edgecolor='white')

    for bar, v in zip(list(b1) + list(b2), sh_vals + off_vals):
        if v > 0:
            ax3.text(bar.get_x() + bar.get_width() / 2, v + 0.05, str(v),
                     ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax3.set_xticks(x3)
    ax3.set_xticklabels(school_order, fontsize=10, fontweight='bold')
    ax3.set_ylabel('Number of crashes', fontsize=10)
    ax3.set_title('Crash Timing — School Hours vs Off-Peak\n(our 3 schools, 2021–2025)',
                  fontsize=11, fontweight='bold')
    ax3.legend(fontsize=9, framealpha=0.8)
    ax3.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax3.set_axisbelow(True)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)

    # ── Panel 4: Time-of-day distribution (Darebin) ─────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor('#FAFAFA')

    hour_counts = darebin.groupby('hour').size().reindex(range(24), fill_value=0)
    bar_colours = []
    for h in range(24):
        if (7 <= h <= 8) or (14 <= h <= 16):
            bar_colours.append('#C0392B')   # school hours
        elif 6 <= h <= 9 or 16 <= h <= 19:
            bar_colours.append('#D35400')   # peak hours
        else:
            bar_colours.append('#BDC3C7')   # off-peak

    ax4.bar(range(24), hour_counts.values, color=bar_colours, edgecolor='white')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)],
                        rotation=45, fontsize=8)
    ax4.set_xlabel('Hour of day', fontsize=10)
    ax4.set_ylabel('Number of crashes (Darebin LGA)', fontsize=10)
    ax4.set_title('Crash Time-of-Day Distribution\nDarebin LGA  (2021–2025)',
                  fontsize=11, fontweight='bold')

    legend_els = [
        mpatches.Patch(color='#C0392B', label='School hours (7:30–9am / 2:30–4:30pm)'),
        mpatches.Patch(color='#D35400', label='General peak hours'),
        mpatches.Patch(color='#BDC3C7', label='Off-peak'),
    ]
    ax4.legend(handles=legend_els, fontsize=8, framealpha=0.8)
    ax4.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax4.set_axisbelow(True)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)

    fig.suptitle(
        'Crash Trend Analysis — Pedestrian & Cyclist Crashes (2021–2025)\n'
        'City of Darebin  |  VicRoads Open Data',
        fontsize=13, fontweight='bold', y=1.01,
    )
    plt.figtext(0.99, 0.005, _FOOTER, ha='right', fontsize=7.5, color='#888888')

    out = os.path.join(OUT_DIR, 'chart_crash_trends.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    return out


def print_findings(darebin, our):
    print('\n' + '='*60)
    print('  CRASH TREND ANALYSIS — KEY FINDINGS')
    print('='*60)

    years = sorted(darebin['year'].dropna().unique().astype(int))
    print(f"\n  Darebin LGA ped/cyc crashes ({years[0]}–{years[-1]}):")
    for yr in years:
        n = int((darebin['year'] == yr).sum())
        print(f"    {yr}: {n} crashes")

    print(f"\n  Total crashes within 400 m of our 3 schools: {len(our)}")
    for sc in ['Preston HS', 'Reservoir HS', 'William Ruthven SC']:
        sub = our[our['school_short'] == sc]
        sh  = sub[sub['school_hours']]
        print(f"    {sc}: {len(sub)} total  ({len(sh)} during school hours)")

    # Trend direction
    yr_counts = darebin.groupby('year').size()
    if len(yr_counts) >= 2:
        first, last = yr_counts.iloc[0], yr_counts.iloc[-1]
        trend = 'increasing' if last > first else 'decreasing' if last < first else 'stable'
        print(f"\n  Darebin LGA crash trend: {trend} "
              f"({first} in {yr_counts.index[0]} → {last} in {yr_counts.index[-1]})")

    # Most dangerous hour in Darebin
    peak_hour = darebin['hour'].value_counts().idxmax()
    print(f"  Peak crash hour (Darebin LGA): {peak_hour:02d}:00")
    print('='*60 + '\n')


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  300,000 Streets — Crash Trend Analysis')
    print('='*60)

    _df, darebin, our = load_data()
    print(f"  Loaded {len(_df):,} statewide crashes  "
          f"|  {len(darebin)} Darebin  |  {len(our)} at our 3 schools")

    out = plot_trends(darebin, our)
    print(f"  Chart saved → {out}")

    print_findings(darebin, our)
