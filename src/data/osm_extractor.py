"""
Spatial Features — School Streets Safety Analysis
Computes OSM-based spatial features per school gate at 200m / 400m / 800m buffers.

Features per radius (3 radii × 15 = 45 total):
  Walking:   walk_edges, walk_length_m, footpath_length_m, footpath_pct
  Roads:     road_count, arterial_count, arterial_pct, avg_speed_kmh, high_speed_road_count
  Crossings: crossings, signals
  Cycling:   cycle_length_m, protected_cycle_length_m, cycle_pct
  Derived:   crossing_density (crossings per km of walkable path)

Also saves network geometries to outputs/networks.gpkg for interactive map overlays.

Run standalone:  python -m src.data.osm_extractor
Output:          outputs/spatial_features.csv
                 outputs/networks.gpkg

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

from config import OUT_DIR, CSV_FILE, SCHOOL_GATES_BY_SHORT

OUT_CSV       = OUT_DIR / 'spatial_features.csv'
NETWORKS_GPKG = OUT_DIR / 'networks.gpkg'

RADII      = [200, 400, 800]   # metres
CRS_METRIC = 'EPSG:7855'       # GDA2020 / MGA zone 55 — accurate metric distances for Victoria
CRS_GEO    = 'EPSG:4326'

FOOTPATH_TYPES = {'footway', 'path', 'pedestrian', 'cycleway', 'steps', 'bridleway'}
ARTERIAL_TYPES = {'primary', 'secondary', 'trunk', 'primary_link', 'secondary_link', 'trunk_link'}

_transformer = Transformer.from_crs(CRS_GEO, CRS_METRIC, always_xy=True)


def gate_to_projected_point(lat: float, lon: float) -> Point:
    """Convert WGS84 lat/lon to a Shapely Point in EPSG:7855."""
    x, y = _transformer.transform(lon, lat)
    return Point(x, y)


def _highway_matches(val, type_set: set) -> bool:
    """Handle OSM highway values that may be a string or list."""
    if isinstance(val, list):
        return any(v in type_set for v in val)
    return val in type_set


def _parse_speed(val) -> float:
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


def load_gates(csv_path=None) -> dict:
    """
    Load gate coordinates from school_data.csv (assessed schools only).
    Falls back to SCHOOL_GATES_BY_SHORT (3 hardcoded Darebin gates) on any error.

    Args:
        csv_path: override path to school_data.csv; defaults to config.CSV_FILE.

    Returns:
        dict mapping school name → {'lat': float, 'lon': float}
    """
    path     = str(csv_path or CSV_FILE)
    fallback = dict(SCHOOL_GATES_BY_SHORT)

    if not os.path.exists(path):
        print(f'  {path} not found — using {len(fallback)} hardcoded gates')
        return fallback
    try:
        sd = pd.read_csv(path)
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
        print(f'  Loaded {len(gates)} school gates from {path}')
        return gates
    except Exception as e:
        print(f'  Warning: could not read {path} ({e}) — using {len(fallback)} hardcoded gates')
        return fallback


def compute_features(name: str, lat: float, lon: float) -> tuple:
    """
    Compute OSM spatial features and collect network geometries for one school gate.

    Args:
        name: school name (used as label in output CSV).
        lat:  gate latitude (WGS84).
        lon:  gate longitude (WGS84).

    Returns:
        (feature_dict, geom_dict) where feature_dict is a flat row for the CSV
        and geom_dict holds GeoDataFrame lists keyed by layer name.
    """
    feat   = {'school_name': name, 'gate_lat': lat, 'gate_lon': lon}
    geoms  = {f'{t}_{r}m': [] for t in ('walk', 'cycling', 'roads') for r in (400, 800)}
    center = gate_to_projected_point(lat, lon)

    for r in RADII:
        # ── Walking network ────────────────────────────────────────────────────
        walk_edges = walk_length = fp_length = fp_pct = np.nan
        edges_walk = None
        try:
            G_walk      = ox.graph_from_point((lat, lon), dist=r, network_type='walk', retain_all=True)
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
            G_drive       = ox.graph_from_point((lat, lon), dist=r, network_type='drive', retain_all=True)
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
            crossings_gdf  = ox.features_from_point((lat, lon), tags={'highway': 'crossing'}, dist=r)
            crossings_gdf  = crossings_gdf.to_crs(CRS_METRIC)
            buf            = center.buffer(r)
            crossing_count = int(crossings_gdf[crossings_gdf.geometry.intersects(buf)].shape[0])
        except Exception:
            pass

        feat[f'crossings_{r}m'] = crossing_count

        # ── Traffic signals ────────────────────────────────────────────────────
        signal_count = np.nan
        try:
            signals_gdf  = ox.features_from_point((lat, lon), tags={'highway': 'traffic_signals'}, dist=r)
            signals_gdf  = signals_gdf.to_crs(CRS_METRIC)
            buf          = center.buffer(r)
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
        edges_bike   = None
        protected_mask = None
        try:
            G_bike     = ox.graph_from_point((lat, lon), dist=r, network_type='bike', retain_all=True)
            edges_bike = ox.graph_to_gdfs(G_bike, nodes=False, edges=True).to_crs(CRS_METRIC)
            cycle_length = edges_bike.geometry.length.sum()

            def _is_protected(e):
                hw = e.get('highway', '')
                cy = e.get('cycleway', '')
                if isinstance(hw, list): hw = hw[0] if hw else ''
                if isinstance(cy, list): cy = cy[0] if cy else ''
                return hw == 'cycleway' or str(cy) in ('track', 'separate', 'separated')

            protected_mask   = edges_bike.apply(_is_protected, axis=1)
            protected_length = edges_bike.loc[protected_mask, 'geometry'].length.sum()
        except Exception:
            pass

        feat[f'cycle_length_{r}m']           = round(cycle_length, 1)    if not np.isnan(cycle_length)    else np.nan
        feat[f'protected_cycle_length_{r}m'] = round(protected_length, 1) if not np.isnan(protected_length) else np.nan
        feat[f'cycle_pct_{r}m'] = (
            round(cycle_length / walk_length * 100, 2)
            if not np.isnan(cycle_length) and not np.isnan(walk_length) and walk_length > 0
            else np.nan
        )

        # ── Save geometries for 400m and 800m only ────────────────────────────
        if r in (400, 800):
            hw_col = 'highway'
            if edges_walk is not None and not edges_walk.empty:
                fp_mask2 = edges_walk[hw_col].apply(lambda v: _highway_matches(v, FOOTPATH_TYPES))
                gdf_w = edges_walk[fp_mask2][['geometry']].copy()
                gdf_w['school_name'] = name
                gdf_w['highway']     = edges_walk.loc[fp_mask2, hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'walk_{r}m'].append(gdf_w.to_crs(CRS_GEO))

            if edges_bike is not None and not edges_bike.empty and protected_mask is not None:
                gdf_c = edges_bike[['geometry']].copy()
                gdf_c['school_name']  = name
                gdf_c['is_protected'] = protected_mask.values
                gdf_c['highway']      = edges_bike[hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'cycling_{r}m'].append(gdf_c.to_crs(CRS_GEO))

            if edges_drive is not None and not edges_drive.empty:
                art_mask2 = edges_drive[hw_col].apply(lambda v: _highway_matches(v, ARTERIAL_TYPES))
                gdf_r = edges_drive[art_mask2][['geometry']].copy()
                gdf_r['school_name'] = name
                gdf_r['highway']     = edges_drive.loc[art_mask2, hw_col].apply(
                    lambda v: v[0] if isinstance(v, list) else v)
                geoms[f'roads_{r}m'].append(gdf_r.to_crs(CRS_GEO))

    return feat, geoms


def compute_spatial_features(gates: dict = None) -> pd.DataFrame:
    """
    Compute OSM spatial features for each school gate and save results.

    Args:
        gates: dict mapping school name → {'lat': float, 'lon': float}.
               If None, loads from school_data.csv via load_gates().

    Returns:
        pd.DataFrame with one row per school and ~45 feature columns.

    Side effects:
        Writes outputs/spatial_features.csv and outputs/networks.gpkg.
    """
    print('\n' + '='*60)
    print('  Spatial Features — OSM walking / road / crossings / cycling')
    print('='*60)

    if gates is None:
        gates = load_gates()

    print(f'\nComputing features for {len(gates)} school gates...')
    print('(~1-2 min per school — Overpass API calls)\n')

    rows      = []
    all_geoms = {f'{t}_{r}m': [] for t in ('walk', 'cycling', 'roads') for r in (400, 800)}

    for i, (name, gate) in enumerate(gates.items(), 1):
        print(f'[{i}/{len(gates)}] {name}  ({gate["lat"]:.5f}, {gate["lon"]:.5f})')
        row, geoms = compute_features(name, gate['lat'], gate['lon'])
        rows.append(row)
        for key in all_geoms:
            all_geoms[key].extend(geoms.get(key, []))

    df = pd.DataFrame(rows)
    os.makedirs(str(OUT_DIR), exist_ok=True)
    df.to_csv(str(OUT_CSV), index=False)
    print(f'\nSaved -> {OUT_CSV}  ({len(df)} schools, {len(df.columns)} columns)')

    _layer_labels = {
        'walk_400m':    'Walk Network 400m',
        'walk_800m':    'Walk Network 800m',
        'cycling_400m': 'Cycling Network 400m',
        'cycling_800m': 'Cycling Network 800m',
        'roads_400m':   'Arterial Roads 400m',
        'roads_800m':   'Arterial Roads 800m',
    }
    print(f'\nSaving network geometries -> {NETWORKS_GPKG}')
    for key, label in _layer_labels.items():
        parts = all_geoms[key]
        if not parts:
            print(f'  (no data for {label})')
            continue
        gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs='EPSG:4326')
        gdf.to_file(str(NETWORKS_GPKG), layer=key, driver='GPKG')
        print(f'  Saved layer: {label}  ({len(gdf)} edges)')

    print('Done.')
    return df


if __name__ == '__main__':
    compute_spatial_features()
