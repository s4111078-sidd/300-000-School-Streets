"""
demographics_chart.py
---------------------
Generates chart4_demographics.png using ABS Census 2021 suburb data
for the City of Darebin school catchments.

Output: outputs/chart4_demographics.png

Run:    python demographics_chart.py

Data source:
  demographics_darebin.csv  (ABS Census 2021 — Reservoir SAL22161, Preston SAL22121)
"""

import os
from config import DEMO_FILE, OUT_DIR
from src.visualisation.charts import plot_demographics

OUT_DIR_STR = str(OUT_DIR)
os.makedirs(OUT_DIR_STR, exist_ok=True)

print('\n' + '='*60)
print('  300,000 Streets — ABS Demographics Chart')
print('='*60)

demo_path = str(DEMO_FILE)
if not os.path.exists(demo_path):
    raise FileNotFoundError(
        f"demographics_darebin.csv not found at {demo_path}\n"
        "This file ships with the project repository."
    )

out = plot_demographics(demo_path, OUT_DIR_STR)
print(f"\n  Chart saved → {out}")
print('='*60 + '\n')
