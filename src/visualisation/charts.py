"""
Static PNG chart generation — safety scores, hazard severity, score breakdown, demographics.

Run standalone:  python -m src.visualisation.charts
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

_FOOTER = '300,000 Streets  |  Regen Melbourne x RMIT University'


def plot_safety_scores(df: pd.DataFrame, out_dir: str) -> str:
    """Chart 1 — grouped bar chart of FAS/CSS/EEI/CIS/CYS per school."""
    schools  = df['School_short'].tolist()
    fas_vals = df['FAS'].tolist()
    css_vals = df['CSS'].tolist()
    eei_vals = df['EEI'].tolist()
    cis_vals = df['CIS'].tolist()
    cys_vals = df['CYS'].tolist()
    x     = np.arange(len(schools))
    width = 0.15

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#FAFAFA')

    b1 = ax.bar(x - 2*width, fas_vals, width, label='Footpath Score (FAS)',        color='#1A1A1A', edgecolor='white')
    b2 = ax.bar(x - 1*width, css_vals, width, label='Crossing Score (CSS)',         color='#555555', edgecolor='white')
    b3 = ax.bar(x + 0*width, eei_vals, width, label='Environment Score (EEI)',      color='#999999', edgecolor='white')
    b4 = ax.bar(x + 1*width, cis_vals, width, label='Cycling Infra Score (CIS)',    color='#27AE60', edgecolor='white')
    b5 = ax.bar(x + 2*width, cys_vals, width, label='Cycling Safety Score (CYS)',   color='#1A8FC1', edgecolor='white')

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
    plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
    plt.tight_layout()
    out = os.path.join(out_dir, 'chart1_safety_scores.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    return out


def plot_hazard_severity(df: pd.DataFrame, out_dir: str) -> str:
    """Chart 2 — stacked bar chart of hazard severity counts per school."""
    sev_order   = ['Major',   'Moderate', 'Minor']
    sev_colours = ['#C0392B', '#D35400',  '#1E8449']
    school_list = df['School_short'].unique()
    counts = {}
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
    plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
    plt.tight_layout()
    out = os.path.join(out_dir, 'chart2_hazard_severity.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    return out


def plot_score_breakdown(df: pd.DataFrame, out_dir: str) -> str:
    """Chart 3 — per-school bar panels with individual score breakdown."""
    metric_labels = ['Footpath\n(FAS)', 'Crossing\n(CSS)', 'Environment\n(EEI)',
                     'Cycling Infra\n(CIS)', 'Cycling Safety\n(CYS)']
    n = len(df)
    fig, axes = plt.subplots(1, n, figsize=(8*n, 6), sharey=True)
    fig.patch.set_facecolor('white')
    if n == 1:
        axes = [axes]

    for ax, (_, row) in zip(axes, df.iterrows()):
        raw_vals = [row['FAS'], row['CSS'], row['EEI'], row['CIS'], row['CYS']]
        school   = row['School_short']
        sev      = row['Sev_clean']
        bar_colours = []
        plot_vals   = []
        for i, v in enumerate(raw_vals):
            if pd.isna(v):
                plot_vals.append(0)
                bar_colours.append('#CCCCCC')
            else:
                v = float(v)
                plot_vals.append(v)
                if i == 3:
                    bar_colours.append('#27AE60' if v >= 6 else '#D35400' if v >= 4 else '#C0392B')
                elif i == 4:
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
        badge_c = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}.get(sev, '#888888')
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
    plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=8, color='#888888')
    plt.tight_layout()
    out = os.path.join(out_dir, 'chart3_score_breakdown.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    return out


def plot_demographics(demo_file: str, out_dir: str) -> str:
    """Chart 4 — suburb demographics from ABS Census 2021 data."""
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
        bars = ax.bar(suburbs, vals, color=colour, edgecolor='white', width=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + max(vals)*0.02,
                    str(val), ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color='#1A1A1A')
        ax.set_title(metric, fontsize=9, fontweight='bold', color='#1A1A1A', pad=8)
        ax.set_ylim(0, max(vals) * 1.3)
        ax.set_xticks(range(len(suburbs)))
        ax.set_xticklabels(suburbs, fontsize=9, fontweight='bold')
        ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')

    fig.suptitle('Suburb Demographics — Darebin  (ABS Census 2021)',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.figtext(0.99, 0.01, '300,000 Streets  |  Source: ABS Census 2021',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()
    out = os.path.join(out_dir, 'chart4_demographics.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()

    print('\n      KEY INSIGHTS:')
    for _, row in demo_df.iterrows():
        children = round(row['Total population'] * row['% children aged 5-17'] / 100)
        print(f"      {row['Suburb']}:")
        print(f"        ~{children:,} school-age children")
        print(f"        ${row['Median weekly household income ($)']:,}/week median income")
        print(f"        {row['% households no car']}% households have no car")
        print(f"        {row['% working full time (35hrs+)']}% parents working full time")

    return out
