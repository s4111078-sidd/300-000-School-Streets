"""
main_full.py — Full pipeline entry point (delegates to run_all.py).

Runs all 7 pipeline steps in order:
  1. crash_analysis.py        — VicRoads crash data
  2. spatial_features.py      — OSM spatial features
  3. environmental_features.py — AQI + crime data
  4. main.py                  — HS1–HS10 scoring, charts, maps, recommendations
  5. feature_engineering.py   — ML feature matrix
  6. ml_model.py              — Ridge regression + LOO-CV
  7. seifa_analysis.py        — SEIFA disadvantage analysis

Usage:
    python main_full.py           # run all steps, skip existing outputs
    python main_full.py --force   # re-run every step from scratch
    python main_full.py --from 4  # start from step 4 onwards
"""
import sys
import subprocess

result = subprocess.run(
    [sys.executable, 'run_all.py'] + sys.argv[1:],
    check=False,
)
sys.exit(result.returncode)
