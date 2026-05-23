"""
scenario_analyzer.py
--------------------
What-if scenario analysis for the 300,000 Streets pipeline.

Loads the trained Ridge model (outputs/hs_predictor.pkl), applies one or more
physical interventions to a school's feature vector, and shows how HS indicator
scores and severity classification would change.

Usage
-----
  # List available schools and interventions
  python scenario_analyzer.py --list

  # Run a single intervention
  python scenario_analyzer.py --school "Preston HS" --interventions pedestrian_crossing

  # Combine multiple interventions
  python scenario_analyzer.py --school "Reservoir HS" \
      --interventions pedestrian_crossing speed_reduction footpath

  # Run all interventions individually and rank by impact
  python scenario_analyzer.py --school "Preston HS" --rank-all

  # Run all interventions for all schools
  python scenario_analyzer.py --all-schools --rank-all

  # Save chart to custom path
  python scenario_analyzer.py --school "Preston HS" \
      --interventions bike_lane --out outputs/my_scenario.png
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

from src.scenarios.engine        import run_scenario, HS_CODES
from src.scenarios.interventions import INTERVENTIONS, list_interventions

OUT_DIR = 'outputs'
_FOOTER = '300,000 Streets  |  Regen Melbourne × RMIT University  |  Scenario Analysis'

SCHOOL_COLOURS = {
    'Reservoir HS':       '#1A476E',
    'William Ruthven SC': '#1A8FC1',
    'Preston HS':         '#C0392B',
}
SCHOOLS = ['Preston HS', 'Reservoir HS', 'William Ruthven SC']

HS_LABELS = [
    'HS1\nFootpath', 'HS2\nCross', 'HS3\nShade', 'HS4\nRest',
    'HS5\nNoise', 'HS6\nActive', 'HS7\nSafe', 'HS8\nThings',
    'HS9\nRelaxed', 'HS10\nAir',
]

SEV_COLOUR = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}


# ── Printing ────────────────────────────────────────────────────────────────────

def print_results(result: dict) -> None:
    school = result['school']
    b      = result['baseline']
    s      = result['scenario']
    d      = result['deltas']

    sev_b = b['severity']
    sev_s = s['severity']
    sev_arrow = '' if sev_b == sev_s else f'  →  {sev_s}'

    print('\n' + '='*64)
    print(f"  SCENARIO: {school}")
    for label in result['interventions']:
        print(f"    + {label}")
    print('='*64)

    print(f"\n  {'Indicator':<12} {'Before':>7} {'After':>7} {'Change':>8}")
    print('  ' + '-'*40)
    for code in HS_CODES:
        delta  = d[code]
        arrow  = '+' if delta > 0 else ''
        marker = '  ▲' if delta >= 0.5 else ('  ▼' if delta <= -0.5 else '')
        print(f"  {code:<12} {b[code]:>7.1f} {s[code]:>7.1f} "
              f"{arrow}{delta:>+6.2f}{marker}")
    print('  ' + '-'*40)
    print(f"  {'OVERALL':<12} {b['HS_overall']:>7.1f} "
          f"{s['HS_overall']:>7.1f} {d['HS_overall']:>+7.2f}")
    print(f"\n  Severity: {sev_b}{sev_arrow}")

    if result['feature_changes']:
        print('\n  Feature changes applied:')
        for feat, (before, after) in result['feature_changes'].items():
            print(f"    {feat:<35}  {before:.1f}  →  {after:.1f}")

    print('\n  Cost summary:')
    for label, cost, timeframe in result['cost_summary']:
        print(f"    {label}")
        print(f"      Cost: {cost}  |  Timeframe: {timeframe}")
    print('='*64 + '\n')


# ── Chart ───────────────────────────────────────────────────────────────────────

def plot_scenario(result: dict, out_path: str) -> str:
    school = result['school']
    b      = result['baseline']
    s      = result['scenario']
    d      = result['deltas']
    colour = SCHOOL_COLOURS.get(school, '#555555')

    base_vals     = [b[c] for c in HS_CODES]
    scenario_vals = [s[c] for c in HS_CODES]
    delta_vals    = [d[c] for c in HS_CODES]

    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38,
                           width_ratios=[1.6, 1])

    # ── Left: before / after horizontal bars ────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor('#FAFAFA')

    y  = np.arange(len(HS_CODES))
    h  = 0.32

    bars_b = ax1.barh(y + h/2, base_vals, h,
                      color='#BDC3C7', edgecolor='white', label='Before', zorder=3)
    bars_s = ax1.barh(y - h/2, scenario_vals, h,
                      color=colour, edgecolor='white', alpha=0.9,
                      label='After (predicted)', zorder=3)

    for bar, val in zip(bars_b, base_vals):
        ax1.text(val + 0.08, bar.get_y() + bar.get_height()/2,
                 f'{val:.1f}', va='center', fontsize=8.5,
                 color='#555555', fontweight='bold')
    for bar, val, delta in zip(bars_s, scenario_vals, delta_vals):
        prefix = '+' if delta > 0 else ''
        label  = f'{val:.1f}  ({prefix}{delta:.2f})'
        ax1.text(val + 0.08, bar.get_y() + bar.get_height()/2,
                 label, va='center', fontsize=8.5,
                 color=colour, fontweight='bold')

    ax1.axvline(6, color='#C0392B', linewidth=0.9, linestyle='--',
                alpha=0.6, zorder=2, label='Good threshold (6.0)')
    ax1.set_yticks(y)
    ax1.set_yticklabels(HS_LABELS, fontsize=9)
    ax1.set_xlim(0, 13)
    ax1.set_xlabel('HS Score  (0 = worst  |  10 = best)', fontsize=10)
    ax1.set_title(f'{school} — Before vs After\n'
                  f'Overall: {b["HS_overall"]:.1f} → {s["HS_overall"]:.1f}  '
                  f'({d["HS_overall"]:+.2f})',
                  fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, framealpha=0.8, loc='lower right')
    ax1.xaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Severity badges
    sev_b_c = SEV_COLOUR.get(b['severity'], '#888')
    sev_s_c = SEV_COLOUR.get(s['severity'], '#888')
    ax1.text(12.5, len(HS_CODES) - 0.5,
             f'Before: {b["severity"]}', ha='right', va='top',
             fontsize=9, fontweight='bold', color=sev_b_c,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                       edgecolor=sev_b_c, linewidth=1.5))
    ax1.text(12.5, len(HS_CODES) - 1.3,
             f'After: {s["severity"]}', ha='right', va='top',
             fontsize=9, fontweight='bold', color=sev_s_c,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                       edgecolor=sev_s_c, linewidth=1.5))

    # ── Right: delta bar chart ───────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor('#FAFAFA')

    bar_colours = ['#1E8449' if v > 0 else '#C0392B' if v < 0 else '#BDC3C7'
                   for v in delta_vals]
    bars_d = ax2.barh(y, delta_vals, 0.5,
                      color=bar_colours, edgecolor='white', zorder=3)

    for bar, val in zip(bars_d, delta_vals):
        if abs(val) > 0.01:
            x_pos  = val + 0.05 if val >= 0 else val - 0.05
            ha     = 'left' if val >= 0 else 'right'
            prefix = '+' if val > 0 else ''
            ax2.text(x_pos, bar.get_y() + bar.get_height()/2,
                     f'{prefix}{val:.2f}', va='center', ha=ha,
                     fontsize=9, fontweight='bold',
                     color='#1E8449' if val > 0 else '#C0392B')

    ax2.axvline(0, color='#1A1A1A', linewidth=0.8, zorder=2)
    ax2.set_yticks(y)
    ax2.set_yticklabels(HS_LABELS, fontsize=9)
    ax2.set_xlabel('Score change (Δ)', fontsize=10)
    ax2.set_title('Predicted change\nper indicator', fontsize=11, fontweight='bold')
    ax2.xaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    legend_els = [
        mpatches.Patch(color='#1E8449', label='Improvement'),
        mpatches.Patch(color='#C0392B', label='Decline'),
        mpatches.Patch(color='#BDC3C7', label='No change'),
    ]
    ax2.legend(handles=legend_els, fontsize=8.5, framealpha=0.8)

    # ── Title ────────────────────────────────────────────────────────────────
    iv_labels = '\n'.join(f'  + {lbl}' for lbl in result['interventions'])
    fig.suptitle(
        f'Scenario Analysis — {school}\n{iv_labels}',
        fontsize=12, fontweight='bold', y=1.02,
    )
    plt.figtext(0.99, 0.005, _FOOTER, ha='right', fontsize=7.5, color='#888888')

    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    return out_path


# ── Rank-all mode ───────────────────────────────────────────────────────────────

def rank_all(school: str) -> None:
    """Run every intervention individually and rank by HS_overall improvement."""
    print(f'\n  Ranking all interventions for {school}...')
    rows = []
    for key, iv in INTERVENTIONS.items():
        try:
            result = run_scenario(school, [key])
            rows.append({
                'key'       : key,
                'label'     : iv['label'],
                'delta_hs'  : result['deltas']['HS_overall'],
                'before_sev': result['baseline']['severity'],
                'after_sev' : result['scenario']['severity'],
                'cost'      : iv['cost'],
                'timeframe' : iv['timeframe'],
                'hs_target' : iv['hs_target'],
            })
        except Exception as e:
            print(f"    Warning: {key} failed — {e}")

    df = pd.DataFrame(rows).sort_values('delta_hs', ascending=False)

    print(f'\n{"="*72}')
    print(f'  INTERVENTION RANKING — {school}  (by predicted ΔHS overall)')
    print(f'{"="*72}')
    print(f"  {'#':<3} {'Intervention':<38} {'ΔHS':>6} {'Severity change':<20} {'Cost'}")
    print('  ' + '-'*70)
    for i, (_, row) in enumerate(df.iterrows(), 1):
        sev_chg = (f"{row['before_sev']} → {row['after_sev']}"
                   if row['before_sev'] != row['after_sev']
                   else '—')
        print(f"  {i:<3} {row['label']:<38} {row['delta_hs']:>+6.2f}  "
              f"{sev_chg:<20}  {row['cost'].split('(')[0].strip()}")
    print(f'{"="*72}')
    print('  Note: severity changes in rank-all mode may reflect model noise')
    print('  (n=3 training schools). Focus on ΔHS overall for comparison.')
    print(f'{"="*72}\n')

    # Save ranking chart
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#FAFAFA')

    df_plot  = df.reset_index(drop=True)
    colours  = ['#1E8449' if v > 0 else '#C0392B' for v in df_plot['delta_hs']]
    y_pos    = np.arange(len(df_plot))

    bars = ax.barh(y_pos, df_plot['delta_hs'], 0.55,
                   color=colours, edgecolor='white', zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_plot['label'], fontsize=9)
    ax.axvline(0, color='#1A1A1A', linewidth=0.8)

    for bar, val in zip(bars, df_plot['delta_hs']):
        x_pos = val + 0.005 if val >= 0 else val - 0.005
        ha    = 'left' if val >= 0 else 'right'
        ax.text(x_pos, bar.get_y() + bar.get_height()/2,
                f'{val:+.3f}', va='center', ha=ha,
                fontsize=8.5, fontweight='bold',
                color='#1E8449' if val > 0 else '#C0392B')

    ax.set_xlabel('Predicted ΔHS Overall Score', fontsize=11)
    ax.set_title(f'Intervention Ranking — {school}\n'
                 f'Predicted impact on HS Overall Score per single intervention',
                 fontsize=12, fontweight='bold')
    ax.xaxis.grid(True, color='#DDDDDD', linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.figtext(0.99, 0.01, _FOOTER, ha='right', fontsize=7.5, color='#888888')
    plt.tight_layout()

    slug = school.replace(' ', '_').replace('/', '_')
    out  = os.path.join(OUT_DIR, f'scenario_ranking_{slug}.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Ranking chart saved → {out}\n')


# ── CLI ─────────────────────────────────────────────────────────────────────────

def _build_parser():
    p = argparse.ArgumentParser(
        description='300,000 Streets — What-If Scenario Analyzer',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument('--list', action='store_true',
                   help='List all available schools and interventions, then exit.')
    p.add_argument('--school', type=str, default=None,
                   help='School short name  (e.g. "Preston HS")')
    p.add_argument('--interventions', nargs='+', default=None,
                   metavar='KEY',
                   help='One or more intervention keys  (e.g. pedestrian_crossing bike_lane)')
    p.add_argument('--rank-all', action='store_true',
                   help='Run every intervention individually and rank by impact.')
    p.add_argument('--all-schools', action='store_true',
                   help='Run for all 3 schools (use with --rank-all or --interventions).')
    p.add_argument('--out', type=str, default=None,
                   help='Output PNG path (default: outputs/scenario_<school>_<keys>.png)')
    p.add_argument('--no-chart', action='store_true',
                   help='Print results only, do not generate a chart.')
    return p


def main():
    parser = _build_parser()
    args   = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    if args.list:
        print(f'\n  Available schools: {SCHOOLS}')
        list_interventions()
        return

    schools = SCHOOLS if args.all_schools else (
        [args.school] if args.school else None
    )

    if schools is None:
        parser.print_help()
        print('\n  ERROR: specify --school or --all-schools\n')
        sys.exit(1)

    if args.rank_all:
        for school in schools:
            rank_all(school)
        return

    if not args.interventions:
        parser.print_help()
        print('\n  ERROR: specify --interventions KEY [KEY ...]\n')
        print('  Run  python scenario_analyzer.py --list  to see available keys.\n')
        sys.exit(1)

    for school in schools:
        result = run_scenario(school, args.interventions)
        print_results(result)

        if not args.no_chart:
            if args.out and len(schools) == 1:
                out_path = args.out
            else:
                slug = school.replace(' ', '_').replace('/', '_')
                keys = '_'.join(args.interventions[:3])
                out_path = os.path.join(OUT_DIR, f'scenario_{slug}_{keys}.png')
            plot_scenario(result, out_path)
            print(f'  Chart saved → {out_path}\n')


if __name__ == '__main__':
    main()
