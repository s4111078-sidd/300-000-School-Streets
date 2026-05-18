"""
KDE hazard density heatmap — static PNG, GeoTIFF, and interactive folium HTML.

Produces:
  outputs/heatmap.png          — static PNG (importable into QGIS)
  outputs/kde_heatmap.tif      — georeferenced GeoTIFF (requires rasterio)
  outputs/map_heatmap.html     — interactive folium heatmap
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium.plugins import HeatMap

from config import SCHOOL_GATES

_SEV_COLOUR = {'Major': 'red', 'Moderate': 'orange', 'Minor': 'green', 'Unknown': 'gray'}


def _sev_weight(s: str) -> float:
    if s == 'Major':    return 3.0
    if s == 'Moderate': return 2.0
    return 1.0


def build_kde_heatmap(df: pd.DataFrame, rec_df: pd.DataFrame, out_dir: str) -> None:
    """
    Build static heatmap PNG, optional GeoTIFF, and interactive heatmap HTML.

    Args:
        df:      scored observations DataFrame (needs Latitude, Longitude, Sev_clean, etc.)
        rec_df:  recommendations DataFrame (School, Recommendation, Priority)
        out_dir: directory for all outputs; crash CSV is read from here if present.
    """
    crash_csv = os.path.join(out_dir, 'crash_data_darebin.csv')

    coords = df[['Latitude', 'Longitude', 'Sev_clean']].dropna(subset=['Latitude', 'Longitude'])
    if len(coords) < 2:
        print("      Not enough points for heatmap — need at least 2 observations")
        return

    lats    = coords['Latitude'].values.astype(float)
    lons    = coords['Longitude'].values.astype(float)
    weights = coords['Sev_clean'].apply(_sev_weight).values

    # ── Gaussian KDE density grid (pure numpy — no scipy) ─────────────────────
    lat_min, lat_max = lats.min() - 0.012, lats.max() + 0.012
    lon_min, lon_max = lons.min() - 0.012, lons.max() + 0.012
    grid_lon, grid_lat = np.meshgrid(
        np.linspace(lon_min, lon_max, 300),
        np.linspace(lat_min, lat_max, 300)
    )
    bandwidth = 0.008
    density   = np.zeros_like(grid_lat)
    for i in range(len(lats)):
        d2 = ((grid_lat - lats[i]) / bandwidth) ** 2 + \
             ((grid_lon - lons[i]) / bandwidth) ** 2
        density += weights[i] * np.exp(-0.5 * d2)
    density = (density - density.min()) / (density.max() - density.min() + 1e-10)

    # ── Static PNG ─────────────────────────────────────────────────────────────
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'hazard', ['#1E8449', '#F4D03F', '#D35400', '#C0392B'], N=256
    )
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('white')
    im = ax.imshow(density,
                   extent=[lon_min, lon_max, lat_min, lat_max],
                   origin='lower', cmap=cmap, alpha=0.75, aspect='auto')

    sev_dot = {'Major': '#C0392B', 'Moderate': '#D35400', 'Minor': '#1E8449'}
    for _, row in df.dropna(subset=['Latitude', 'Longitude']).iterrows():
        c = sev_dot.get(row['Sev_clean'], '#888888')
        ax.scatter(row['Longitude'], row['Latitude'],
                   c=c, s=140, zorder=5, edgecolors='white', linewidths=1.8)
        ax.annotate(row['School_short'],
                    (row['Longitude'], row['Latitude']),
                    textcoords='offset points', xytext=(8, 4),
                    fontsize=8, fontweight='bold', color='#1A1A1A',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.8, edgecolor='none'))

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Hazard Density (weighted by severity)', fontsize=9, color='#444444')
    cbar.ax.tick_params(labelsize=8)
    ax.set_title('Hazard Density Heatmap — School Catchment Zones',
                 fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Longitude', fontsize=9, color='#666666')
    ax.set_ylabel('Latitude',  fontsize=9, color='#666666')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.figtext(0.99, 0.01, '300,000 Streets  |  Regen Melbourne x RMIT University',
                ha='right', fontsize=7, color='#888888')
    plt.tight_layout()
    heatmap_png = os.path.join(out_dir, 'heatmap.png')
    plt.savefig(heatmap_png, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"      Saved -> {heatmap_png}")

    # ── GeoTIFF ────────────────────────────────────────────────────────────────
    kde_tif = os.path.join(out_dir, 'kde_heatmap.tif')
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS as RioCRS
        transform = from_bounds(lon_min, lat_min, lon_max, lat_max, 300, 300)
        with rasterio.open(
            kde_tif, 'w', driver='GTiff',
            height=300, width=300, count=1, dtype='float32',
            crs=RioCRS.from_epsg(4326), transform=transform, nodata=0.0,
        ) as dst:
            dst.write(density[::-1].astype('float32'), 1)
        print(f"      Saved -> {kde_tif}  (georeferenced — ready for PyQGIS)")
    except ImportError:
        print("      NOTE: rasterio not installed — kde_heatmap.tif not saved")

    # ── Interactive heatmap HTML ───────────────────────────────────────────────
    heat_data = [[float(lats[i]), float(lons[i]), float(weights[i])]
                 for i in range(len(lats))]

    m2 = folium.Map(location=[lats.mean(), lons.mean()],
                    zoom_start=14, tiles='CartoDB positron', control_scale=True)

    HeatMap(heat_data, min_opacity=0.4, radius=50, blur=30,
            gradient={'0.2': '#1E8449', '0.5': '#F4D03F',
                      '0.75': '#D35400', '1.0': '#C0392B'}
            ).add_to(m2)

    for name, info in SCHOOL_GATES.items():
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=folium.Popup(f"<b>{name}</b><br>{info['addr']}", max_width=220),
            tooltip=name,
            icon=folium.Icon(color='black', icon='graduation-cap', prefix='fa')
        ).add_to(m2)
        folium.Circle(
            location=[info['lat'], info['lon']], radius=400,
            color='#333333', weight=1.5, fill=True, fill_opacity=0.04,
            tooltip='400m buffer'
        ).add_to(m2)

    # Observation markers on heatmap
    for _, row in df.iterrows():
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
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
            f'<b>EEI:</b> {row["EEI"]:.1f}<br>'
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
            location=[row['Latitude'], row['Longitude']],
            radius=10, color='white', weight=2,
            fill=True, fill_color=_SEV_COLOUR.get(sev, 'gray'), fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=270),
            tooltip=f"{row['School_short']} — {row['Street']} ({sev})"
        ).add_to(m2)

    # Crash markers on heatmap
    if os.path.exists(crash_csv):
        crash_df = pd.read_csv(crash_csv, low_memory=False)
        crash_df.columns = crash_df.columns.str.strip()
        lat_c = next((c for c in crash_df.columns if c.upper() in ('LAT', 'LATITUDE', 'Y')), None)
        lon_c = next((c for c in crash_df.columns if c.upper() in ('LON', 'LONG', 'LONGITUDE', 'X')), None)
        if lat_c and lon_c:
            for _, cr in crash_df.dropna(subset=[lat_c, lon_c]).iterrows():
                school = cr.get('nearest_school', 'Unknown')
                folium.CircleMarker(
                    location=[cr[lat_c], cr[lon_c]], radius=6,
                    color='white', weight=1.5, fill=True,
                    fill_color='#2980B9', fill_opacity=0.85,
                    tooltip=f"Crash — {school}"
                ).add_to(m2)

    legend_html2 = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
         background:white;padding:12px 16px;border-radius:8px;
         border:1px solid #ccc;font-family:Arial;font-size:12px;">
      <b>300,000 Streets</b><br>
      <span style="color:#666;font-size:11px">Hazard Heatmap</span><br><br>
      <span style="color:#C0392B">&#9632;</span> High density<br>
      <span style="color:#D35400">&#9632;</span> Medium density<br>
      <span style="color:#F4D03F">&#9632;</span> Low density<br>
      <span style="color:#1E8449">&#9632;</span> Minimal<br>
      <span style="color:#D35400">&#9679;</span> Moderate hazard<br>
      <span style="color:#1E8449">&#9679;</span> Minor hazard<br>
      <span style="color:#2980B9">&#9679;</span> Road crash (ped/cyc)<br>
      &#9711; 400m buffer<br><br>
      <span style="color:#999;font-size:10px">Weighted by severity</span>
    </div>"""
    m2.get_root().html.add_child(folium.Element(legend_html2))
    heatmap_html = os.path.join(out_dir, 'map_heatmap.html')
    m2.save(heatmap_html)
    print(f"      Saved -> {heatmap_html}")
    print("      Open map_heatmap.html in browser — interactive heatmap")
    print("      heatmap.png ready for QGIS import")
