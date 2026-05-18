"""
Interactive folium map — hazard points, school gates, buffers, crash markers, OSM networks.

Produces outputs/map_interactive.html.
"""
import os
import pandas as pd
import folium

from config import SCHOOL_GATES

_SEV_COLOUR = {'Major': 'red', 'Moderate': 'orange', 'Minor': 'green', 'Unknown': 'gray'}

_LEGEND_HTML = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:12px 16px;border-radius:8px;
     border:1px solid #ccc;font-family:Arial;font-size:12px;">
  <b>300,000 Streets</b><br>
  <span style="color:#666;font-size:11px">Hazard Severity</span><br><br>
  <span style="color:#C0392B">&#9679;</span> Major<br>
  <span style="color:#D35400">&#9679;</span> Moderate<br>
  <span style="color:#1E8449">&#9679;</span> Minor<br>
  <span style="color:#2980B9">&#9679;</span> Road crash (ped/cyc)<br>
  <span style="color:#333">&#9670;</span> School gate<br>
  &#9711; 400m / 800m buffer<br>
  <span style="color:#27AE60">&#9135;</span> Walk network<br>
  <span style="color:#1A8FC1">&#9135;</span> Cycling (thick = protected)<br>
  <span style="color:#C0392B">&#9135;</span> Arterial roads<br><br>
  <span style="color:#999;font-size:10px">Click any point for details</span>
