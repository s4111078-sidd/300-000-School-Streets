"""
Recommendation engine — applies HS-based rules to a school observations DataFrame.

Usage:
    from src.recommendations.engine import run_recommendations
    rec_df = run_recommendations(df)   # returns one row per triggered rule
"""
import pandas as pd

from src.recommendations.rules import (
    rule_01_footpath_missing,
    rule_02_footpath_narrow,
    rule_03_crossing_absent,
    rule_04_crossing_too_far,
    rule_05_tactile_missing,
    rule_06_no_school_zone,
    rule_07_no_traffic_calming,
    rule_08_no_cycling_infra,
    rule_09_poor_lighting,
    rule_10_vegetation_block,
    rule_11_no_kerb_ramps,
    rule_12_high_speed_zone,
    rule_13_heavy_vehicle_route,
    rule_14_low_visibility_crossing,
    rule_15_low_hs6_active_travel,
    rule_16_low_hs7_safety,
    rule_17_low_hs10_air_quality,
)

_RULES = [
    rule_01_footpath_missing,
    rule_02_footpath_narrow,
    rule_03_crossing_absent,
    rule_04_crossing_too_far,
    rule_05_tactile_missing,
    rule_06_no_school_zone,
    rule_07_no_traffic_calming,
    rule_08_no_cycling_infra,
    rule_09_poor_lighting,
    rule_10_vegetation_block,
    rule_11_no_kerb_ramps,
    rule_12_high_speed_zone,
    rule_13_heavy_vehicle_route,
    rule_14_low_visibility_crossing,
    rule_15_low_hs6_active_travel,
    rule_16_low_hs7_safety,
    rule_17_low_hs10_air_quality,
]


def generate_recommendations(row) -> list:
    return [r for fn in _RULES if (r := fn(row)) is not None]


def run_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the recommendation engine to every row in df.

    Returns:
        pd.DataFrame with columns:
        School, Location, Severity, HS_overall,
        HS_indicator, Hazard, Recommendation, Priority, Cost, Timeframe.
    """
    records = []
    for _, row in df.iterrows():
        for rec in generate_recommendations(row):
            records.append({
                'School'        : row['School'],
                'Location'      : row.get('Street', ''),
                'Severity'      : row.get('Sev_clean', ''),
                'HS_overall'    : row.get('HS_overall', ''),
                'HS_indicator'  : rec.get('hs_indicator', ''),
                'Hazard'        : rec['hazard'],
                'Recommendation': rec['recommendation'],
                'Priority'      : rec['priority'],
                'Cost'          : rec['cost'],
                'Timeframe'     : rec['timeframe'],
            })
    return pd.DataFrame(records)
