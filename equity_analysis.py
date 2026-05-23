"""
equity_analysis.py
------------------
Joins SEIFA 2021 socioeconomic disadvantage data with Healthy Streets scores
to show whether the most disadvantaged school catchments also have the worst
pedestrian safety outcomes.

Output: outputs/chart_equity_seifa.png

Run:    python equity_analysis.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

OUT_DIR = 'outputs'
_FOOTER = '300,000 Streets  |  Regen Melbourne × RMIT University  |  ABS SEIFA 2021'

SCHOOL_COLOURS = {
    'Reservoir HS':       '#1A476E',
    'William Ruthven SC': '#1A8FC1',
    'Preston HS':         '#C0392B',
}

HS_CODES = ['HS1', 'HS2', 'HS3', 'HS4', 'HS5', 'HS6', 'HS7', 'HS8', 'HS9', 'HS10']
HS_LABELS_SHORT = [
    'Footpath\naccess', 'Easy to\ncross', 'Shade &\nshelter', 'Rest\nspots',
    'Not too\nnoisy', 'Active\ntravel', 'Feel\nsafe', 'Things\nto see',
    'Feel\nrelaxed', 'Clean\nair',
]


def load_and_join():
    seifa = pd.read_csv(os.path.join(OUT_DIR, 'seifa_darebin.csv'))
    hs    = pd.read_csv(os.path.join(OUT_DIR, 'hs_scores.csv'))
    df    = seifa.merge(hs, on='School', how='inner')
    df    = df.sort_values('IRSD_Decile').reset_index(drop=True)
    return df


def plot_equity(df):
    fig = plt.figure(figsize=(16, 11))
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.50, wspace=0.38,
                           height_ratios=[1.1, 1])

    schools  = df['School_short'].tolist()
    colours  = [SCHOOL_COLOURS.get(s, '#888888') for s in schools]
    x        = np.arange(len(schools))
    width    = 0.35

    # ── Panel 1: SEIFA Decile vs HS Overall side-by-side bars ──────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#FAFAFA')

    b1 = ax1.bar(x - width / 2, df['IRSD_Decile'], width,
                 label='SEIFA IRSD Decile', color='#7F8C8D',
                 edgecolor='white', alpha=0.85)
    b2 = ax1.bar(x + width / 2, df['HS_overall'], width,
                 label='HS Overall Score', color=colours, edgecolor='white')

    for bar, val in zip(b1, df['IRSD_Decile']):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.1,
                 f'{val:.1f}', ha='center', va='bottom',
                 fontsize=10, fontweight='bold', color='#555555')
    for bar, val in zip(b2, df['HS_overall']):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.1,
                 f'{val:.1f}', ha='center', va='bottom',
                 fontsize=10, fontweight='bold', color='#1A1A1A')

    ax1.axhline(6, color='#C0392B', linewidth=0.9, linestyle='--', alpha=0.6)
    ax1.text(len(schools) - 0.05, 6.2, 'HS threshold (6.0)',
             ha='right', fontsize=8, color='#C0392B', style='italic')
    ax1.set_xticks(x)
    ax1.set_xticklabels(schools, fontsize=10, fontweight='bold')
    ax1.set_ylim(0, 12)
    ax1.set_ylabel('Score / Decile  (0 – 10)', fontsize=10)
    ax1.set_title('Disadvantage Decile vs Safety Score\n(sorted most → least disadvantaged)',
                  fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, framealpha=0.8, loc='upper left')
    ax1.yaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # ── Panel 2: Scatter — IRSD Decile vs HS Overall ───────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#FAFAFA')

    for _, row in df.iterrows():
        c = SCHOOL_COLOURS.get(row['School_short'], '#888888')
        ax2.scatter(row['IRSD_Decile'], row['HS_overall'],
                    color=c, s=200, zorder=5,
                    edgecolors='white', linewidths=1.5)
        ax2.annotate(row['School_short'],
                     (row['IRSD_Decile'], row['HS_overall']),
                     textcoords='offset points', xytext=(10, 4),
                     fontsize=9, fontweight='bold', color=c)

    # Shaded quadrants
    ax2.axhspan(0, 6, xmin=0, xmax=0.5, alpha=0.06, color='#C0392B',
                label='High risk zone')
    ax2.text(1.2, 3.0, 'Most at risk:\nhigh disadvantage\n+ poor safety',
             fontsize=7.5, color='#C0392B', style='italic', alpha=0.8)

    ax2.set_xlabel('IRSD Decile  (1 = most disadvantaged)', fontsize=10)
    ax2.set_ylabel('HS Overall Score  (10 = safest streets)', fontsize=10)
    ax2.set_title('Safety Score vs Socioeconomic Disadvantage\n(each point = one school catchment)',
                  fontsize=11, fontweight='bold')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axhline(6, color='#C0392B', linewidth=0.8, linestyle='--', alpha=0.5)
    ax2.axvline(5, color='#7F8C8D', linewidth=0.8, linestyle='--', alpha=0.5)
    ax2.text(0.5, 6.2, 'HS threshold', fontsize=8, color='#C0392B', style='italic')
    ax2.text(5.1, 0.4, 'National median', fontsize=8, color='#7F8C8D',
             style='italic', rotation=90, va='bottom')
    ax2.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
    ax2.xaxis.grid(True, color='#DDDDDD', linewidth=0.6)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # ── Panel 3: HS Indicator Heatmap (full width bottom row) ──────────────
    ax3 = fig.add_subplot(gs[1, :])
    hs_matrix = df[HS_CODES].values.astype(float)

    im = ax3.imshow(hs_matrix, cmap='RdYlGn', vmin=0, vmax=10, aspect='auto')

    ax3.set_xticks(range(10))
    ax3.set_xticklabels(HS_LABELS_SHORT, fontsize=9)
    ax3.set_yticks(range(len(schools)))
    ax3.set_yticklabels(schools, fontsize=10, fontweight='bold')

    for i in range(len(schools)):
        for j in range(10):
            val = hs_matrix[i, j]
            text_c = 'white' if val < 3.5 or val > 8.5 else '#1A1A1A'
            ax3.text(j, i, f'{val:.1f}', ha='center', va='center',
                     fontsize=11, fontweight='bold', color=text_c)

    ax3.set_title(
        'HS Indicator Breakdown — All 10 Indicators  '
        '(schools ordered most → least disadvantaged by IRSD)',
        fontsize=11, fontweight='bold', pad=10)

    cbar = plt.colorbar(im, ax=ax3, label='Score (0 – 10)',
                        shrink=0.55, pad=0.01)
    cbar.ax.tick_params(labelsize=8)

    # SEIFA annotation on left of heatmap
    for i, (_, row) in enumerate(df.iterrows()):
        ax3.annotate(
            f'IRSD {row["IRSD_Score_Weighted"]:.0f}  D{row["IRSD_Decile"]:.0f}',
            xy=(0, i), xycoords=('axes fraction', 'data'),
            xytext=(-5, 0), textcoords='offset points',
            ha='right', va='center', fontsize=8.5, color='#444444',
        )

    fig.suptitle(
        'Equity Analysis — Pedestrian Safety vs Socioeconomic Disadvantage\n'
        'City of Darebin  |  ABS SEIFA 2021  ×  Healthy Streets Assessment',
        fontsize=13, fontweight='bold', y=1.02,
    )
    plt.figtext(0.99, 0.005, _FOOTER, ha='right', fontsize=7.5, color='#888888')

    out = os.path.join(OUT_DIR, 'chart_equity_seifa.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    return out


def print_findings(df):
    print('\n' + '='*60)
    print('  EQUITY ANALYSIS — KEY FINDINGS')
    print('='*60)
    for _, row in df.iterrows():
        print(f"\n  {row['School_short']}")
        print(f"    IRSD Score   : {row['IRSD_Score_Weighted']:.0f}  "
              f"(Decile {row['IRSD_Decile']:.0f} / 10)")
        print(f"    HS Overall   : {row['HS_overall']:.1f} / 10")
        print(f"    Disadvantage : {row['Disadvantage_Level']}")
        below = [c for c in HS_CODES if row[c] < 6.0]
        print(f"    Indicators < 6.0 : {', '.join(below) if below else 'None'}")

    most_dis = df.loc[df['IRSD_Decile'].idxmin()]
    worst_hs = df.loc[df['HS_overall'].idxmin()]
    print('\n' + '-'*60)
    print(f"  Most disadvantaged catchment : {most_dis['School_short']} "
          f"(IRSD Decile {most_dis['IRSD_Decile']:.0f})")
    print(f"  Lowest HS overall score      : {worst_hs['School_short']} "
          f"(HS {worst_hs['HS_overall']:.1f})")

    # Positive r: higher decile (less disadvantaged) → higher HS (safer streets)
    # i.e. more disadvantaged catchments have worse safety — the key policy finding.
    corr = df['IRSD_Decile'].corr(df['HS_overall'])
    print(f"\n  Correlation (IRSD Decile × HS Overall) : r = {corr:.2f}")
    if corr > 0.3:
        print("  FINDING: More disadvantaged catchments have WORSE safety scores.")
        print("  Higher decile (less disadvantaged) = higher HS score (safer streets).")
        print("  This supports prioritised investment under the 300,000 Streets initiative.")
    elif corr < -0.3:
        print("  FINDING: More disadvantaged catchments have BETTER safety scores.")
        print("  Consider whether the sample reflects true conditions across more schools.")
    else:
        print("  FINDING: No strong linear relationship in this 3-school sample.")
        print("  Expanding to more schools would strengthen statistical inference.")
    print('='*60 + '\n')


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  300,000 Streets — Equity / SEIFA Analysis')
    print('='*60)

    df = load_and_join()
    print(f"  Joined {len(df)} schools across SEIFA + HS datasets")

    out = plot_equity(df)
    print(f"  Chart saved → {out}")

    print_findings(df)
