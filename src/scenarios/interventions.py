"""
Intervention templates for scenario analysis.

Each intervention defines which ML features change and by how much when
a physical improvement is made to the street environment. Deltas are
calibrated to realistic before/after magnitudes based on OSM feature
distributions across the 3 assessed schools.

Usage:
    from src.scenarios.interventions import INTERVENTIONS, list_interventions
"""

# key → intervention definition
INTERVENTIONS = {

    'pedestrian_crossing': {
        'label'      : 'Install signalised pedestrian crossing',
        'description': 'Add a signalised crossing adjacent to the school gate '
                       '(zebra + signals + countdown timer).',
        'deltas': {
            'crossings_400m'         : +1,
            'signals_400m'           : +1,
            'crossing_density_400m'  : +0.15,
        },
        'cost'      : 'Medium  (~$80k–$200k)',
        'timeframe' : '< 1 year',
        'hs_target' : 'HS2',
    },

    'bike_lane': {
        'label'      : 'Install protected bike lane',
        'description': 'Build a physically separated cycling lane along the '
                       'school frontage and key approach routes (~200m).',
        'deltas': {
            'cycle_pct_400m'                : +12.0,
            'protected_cycle_length_400m'   : +200.0,
        },
        'cost'      : 'High  (~$500k–$1.5M per km)',
        'timeframe' : '1–3 years',
        'hs_target' : 'HS6',
    },

    'speed_reduction': {
        'label'      : 'Reduce speed limit to 40 km/h school zone',
        'description': 'Lower the posted speed limit to 40 km/h within 400m '
                       'of the school gate, active during school hours.',
        'deltas': {
            'avg_speed_400m' : -10.0,
            'avg_speed_zone' : -10.0,
        },
        'cost'      : 'Low  (~$5k–$20k signage)',
        'timeframe' : '< 6 months',
        'hs_target' : 'HS5',
    },

    'traffic_calming': {
        'label'      : 'Install traffic calming (speed humps / raised crossing)',
        'description': 'Speed humps, raised pedestrian crossings, or chicanes '
                       'to physically slow vehicles near the school gate.',
        'deltas': {
            'avg_speed_400m'       : -5.0,
            'crash_count'          : -2,
            'serious_or_fatal_rate': -0.10,
        },
        'cost'      : 'Medium  (~$50k–$150k)',
        'timeframe' : '< 1 year',
        'hs_target' : 'HS9',
    },

    'footpath': {
        'label'      : 'Build / extend continuous footpath',
        'description': 'Construct or widen a continuous footpath along the '
                       'school street and key pedestrian approach routes.',
        'deltas': {
            'footpath_pct_200m': +10.0,
            'footpath_pct_400m': +10.0,
            'walk_length_400m' : +500.0,
        },
        'cost'      : 'Medium  (~$100k–$300k)',
        'timeframe' : '< 1 year',
        'hs_target' : 'HS1',
    },

    'street_trees': {
        'label'      : 'Plant street trees',
        'description': 'Plant trees along the school frontage and footpath '
                       'to improve shade, shelter, and visual amenity.',
        'deltas': {
            'tree_count_100m': +12,
            'green_pct_400m' : +5.0,
        },
        'cost'      : 'Low  (~$20k–$60k)',
        'timeframe' : '< 1 year',
        'hs_target' : 'HS3',
    },

    'benches': {
        'label'      : 'Add street benches / seating',
        'description': 'Install seating along the school frontage and nearby '
                       'footpaths for students, parents, and pedestrians.',
        'deltas': {
            'bench_count_200m': +6,
        },
        'cost'      : 'Low  (~$5k–$15k)',
        'timeframe' : '< 6 months',
        'hs_target' : 'HS4',
    },

    'pt_stop': {
        'label'      : 'Add / improve public transport stop',
        'description': 'Install a new bus or tram stop within 400m of the '
                       'school gate, or upgrade an existing stop.',
        'deltas': {
            'pt_stops_400m': +1,
        },
        'cost'      : 'Medium  (~$50k–$200k)',
        'timeframe' : '1–2 years',
        'hs_target' : 'HS6',
    },

    'shelter': {
        'label'      : 'Install covered shelter / bus shelter',
        'description': 'Add a covered shelter near the school gate for students '
                       'waiting for buses or parents in rain.',
        'deltas': {
            'shelter_count_200m': +2,
        },
        'cost'      : 'Low  (~$15k–$40k)',
        'timeframe' : '< 6 months',
        'hs_target' : 'HS3',
    },

    'remove_arterial': {
        'label'      : 'Reroute heavy vehicles / reduce arterial traffic',
        'description': 'Divert heavy vehicles or reduce arterial road '
                       'classification near the school via local traffic plan.',
        'deltas': {
            'arterial_pct_400m'   : -10.0,
            'high_speed_road_400m': -3,
            'avg_speed_400m'      : -5.0,
        },
        'cost'      : 'High  (network-level, council decision)',
        'timeframe' : '2–5 years',
        'hs_target' : 'HS5',
    },
}


def list_interventions() -> None:
    """Print all available interventions with their keys and labels."""
    print('\n  Available interventions:')
    print('  ' + '-' * 54)
    for key, iv in INTERVENTIONS.items():
        print(f"  {key:<22}  {iv['label']}")
        print(f"  {'':22}  Cost: {iv['cost']}  |  {iv['timeframe']}")
    print()