</div>"""

_NET_LAYERS = [
    ('walk_400m',    'Walk Network 400m',    '#27AE60', 2,   0.75, False),
    ('walk_800m',    'Walk Network 800m',    '#27AE60', 1.5, 0.5,  False),
    ('cycling_400m', 'Cycling Network 400m', '#1A8FC1', 2,   0.8,  True),
    ('cycling_800m', 'Cycling Network 800m', '#1A8FC1', 1.5, 0.6,  True),
    ('roads_400m',   'Arterial Roads 400m',  '#C0392B', 2.5, 0.7,  False),
    ('roads_800m',   'Arterial Roads 800m',  '#C0392B', 2,   0.5,  False),
]


def build_interactive_map(df: pd.DataFrame, rec_df: pd.DataFrame, out_dir: str) -> str:
    """
    Build the interactive folium map with hazard points, crash markers, and OSM network layers.

    Args:
        df:      scored observations DataFrame (needs Latitude, Longitude, Sev_clean, etc.)
        rec_df:  recommendations DataFrame (School, Recommendation, Priority columns)
        out_dir: directory for outputs; crash and network files are read from here if present.

    Returns:
        str: path to saved map_interactive.html
    """
    crash_csv    = os.path.join(out_dir, 'crash_data_darebin.csv')
    networks_gpkg = os.path.join(out_dir, 'networks.gpkg')

    centre_lat = df['Latitude'].mean()
    centre_lon = df['Longitude'].mean()
    m = folium.Map(location=[centre_lat, centre_lon],
                   zoom_start=14, tiles='CartoDB positron', control_scale=True)

    # ── School gate markers + buffers ─────────────────────────────────────────
    for name, info in SCHOOL_GATES.items():
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=folium.Popup(
                f"<b>{name}</b><br>{info['addr']}<br><i>School gate</i>", max_width=240),
            tooltip=name,
            icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
        ).add_to(m)
        folium.Circle(
            location=[info['lat'], info['lon']], radius=400,
            color='#333333', weight=1.5, fill=True, fill_opacity=0.04,
            tooltip='400m buffer'
        ).add_to(m)
        folium.Circle(
            location=[info['lat'], info['lon']], radius=800,
            color='#888888', weight=1, fill=True, fill_opacity=0.02,
            tooltip='800m buffer', dash_array='6'
        ).add_to(m)

    # ── Hazard observation markers ─────────────────────────────────────────────
    for _, row in df.iterrows():
        lat = row['Latitude']
        lon = row['Longitude']
        if pd.isna(lat) or pd.isna(lon):
            continue

        sev     = row['Sev_clean']
        hazards = str(row['Hazard_types']) if pd.notna(row['Hazard_types']) else 'Not recorded'

        school_recs = rec_df[rec_df['School'] == row['School']]
        top_rec = school_recs.iloc[0]['Recommendation'] if len(school_recs) > 0 else 'Not recorded'
        top_pri = school_recs.iloc[0]['Priority']       if len(school_recs) > 0 else 'Not recorded'

        popup_html = (
            f'<div style="font-family:Arial;font-size:12px;min-width:230px">'
            f'<b style="font-size:13px">{row["School"]}</b><br>'
            f'<span style="color:#666">{row["Street"]}</span><br>'
            f'<hr style="margin:5px 0">'
            f'<b>Severity:</b> <span style="color:{_SEV_COLOUR.get(sev,"gray")}">{sev}</span><br>'
            f'<b>FAS:</b> {row["FAS"]:.1f} &nbsp;'
            f'<b>CSS:</b> {row["CSS"]:.1f} &nbsp;'
            f'<b>EEI:</b> {row["EEI"]:.1f} &nbsp;'
            f'<b>CIS:</b> {row["CIS"]:.1f}<br>'
            f'<hr style="margin:5px 0">'
            f'<b>Hazards:</b><br>'
            f'<span style="color:#555;font-size:11px">{hazards}</span><br>'
            f'<hr style="margin:5px 0">'
            f'<b>Top Recommendation:</b><br>'
            f'<span style="font-size:11px">{top_rec}</span><br>'
            f'<b>Priority:</b> {top_pri}'
            f'</div>'
        )

        folium.CircleMarker(
            location=[lat, lon], radius=12,
            color='white', weight=2, fill=True,
            fill_color=_SEV_COLOUR.get(sev, 'gray'), fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=270),
            tooltip=f"{row['School_short']} — {row['Street']} ({sev})"
        ).add_to(m)

    # ── Crash markers ──────────────────────────────────────────────────────────
    crash_count = 0
    if os.path.exists(crash_csv):
        crash_df = pd.read_csv(crash_csv, low_memory=False)
        crash_df.columns = crash_df.columns.str.strip()
        lat_c = next((c for c in crash_df.columns if c.upper() in ('LAT', 'LATITUDE', 'Y')), None)
        lon_c = next((c for c in crash_df.columns if c.upper() in ('LON', 'LONG', 'LONGITUDE', 'X')), None)
        if lat_c and lon_c:
            for _, cr in crash_df.dropna(subset=[lat_c, lon_c]).iterrows():
                school = cr.get('nearest_school', 'Unknown')
                dist   = cr.get('dist_to_gate_m', '')
                date   = cr.get('ACCIDENTDATE', '') or cr.get('accidentdate', '')
                folium.CircleMarker(
                    location=[cr[lat_c], cr[lon_c]], radius=7,
                    color='white', weight=1.5, fill=True,
                    fill_color='#2980B9', fill_opacity=0.85,
                    popup=folium.Popup(
                        f"<div style='font-family:Arial;font-size:12px'>"
                        f"<b>Road Crash</b><br>"
                        f"<b>School:</b> {school}<br>"
                        + (f"<b>Distance to gate:</b> {dist:.0f}m<br>" if isinstance(dist, float)
                           else f"<b>Distance to gate:</b> {dist}<br>")
                        + f"<b>Date:</b> {date}<br>"
                        f"<span style='color:#2980B9'>Pedestrian/Cyclist involved</span>"
                        f"</div>", max_width=220),
                    tooltip=(f"Crash — {school} ({dist:.0f}m)" if isinstance(dist, float)
                             else f"Crash — {school}")
                ).add_to(m)
                crash_count += 1
    if crash_count:
        print(f"      Added {crash_count} crash markers to interactive map")

    # ── OSM network layers ─────────────────────────────────────────────────────
    net_added = 0
    if os.path.exists(networks_gpkg):
        try:
            import geopandas as gpd
            for key, label, colour, weight, opacity, is_cycling in _NET_LAYERS:
                try:
                    gdf = gpd.read_file(networks_gpkg, layer=key)
                except Exception:
                    continue
                fg = folium.FeatureGroup(name=label, show=(key.endswith('400m')))
                for _, r in gdf.iterrows():
                    geom = r.geometry
                    if geom is None or geom.is_empty:
                        continue
                    if geom.geom_type == 'LineString':
                        parts = [list(geom.coords)]
                    elif geom.geom_type == 'MultiLineString':
                        parts = [list(g.coords) for g in geom.geoms]
                    else:
                        continue
                    w = weight * 2 if (is_cycling and r.get('is_protected')) else weight
                    c = '#0D4F8B'   if (is_cycling and r.get('is_protected')) else colour
                    for coords in parts:
                        folium.PolyLine(
                            [[pt[1], pt[0]] for pt in coords],
                            color=c, weight=w, opacity=opacity,
                            tooltip=str(r.get('highway', '')),
                        ).add_to(fg)
                fg.add_to(m)
                net_added += 1
            folium.LayerControl(collapsed=False).add_to(m)
            print(f"      Added {net_added} network layers to interactive map")
        except Exception as e:
            print(f"      (Network layers skipped: {e})")
    else:
        print("      (networks.gpkg not found — run spatial_features.py to add network layers)")

    m.get_root().html.add_child(folium.Element(_LEGEND_HTML))
    out = os.path.join(out_dir, 'map_interactive.html')
    m.save(out)
    return out
