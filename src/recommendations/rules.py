"""
Recommendation rules — Healthy Streets framework (HS1–HS10).

Each function accepts a scored DataFrame row and returns a recommendation dict
(keys: hs_indicator, hazard, recommendation, priority, cost, timeframe) or None.
"""
from typing import Optional
import pandas as pd


def rule_01_footpath_missing(row) -> Optional[dict]:
    if row.get('Footpath_present') in ['No footpath at all',
                                        'Partial or broken — gaps present']:
        return {
            'hs_indicator'  : 'HS1',
            'hazard'        : 'Missing or broken footpath',
            'recommendation': 'Construct continuous concrete footpath minimum 1.8m wide',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_02_footpath_narrow(row) -> Optional[dict]:
    try:
        if float(row['Footpath_width']) < 1.5:
            return {
                'hs_indicator'  : 'HS1',
                'hazard'        : 'Footpath below minimum width standard (1.5m)',
                'recommendation': 'Widen footpath to minimum 1.5m — Australian Standard AS 1428.1',
                'priority'      : 'Medium',
                'cost'          : 'Medium — $20,000 to $200,000',
                'timeframe'     : 'Short-term — within 1 year',
            }
    except (ValueError, TypeError):
        pass
    return None


def rule_03_crossing_absent(row) -> Optional[dict]:
    if row.get('Crossing_present') in ['No crossing at all',
                                        'Yes — informal / unmarked only']:
        return {
            'hs_indicator'  : 'HS2',
            'hazard'        : 'No formal pedestrian crossing present',
            'recommendation': 'Install raised zebra crossing with tactile pavers adjacent to school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_04_crossing_too_far(row) -> Optional[dict]:
    try:
        if float(row['Crossing_dist']) > 150:
            return {
                'hs_indicator'  : 'HS2',
                'hazard'        : 'Nearest crossing too far from school gate',
                'recommendation': 'Install additional pedestrian crossing within 50m of school gate',
                'priority'      : 'High',
                'cost'          : 'Medium — $20,000 to $200,000',
                'timeframe'     : 'Short-term — within 1 year',
            }
    except (ValueError, TypeError):
        pass
    return None


def rule_05_tactile_missing(row) -> Optional[dict]:
    if row.get('Tactile') == 'No':
        return {
            'hs_indicator'  : 'HS2',
            'hazard'        : 'No tactile ground surface indicators at crossing',
            'recommendation': 'Install tactile pavers on both sides of all crossings within 400m of gate',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_06_no_school_zone(row) -> Optional[dict]:
    if row.get('School_zone') == 'No school zone at all':
        return {
            'hs_indicator'  : 'HS9',
            'hazard'        : 'No school zone signage present on this street',
            'recommendation': 'Install school zone signs with 40km/h speed restriction on all approaches',
            'priority'      : 'High',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_07_no_traffic_calming(row) -> Optional[dict]:
    if (row.get('Traffic_calming') == 'No traffic calming at all' and
            '3 or more' in str(row.get('Lanes', ''))):
        return {
            'hs_indicator'  : 'HS9',
            'hazard'        : 'No traffic calming on multi-lane road near school gate',
            'recommendation': 'Install speed humps or raised intersection table near school gate',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_08_no_cycling_infra(row) -> Optional[dict]:
    if row.get('Cycling_infra') == 'No cycling infrastructure':
        return {
            'hs_indicator'  : 'HS6',
            'hazard'        : 'No cycling infrastructure on school frontage road',
            'recommendation': 'Install painted bike lane or shared path along school frontage',
            'priority'      : 'Low',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Long-term — 1 to 3 years',
        }
    return None


def rule_09_poor_lighting(row) -> Optional[dict]:
    if row.get('Lighting') in ['Poor — dim or infrequent lights', 'No street lighting']:
        return {
            'hs_indicator'  : 'HS7',
            'hazard'        : 'Poor street lighting on walking route to school',
            'recommendation': 'Install LED street lights at regular intervals along primary walking route',
            'priority'      : 'Medium',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_10_vegetation_block(row) -> Optional[dict]:
    if 'Vegetation' in str(row.get('Hazard_types', '')):
        return {
            'hs_indicator'  : 'HS3',
            'hazard'        : 'Vegetation blocking footpath or crossing sightlines',
            'recommendation': 'Remove and regularly trim vegetation obstructing path and crossing visibility',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_11_no_kerb_ramps(row) -> Optional[dict]:
    if 'No kerb ramps' in str(row.get('Kerb_ramps', '')):
        return {
            'hs_indicator'  : 'HS1',
            'hazard'        : 'No kerb ramps at intersections within catchment zone',
            'recommendation': 'Install kerb ramps at all intersections within 400m of school gate',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_12_high_speed_zone(row) -> Optional[dict]:
    if any(s in str(row.get('Speed_limit', '')) for s in ['60', '70', '80', '90', '100']):
        return {
            'hs_indicator'  : 'HS5',
            'hazard'        : 'Speed limit exceeds school zone standard near school gate',
            'recommendation': 'Advocate for speed limit reduction to 40km/h and school zone establishment',
            'priority'      : 'High',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_13_heavy_vehicle_route(row) -> Optional[dict]:
    if 'frequent' in str(row.get('Heavy_vehicles', '')).lower():
        return {
            'hs_indicator'  : 'HS5',
            'hazard'        : 'Frequent heavy vehicles travelling past school gate',
            'recommendation': 'Install heavy vehicle restriction signage and physical barriers during school hours',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_14_low_visibility_crossing(row) -> Optional[dict]:
    try:
        vis = float(row['Visibility'])
        if pd.notna(vis) and vis < 3:
            return {
                'hs_indicator'  : 'HS2',
                'hazard'        : 'Poor crossing visibility — approaching drivers cannot see pedestrians in time',
                'recommendation': 'Remove sightline obstructions, install raised crossing and advance warning signs',
                'priority'      : 'Medium',
                'cost'          : 'Medium — $20,000 to $200,000',
                'timeframe'     : 'Short-term — within 1 year',
            }
    except (ValueError, TypeError):
        pass
    return None


def rule_15_low_hs6_active_travel(row) -> Optional[dict]:
    hs6 = row.get('HS6')
    if pd.notna(hs6) and float(hs6) < 4:
        return {
            'hs_indicator'  : 'HS6',
            'hazard'        : f'Poor active travel score (HS6 {float(hs6):.1f}/10) — unsafe cycling conditions',
            'recommendation': 'Install separated cycling infrastructure (kerb-protected lane or shared path), improve surface, add wayfinding signage',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_16_low_hs7_safety(row) -> Optional[dict]:
    hs7 = row.get('HS7')
    if pd.notna(hs7) and float(hs7) < 5:
        return {
            'hs_indicator'  : 'HS7',
            'hazard'        : f'Low personal safety score (HS7 {float(hs7):.1f}/10)',
            'recommendation': 'Improve street lighting, increase passive surveillance with activated frontages, engage council on CPTED principles',
            'priority'      : 'High',
            'cost'          : 'Medium — $20,000 to $200,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None


def rule_17_low_hs10_air_quality(row) -> Optional[dict]:
    hs10 = row.get('HS10')
    if pd.notna(hs10) and float(hs10) < 5:
        return {
            'hs_indicator'  : 'HS10',
            'hazard'        : f'Poor air quality near school (HS10 {float(hs10):.1f}/10)',
            'recommendation': 'Advocate for heavy vehicle restrictions near school, increase tree canopy and green buffer, monitor EPA AirWatch during high-AQI events',
            'priority'      : 'Medium',
            'cost'          : 'Low — under $20,000',
            'timeframe'     : 'Short-term — within 1 year',
        }
    return None
