"""
run_all.py — Master runner for the 300,000 Streets pipeline.

Runs all steps in order. Safe to re-run at any time.
Each step is skipped if its output already exists (use --force to override).

Usage:
    python run_all.py            # run all steps, skip existing outputs
    python run_all.py --force    # re-run every step from scratch
    python run_all.py --from 3   # start from step 3 onwards
"""
import os
import sys
import subprocess
import time

FORCE  = '--force' in sys.argv
FROM   = int(next((sys.argv[sys.argv.index('--from') + 1]
                   for _ in [None] if '--from' in sys.argv), 1))

GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
CYAN   = '\033[96m'
RESET  = '\033[0m'
BOLD   = '\033[1m'

STEPS = [
    {
        'n'      : 1,
        'script' : 'crash_analysis.py',
        'label'  : 'Download crash data (VicRoads)',
        'checks' : ['outputs/crash_data_statewide.csv'],
        'note'   : 'Downloads ~7,700 Victorian ped/cyc crashes. Requires internet.',
    },
    {
        'n'      : 2,
        'script' : 'spatial_features.py',
        'label'  : 'Extract OSM spatial features',
        'checks' : ['outputs/spatial_features.csv'],
        'note'   : 'Queries OpenStreetMap. Takes 3–5 min per school.',
    },
    {
        'n'      : 3,
        'script' : 'environmental_features.py',
        'label'  : 'Fetch AQI + crime data',
        'checks' : ['outputs/environmental_features.csv'],
        'note'   : 'EPA AirWatch + Crime Statistics Agency Victoria.',
    },
    {
        'n'      : 4,
        'script' : 'main.py',
        'label'  : 'HS scoring, charts, maps, recommendations',
        'checks' : ['outputs/hs_scores.csv', 'outputs/chart1_hs_radar.png'],
        'note'   : 'Core pipeline — HS1–HS10 indicator scoring.',
    },
    {
        'n'      : 5,
        'script' : 'feature_engineering.py',
        'label'  : 'Build ML feature matrix',
        'checks' : ['outputs/ml_school_features.csv'],
        'note'   : 'Joins spatial + environmental + crash → school-level features.',
    },
    {
        'n'      : 6,
        'script' : 'ml_model.py',
        'label'  : 'Train HS score prediction model (Ridge + LOO-CV)',
        'checks' : ['outputs/ml_predictions.csv', 'outputs/hs_predictor.pkl'],
        'note'   : 'Predicts HS1–HS10 from open data. Uses leave-one-out CV.',
    },
    {
        'n'      : 7,
        'script' : 'seifa_analysis.py',
        'label'  : 'SEIFA disadvantage analysis',
        'checks' : ['outputs/seifa_darebin.csv'],
        'note'   : 'ABS SEIFA 2021 — socio-economic context for Darebin catchments.',
    },
]

def _all_exist(paths):
    return all(os.path.exists(p) for p in paths)

def _run(script):
    result = subprocess.run([sys.executable, script], capture_output=False)
    return result.returncode == 0

print(f'\n{BOLD}{"="*60}')
print('  300,000 Streets — Full Pipeline Runner')
print(f'{"="*60}{RESET}')
if FORCE:
    print(f'  {YELLOW}--force: all steps will re-run{RESET}')
if FROM > 1:
    print(f'  {YELLOW}--from {FROM}: skipping steps 1–{FROM-1}{RESET}')
print()

total_start = time.time()
results = []

for step in STEPS:
    n      = step['n']
    script = step['script']
    label  = step['label']
    checks = step['checks']

    if n < FROM:
        print(f'  [{n}/7] {label}  {YELLOW}(skipped — before --from){RESET}')
        results.append('skip')
        continue

    if not FORCE and _all_exist(checks):
        print(f'  [{n}/7] {label}  {GREEN}✓ already done{RESET}')
        results.append('skip')
        continue

    print(f'\n{BOLD}{"─"*60}')
    print(f'  [{n}/7] {label}')
    print(f'  {CYAN}{step["note"]}{RESET}')
    print(f'{"─"*60}{RESET}')

    t0      = time.time()
    success = _run(script)
    elapsed = time.time() - t0

    if success:
        print(f'\n  {GREEN}✓ Step {n} completed in {elapsed:.1f}s{RESET}')
        results.append('ok')
    else:
        print(f'\n  {RED}✗ Step {n} FAILED — check output above{RESET}')
        results.append('fail')
        print(f'  {YELLOW}Continuing with remaining steps...{RESET}')

# ── Summary ────────────────────────────────────────────────────────────────────
total = time.time() - total_start
print(f'\n{BOLD}{"="*60}')
print('  PIPELINE COMPLETE')
print(f'  Total time: {total:.0f}s')
print(f'{"="*60}{RESET}')
print()
for step, result in zip(STEPS, results):
    icon = {'ok': f'{GREEN}✓{RESET}', 'skip': f'{YELLOW}–{RESET}', 'fail': f'{RED}✗{RESET}'}[result]
    print(f'  {icon}  Step {step["n"]}: {step["label"]}')

print()
print(f'  {BOLD}Key outputs:{RESET}')
print('    outputs/hs_scores.csv          — HS1–HS10 scores per school')
print('    outputs/recommendations.csv    — ranked interventions')
print('    outputs/chart1_hs_radar.png    — radar chart')
print('    outputs/map_interactive.html   — open in browser')
print('    outputs/ml_predictions.csv     — ML LOO-CV results')
print('    outputs/seifa_darebin.csv      — SEIFA disadvantage analysis')
print()

if 'fail' in results:
    sys.exit(1)
