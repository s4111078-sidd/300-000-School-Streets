"""
Spatial Features — School Streets Safety Analysis
Computes OSM-based spatial features per school gate at 200m / 400m / 800m buffers.

Features per radius (3 radii × 12 = 36 total):
  Walking:   walk_edges, walk_length_m, footpath_length_m, footpath_pct
  Roads:     road_count, arterial_count, arterial_pct, avg_speed_kmh, high_speed_road_count
  Crossings: crossings, signals
  Derived:   crossing_density (crossings per km of walkable path)

Run:    python spatial_features.py
Output: outputs/spatial_features.csv

Requires: geopandas, osmnx, shapely, pyproj, networkx
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point
from pyproj import Transformer

OUT_DIR = 'outputs'
OUT_CSV = os.path.join(OUT_DIR, 'spatial_features.csv')

RADII      = [200, 400, 800]   # metres
CRS_METRIC = 'EPSG:7855'       # GDA2020 / MGA zone 55 — accurate metric distances for Victoria
CRS_GEO    = 'EPSG:4326'

FOOTPATH_TYPES = {'footway', 'path', 'pedestrian', 'cycleway', 'steps', 'bridleway'}
ARTERIAL_TYPES = {'primary', 'secondary', 'trunk', 'primary_link', 'secondary_link', 'trunk_link'}

# Fallback: 3 original Darebin school gates
SCHOOL_GATES = {
    'Reservoir HS':       {'lat': -37.7224,  'lon': 145.0294},
    'William Ruthven SC': {'lat': -37.69654, 'lon': 145.00299},
    'Preston HS':         {'lat': -37.7417,  'lon': 145.0071},
}

_transformer = Transformer.from_crs(CRS_GEO, CRS_METRIC, always_xy=True)


def gate_to_projected_point(lat, lon):
    """Convert WGS84 lat/lon to a Shapely Point in EPSG:7855."""
    x, y = _transformer.transform(lon, lat)
    return Point(x, y)


def _highway_matches(val, type_set):
    """Handle OSM highway values that may be a string or list."""
    if isinstance(val, list):
        return any(v in type_set for v in val)
    return val in type_set


def _parse_speed(val):
    """Parse OSM maxspeed to km/h float. Returns np.nan on failure."""
    if isinstance(val, list):
        val = val[0]
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    if 'mph' in s:
        try:
            return float(s.replace('mph', '').strip()) * 1.60934
        except ValueError:
            return np.nan
    try:
        return float(s.replace('km/h', '').replace('kmh', '').strip())
    except ValueError:
        return np.nan


SCHOOL_DATA_CSV = 'school_data.csv'

def load_gates():
    """Load gates from school_data.csv (assessed schools only). Falls back to 3 hardcoded gates."""
    fallback = dict(SCHOOL_GATES)
    if not os.path.exists(SCHOOL_DATA_CSV):
        print(f'  {SCHOOL_DATA_CSV} not found — using {len(fallback)} hardcoded gates')
        return fallback
    try:
        sd = pd.read_csv(SCHOOL_DATA_CSV)
        sd.columns = sd.columns.str.strip()
        name_col = next((c for c in sd.columns if 'school name' in c.lower() or c.lower() == 'school'), None)
        lat_col  = next((c for c in sd.columns if 'latitude'    in c.lower()), None)
        lon_col  = next((c for c in sd.columns if 'longitude'   in c.lower()), None)
        if not all([name_col, lat_col, lon_col]):
            raise ValueError(f'Could not find name/lat/lon columns. Found: {sd.columns.tolist()}')
        gates = {}
        for _, row in sd.drop_duplicates(subset=[name_col]).iterrows():
            name = str(row[name_col]).strip()
            try:
                gates[name] = {'lat': float(row[lat_col]), 'lon': float(row[lon_col])}
            except (ValueError, TypeError):
                pass
        gates.update(fallback)
        print(f'  Loaded {len(gates)} school gates from {SCHOOL_DATA_CSV}')
        return gates
    except Exception as e:
        print(f'  Warning: could not read {SCHOOL_DATA_CSV} ({e}) — using {len(fallback)} hardcoded gates')
        return fallback


def compute_features(name, lat, lon):
    """Return (feature_dict, geom_dict) for one school gate."""
    feat   = {'school_name': name, 'gate_lat': lat, 'gate_lon': lon}
    geoms  = {f'{t}_{r}m': [] for t in ('walk', 'cycling', 'roads') for r in (400, 800)}
    center = gate_to_projected_point(lat, lon)

    for r in RADII:
        # ── Walking network ────────────────────────────────────────────────────
        walk_edges = walk_length = fp_length = fp_pct = np.nan
        edges_walk = None
        try:
            G_walk = ox.graph_from_point((lat, lon), dist=r, network_type='walk', retain_all=True)
            edges_walk  = ox.graph_to_gdfs(G_walk, nodes=False, edges=True).to_crs(CRS_METRIC)
            walk_edges  = len(edges_walk)
            walk_length = edges_walk.geometry.length.sum()
            fp_mask     = edges_walk['highway'].apply(lambda v: _highway_matches(v, FOOTPATH_TYPES))
            fp_length   = edges_walk.loc[fp_mask, 'geometry'].length.sum()
            fp_pct      = (fp_length / walk_length * 100) if walk_length > 0 else 0.0
        except Exception:
            pass

        feat[f'walk_edges_{r}m']      = walk_edges
        feat[f'walk_length_{r}m']     = round(walk_length, 1) if not np.isnan(walk_length) else np.nan
        feat[f'footpath_length_{r}m'] = round(fp_length, 1)   if not np.isnan(fp_length)   else np.nan
        feat[f'footpath_pct_{r}m']    = round(fp_pct, 2)      if not np.isnan(fp_pct)       else np.nan

        # ── Drive (road) network ───────────────────────────────────────────────
        road_count = arterial_count = arterial_pct = avg_speed = high_speed = np.nan
        edges_drive = None
        try:
            G_drive = ox.graph_from_point((lat, lon), dist=r, network_type='drive', retain_all=True)
            edges_drive   = ox.graph_to_gdfs(G_drive, nodes=False, edges=True).to_crs(CRS_METRIC)
            road_count    = len(edges_drive)
            arterial_mask = edges_drive['highway'].apply(lambda v: _highway_matches(v, ARTERIAL_TYPES))
            arterial_count = int(arterial_mask.sum())
            arterial_pct   = (arterial_count / road_count * 100) if road_count > 0 else 0.0
            speeds         = edges_drive['maxspeed'].apply(_parse_speed).dropna()
            avg_speed      = speeds.mean()      if len(speeds) > 0 else np.nan
            high_speed     = int((speeds >= 60).sum()) if len(speeds) > 0 else 0
        except Exception:
            pass

        feat[f'road_count_{r}m']      = road_count
        feat[f'arterial_count_{r}m']  = arterial_count
        feat[f'arterial_pct_{r}m']    = round(arterial_pct, 2) if not np.isnan(arterial_pct) else np.nan
        feat[f'avg_speed_{r}m']       = round(avg_speed, 1)    if not np.isnan(avg_speed)    else np.nan
        feat[f'high_speed_road_{r}m'] = high_speed

        # ── Crossings ──────────────────────────────────────────────────────────
        crossing_count = np.nan
        try:
            crossings_gdf = ox.features_from_point((lat, lon), tags={'highway': 'crossing'}, dist=r)
            crossings_gdf = crossings_gdf.to_crs(CRS_METRIC)
            buf           = center.buffer(r)
            crossing_count = int(crossings_gdf[crossings_gdf.geometry.intersects(buf)].shape[0])
        except Exception:
            pass

        feat[f'crossings_{r}m'] = crossing_count

        # ── Traffic signals ────────────────────────────────────────────────────
        signal_count = np.nan
        try:
            signals_gdf = ox.features_from_point((lat, lon), tags={'highway': 'traffic_signals'}, dist=r)
            signals_gdf = signals_gdf.to_crs(CRS_METRIC)
            buf         = center.buffer(r)
            signal_count = int(signals_gdf[signals_gdf.geometry.intersects(buf)].shape[0])
        except Exception:
            pass

        feat[f'signals_{r}m'] = signal_count

        # ── Derived: crossing density (crossings per km of walkable path) ──────
        if not np.isnan(crossing_count) and not np.isnan(walk_length) and walk_length > 0:
            feat[f'crossing_density_{r}m'] = round(crossing_count / (walk_length / 1000), 2)
        else:
            feat[f'crossing_density_{r}m'] = np.nan

        # ── Cycling network ────────────────────────────────────────────────────
        cycle_length = protected_length = np.nan
        try:
            G_bike = ox.graph_from_point((lat, lon), dist=r, network_type='bike', retain_all=True)
            edges_bike = ox.graph_to_gdfs(G_bike, nodes=False, edges=True).to_crs(CRS_METRIC)
            cycle_length = edges_bike.geometry.length.sum()

            def _is_protected(e):
                hw = e.get('highway', '')
                cy = e.get('cycleway', '')
                if isinstance(hw, list): hw = hw[0] if hw else ''
                if isinstance(cy, list): cy = cy[0] if cy else ''
                return hw == 'cycleway' or str(cy) in ('track', 'separate', 'separated')

            protected_mask = edges_bike.apply(_is_protected, axis=1)
            protected_length = edges_bike.loc[protected_mask, 'geometry'].length.sum()
        except Exception:
            edges_bike    = None
            protected_mask = None

        feat[f'cycle_length_{r}m'] = round(cycle_length, 1) if not np.isnan(cycle_length) else np.nan
        feat[f'protected_cycle_length_{r}m'] = round(protected_length, 1) if not np.isnan(protected_length) else np.nan
        feat[f'cycle_pct_{r}m'] = (
            round(cycle_length / walk_length * 100, 2)
            if not np.isnan(cycle_length) and not np.isnan(walk_length) and walk_length > 0
            else np.nan
        )

        # ── Save geometries for 400m and 800m only ────────────────────────────
        if r in (400, 800):
            hw_col = 'highway'

            # Walk network edges → filter to footpath types only
            if edges_walk is not None and not edges_walk.empty:
                fp_mask = edges_walk[hw_col].apply(lambda v: _highway_matches(v, FOOTPATH_TYPES))
                gdf_w = edges_walk[fp_mask][['geometry']].copy()
                gdf_w['school_name'] = name
                gdf_w['highway']     = edges_walk.loc[fp_mask, hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'walk_{r}m'].append(gdf_w.to_crs(CRS_GEO))

            # Cycling edges — with is_protected flag
            if edges_bike is not None and not edges_bike.empty and protected_mask is not None:
                gdf_c = edges_bike[['geometry']].copy()
                gdf_c['school_name']  = name
                gdf_c['is_protected'] = protected_mask.values
                gdf_c['highway']      = edges_bike[hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'cycling_{r}m'].append(gdf_c.to_crs(CRS_GEO))

            # Arterial roads
            if edges_drive is not None and not edges_drive.empty:
                art_mask = edges_drive[hw_col].apply(lambda v: _highway_matches(v, ARTERIAL_TYPES))
                gdf_r = edges_drive[art_mask][['geometry']].copy()
                gdf_r['school_name'] = name
                gdf_r['highway']     = edges_drive.loc[art_mask, hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'roads_{r}m'].append(gdf_r.to_crs(CRS_GEO))

    return feat, geoms


# ── Main ───────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  Spatial Features — OSM walking / road / crossings / cycling')
print('='*60)

all_gates = load_gates()
print(f'\nComputing features for {len(all_gates)} school gates...')
print('(~1-2 min per school — Overpass API calls)\n')

NETWORKS_GPKG = os.path.join(OUT_DIR, 'networks.gpkg')

rows      = []
all_geoms = {f'{t}_{r}m': [] for t in ('walk', 'cycling', 'roads') for r in (400, 800)}

for i, (name, gate) in enumerate(all_gates.items(), 1):
    print(f'[{i}/{len(all_gates)}] {name}  ({gate["lat"]:.5f}, {gate["lon"]:.5f})')
    row, geoms = compute_features(name, gate['lat'], gate['lon'])
    rows.append(row)
    for key in all_geoms:
        all_geoms[key].extend(geoms.get(key, []))

df = pd.DataFrame(rows)
os.makedirs(OUT_DIR, exist_ok=True)
df.to_csv(OUT_CSV, index=False)
print(f'\nSaved -> {OUT_CSV}  ({len(df)} schools, {len(df.columns)} columns)')

# ── Save network geometries to GeoPackage ──────────────────────────────────────
print(f'\nSaving network geometries -> {NETWORKS_GPKG}')
import geopandas as _gpd
_layer_labels = {
    'walk_400m':    'Walk Network 400m',
    'walk_800m':    'Walk Network 800m',
    'cycling_400m': 'Cycling Network 400m',
    'cycling_800m': 'Cycling Network 800m',
    'roads_400m':   'Arterial Roads 400m',
    'roads_800m':   'Arterial Roads 800m',
}
for key, label in _layer_labels.items():
    parts = all_geoms[key]
    if not parts:
        print(f'  (no data for {label})')
        continue
    gdf = _gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs='EPSG:4326')
    gdf.to_file(NETWORKS_GPKG, layer=key, driver='GPKG')
    print(f'  Saved layer: {label}  ({len(gdf)} edges)')
print(f'Done.')
