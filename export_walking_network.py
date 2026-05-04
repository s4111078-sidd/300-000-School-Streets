"""
Sprint task: Export OSMnx walking network with walkability scores → GeoPackage
Output: outputs/school_streets.gpkg  (layers: walking_network, hazard_points, school_gates)
Run:    conda run -n geo python export_walking_network.py
"""

import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, box
from scipy.spatial import cKDTree
import numpy as np

CSV_FILE = 'school_data.csv'
OUT_GPKG = os.path.join('outputs', 'school_streets.gpkg')

SCHOOL_GATES = {
    'Reservoir High School':             {'lat': -37.7224,  'lon': 145.0294},
    'William Ruthven Secondary College': {'lat': -37.69654, 'lon': 145.00299},
    'Preston High School':               {'lat': -37.7417,  'lon': 145.0071},
}
BUFFER_M = 1000   # download network within 1 km of each school gate
CRS      = 'EPSG:4326'

# ── 1. Load survey data ────────────────────────────────────────────────────────
print('[1/5] Loading survey data...')
df = pd.read_csv(CSV_FILE)
df.columns = df.columns.str.strip()
df = df.rename(columns={
    'School name'                                                    : 'School',
    'Overall hazard severity at this location'                       : 'Severity',
    'Footpath Accessibility Score — FAS (0 to 10)'             : 'FAS',
    'Crossing Safety Score — CSS (0 to 10)'                    : 'CSS',
    'Environmental Exposure Indicator — EEI (0 to 10)'         : 'EEI',
    'Street or location being assessed'                              : 'Street',
    'Latitude (decimal degrees)'                                     : 'Latitude',
    'Longitude (decimal degrees)'                                    : 'Longitude',
})
df['FAS']           = pd.to_numeric(df['FAS'], errors='coerce')
df['CSS']           = pd.to_numeric(df['CSS'], errors='coerce')
df['EEI']           = pd.to_numeric(df['EEI'], errors='coerce')
df['Overall_score'] = (df['FAS'] + df['CSS'] + df['EEI']) / 3

def clean_severity(s):
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'

df['Severity'] = df['Severity'].apply(clean_severity)
df = df.dropna(subset=['Latitude', 'Longitude'])
print(f'      {len(df)} survey points loaded')

# ── 2. Download walking network ────────────────────────────────────────────────
print('[2/5] Downloading OSMnx walking network...')
ox.settings.log_console = False

graphs = []
for name, gate in SCHOOL_GATES.items():
    print(f'      {name}...')
    G = ox.graph_from_point(
        (gate['lat'], gate['lon']),
        dist=BUFFER_M,
        network_type='walk',
        retain_all=False,
        simplify=True,
    )
    graphs.append(G)

import networkx as nx
G_all = nx.compose_all(graphs)
print(f'      {G_all.number_of_edges()} edges, {G_all.number_of_nodes()} nodes')

# ── 3. Convert to GeoDataFrames ────────────────────────────────────────────────
print('[3/5] Converting to GeoDataFrame...')
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_all)
edges_gdf = edges_gdf.reset_index()

# Keep only useful columns
keep_edge_cols = ['u', 'v', 'key', 'name', 'highway', 'length', 'maxspeed',
                  'oneway', 'lanes', 'geometry']
keep_edge_cols = [c for c in keep_edge_cols if c in edges_gdf.columns]
edges_gdf = edges_gdf[keep_edge_cols].copy()

# Ensure string types for GPKG compatibility
for col in ['name', 'highway', 'maxspeed', 'lanes']:
    if col in edges_gdf.columns:
        edges_gdf[col] = edges_gdf[col].astype(str)

# ── 4. Snap survey scores onto nearest edge ────────────────────────────────────
print('[4/5] Joining walkability scores to nearest network edges...')

# Project to metric CRS for distance calculations
edges_proj  = edges_gdf.to_crs('EPSG:32755')   # UTM zone 55S — Melbourne
survey_proj = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']),
    crs=CRS,
).to_crs('EPSG:32755')

# Get edge centroids for nearest-neighbour lookup
edge_centroids = np.column_stack([
    edges_proj.geometry.centroid.x,
    edges_proj.geometry.centroid.y,
])
survey_coords = np.column_stack([
    survey_proj.geometry.x,
    survey_proj.geometry.y,
])

tree = cKDTree(edge_centroids)
dist, idx = tree.query(survey_coords, k=1)

# Only snap if within 300 m of a survey point
MAX_SNAP_M = 300
score_cols  = ['FAS', 'CSS', 'EEI', 'Overall_score', 'Severity']
for col in score_cols:
    edges_gdf[col] = np.nan
edges_gdf['Severity'] = edges_gdf['Severity'].astype(object)

for i, (d, edge_i) in enumerate(zip(dist, idx)):
    if d <= MAX_SNAP_M:
        row = df.iloc[i]
        for col in score_cols:
            current = edges_gdf.at[edges_gdf.index[edge_i], col]
            # Average if multiple survey points map to the same edge
            if pd.isna(current) or col == 'Severity':
                edges_gdf.at[edges_gdf.index[edge_i], col] = row[col]
            else:
                edges_gdf.at[edges_gdf.index[edge_i], col] = (float(current) + float(row[col])) / 2

scored = edges_gdf['Overall_score'].notna().sum()
print(f'      {scored} of {len(edges_gdf)} edges scored')

# ── 5. Build hazard_points and school_gates layers ────────────────────────────
hazard_gdf = gpd.GeoDataFrame(
    df[['School', 'Street', 'Severity', 'FAS', 'CSS', 'EEI', 'Overall_score',
        'Latitude', 'Longitude']],
    geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']),
    crs=CRS,
)

gates_rows = [
    {'School': name, 'geometry': Point(g['lon'], g['lat'])}
    for name, g in SCHOOL_GATES.items()
]
gates_gdf = gpd.GeoDataFrame(gates_rows, crs=CRS)

# ── 6. Write GeoPackage ────────────────────────────────────────────────────────
print('[5/5] Writing GeoPackage...')
os.makedirs('outputs', exist_ok=True)

edges_out = edges_gdf.to_crs(CRS)
edges_out.to_file(OUT_GPKG, layer='walking_network', driver='GPKG')
hazard_gdf.to_file(OUT_GPKG, layer='hazard_points',  driver='GPKG')
gates_gdf.to_file( OUT_GPKG, layer='school_gates',   driver='GPKG')

print(f'\n  Done — {OUT_GPKG}')
print('  Layers:')
print('    walking_network  — street edges with FAS/CSS/EEI/Overall_score')
print('    hazard_points    — survey assessment locations')
print('    school_gates     — school entrance markers')
print('\nNext: open outputs/school_streets.gpkg in QGIS (see QGIS_styling_guide.md)')
