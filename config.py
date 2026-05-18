"""
Configuration — paths, constants, and lookup tables shared across all modules.
All modules should import constants from here rather than defining their own.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# ── Paths ──────────────────────────────────────────────────────────────────────
CSV_FILE    = PROJECT_ROOT / 'school_data.csv'
DEMO_FILE   = PROJECT_ROOT / 'demographics_darebin.csv'
OUT_DIR     = PROJECT_ROOT / 'outputs'
SPATIAL_CSV = OUT_DIR / 'spatial_features.csv'
ENV_CSV     = OUT_DIR / 'environmental_features.csv'
HS_CSV      = OUT_DIR / 'hs_scores.csv'

# ── Healthy Streets indicators ─────────────────────────────────────────────────
# 10 indicators (Lucy Saunders / TfL framework, adapted for school streets).
HS_INDICATORS = [
    ('HS1',  'Pedestrians from\nall walks of life'),
    ('HS2',  'Easy to\ncross'),
    ('HS3',  'Shade and\nshelter'),
    ('HS4',  'Places to stop\nand rest'),
    ('HS5',  'Not too\nnoisy'),
    ('HS6',  'People choose to\nwalk / cycle / PT'),
    ('HS7',  'People\nfeel safe'),
    ('HS8',  'Things to\nsee and do'),
    ('HS9',  'People\nfeel relaxed'),
    ('HS10', 'Clean\nair'),
]
HS_CODES  = [h[0] for h in HS_INDICATORS]
HS_LABELS = [h[1] for h in HS_INDICATORS]

# ── School gates ───────────────────────────────────────────────────────────────
# Main gate coordinates and addresses for all assessed schools.
SCHOOL_GATES = {
    'Reservoir High School': {
        'lat': -37.7224, 'lon': 145.0294,
        'addr': '855 Plenty Rd, Reservoir VIC 3073',
    },
    'William Ruthven Secondary College': {
        'lat': -37.69654, 'lon': 145.00299,
        'addr': '60 Merrilands Rd, Reservoir VIC 3073',
    },
    'Preston High School': {
        'lat': -37.7417, 'lon': 145.0071,
        'addr': '2-16 Cooma St, Preston VIC 3072',
    },
}

# Full name → short display name (chart labels, CSV matching).
SCHOOL_SHORT_NAMES = {
    'Reservoir High School':             'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School':               'Preston HS',
}

# Short name → gate coords (used by crash_analysis and spatial_features which
# key their gate dicts by short name).
SCHOOL_GATES_BY_SHORT = {
    'Reservoir HS':       {'lat': -37.7224,  'lon': 145.0294},
    'William Ruthven SC': {'lat': -37.69654, 'lon': 145.00299},
    'Preston HS':         {'lat': -37.7417,  'lon': 145.0071},
}

# ── CIS lookup ─────────────────────────────────────────────────────────────────
# Cycling Infrastructure Score mapping.
# Reference: LTS (Mekuria, Furth & Nixon 2012); VicRoads TEM Vol. 3 Part 218.
CIS_MAP = {
    'Yes — separated bike lane':          9.0,
    'Yes — shared path or greenway':      8.0,
    'Yes — painted bike lane (on-road)':  4.5,
    'Yes — advisory lane / shared road':  2.0,
    'No cycling infrastructure':               1.0,
}

# ── Column rename mapping ──────────────────────────────────────────────────────
# Maps raw CSV header strings to internal short names used throughout the pipeline.
COLUMN_RENAME = {
    'School name'                                                    : 'School',
    'Overall hazard severity at this location'                       : 'Severity',
    'Footpath Accessibility Score — FAS (0 to 10)'             : 'FAS',
    'Crossing Safety Score — CSS (0 to 10)'                    : 'CSS',
    'Environmental Exposure Indicator — EEI (0 to 10)'         : 'EEI',
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
}
