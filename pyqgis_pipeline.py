import os
import csv
import sys

# ── STANDALONE INIT (skip when running inside QGIS Console) ──────────────────
_STANDALONE = not ('qgis.core' in sys.modules or 'qgis' in sys.modules)
if _STANDALONE:
    QGIS_PREFIX = '/Applications/QGIS.app/Contents/MacOS'  # adjust if needed
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path.insert(0, os.path.join(QGIS_PREFIX, 'lib', 'python3', 'dist-packages'))
    from qgis.core import QgsApplication
    _app = QgsApplication([], False)
    _app.setPrefixPath(QGIS_PREFIX, True)
    _app.initQgis()
    import processing as _proc_mod
    from processing.core.Processing import Processing as _ProcCore
    _ProcCore.initialize()

# ── QGIS IMPORTS ─────────────────────────────────────────────────────────────
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsFields,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsVectorFileWriter,
    QgsMarkerSymbol,
    QgsFillSymbol,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsRasterLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
import processing

# ── CONFIG ───────────────────────────────────────────────────────────────────
BASE_DIR = '/Users/hishikeshphukan/Library/CloudStorage/OneDrive-RMITUniversity/300,000 Streets of Melbourne/300-000-School-Streets'
CSV_FILE = os.path.join(BASE_DIR, 'school_data.csv')
OUT_DIR  = os.path.join(BASE_DIR, 'outputs')
GPKG_OUT = os.path.join(OUT_DIR, 'school_streets.gpkg')
PROJ_OUT = os.path.join(OUT_DIR, 'school_streets.qgz')
os.makedirs(OUT_DIR, exist_ok=True)

CRS_WGS84    = QgsCoordinateReferenceSystem('EPSG:4326')
CRS_METRIC   = QgsCoordinateReferenceSystem('EPSG:7855')   # GDA2020 / MGA zone 55 (Melbourne)

# Raw CSV column names (with Unicode em dash U+2014)
COL_SCHOOL    = 'School name'
COL_STREET    = 'Street or location being assessed'
COL_LAT       = 'Latitude (decimal degrees)'
COL_LON       = 'Longitude (decimal degrees)'
COL_SEVERITY  = 'Overall hazard severity at this location'
COL_FAS       = 'Footpath Accessibility Score \u2014 FAS (0 to 10)'
COL_CSS       = 'Crossing Safety Score \u2014 CSS (0 to 10)'
COL_EEI       = 'Environmental Exposure Indicator \u2014 EEI (0 to 10)'
COL_DIST      = 'Approximate distance from school gate (metres)'
COL_HAZARDS   = 'Hazard types observed at this location (select all that apply)'
COL_REC_TYPE  = 'Recommended intervention type'
COL_PRIORITY  = 'Recommendation priority level'
COL_COST      = 'Estimated cost level'
COL_TIMEFRAME = 'Suggested implementation timeframe'
COL_HAZ_DESC  = 'Detailed hazard description'
COL_REC_DESC  = 'Detailed intervention description'

SCHOOL_SHORT = {
    'Reservoir High School':             'Reservoir HS',
    'William Ruthven Secondary College': 'William Ruthven SC',
    'Preston High School':               'Preston HS',
}

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

SEV_COLOUR = {
    'Major':    '#C0392B',
    'Moderate': '#D35400',
    'Minor':    '#1E8449',
    'Unknown':  '#888888',
}


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def _clean_severity(s):
    s = str(s).lower()
    if 'major'    in s: return 'Major'
    if 'moderate' in s: return 'Moderate'
    if 'minor'    in s: return 'Minor'
    return 'Unknown'

def _strip_header(row):
    """Normalise CSV header keys: strip whitespace."""
    return {k.strip(): v.strip() for k, v in row.items()}


# ── LAYER BUILDERS ───────────────────────────────────────────────────────────

def build_assessment_layer(csv_path):
    """Read CSV and return a memory point layer with all safety fields."""
    fields = QgsFields()
    for name, vtype in [
        ('School',        QVariant.String),
        ('School_short',  QVariant.String),
        ('Street',        QVariant.String),
        ('Severity',      QVariant.String),
        ('FAS',           QVariant.Double),
        ('CSS',           QVariant.Double),
        ('EEI',           QVariant.Double),
        ('Overall_score', QVariant.Double),
        ('Distance_gate', QVariant.Double),
        ('Hazard_types',  QVariant.String),
        ('Rec_type',      QVariant.String),
        ('Priority',      QVariant.String),
        ('Cost_level',    QVariant.String),
        ('Timeframe',     QVariant.String),
        ('Hazard_desc',   QVariant.String),
        ('Rec_desc',      QVariant.String),
    ]:
        fields.append(QgsField(name, vtype))

    layer = QgsVectorLayer('Point?crs=EPSG:4326', 'Safety Assessment Points', 'memory')
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()

    features = []
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        for raw in csv.DictReader(f):
            row = _strip_header(raw)
            lat = _safe_float(row.get(COL_LAT))
            lon = _safe_float(row.get(COL_LON))
            if lat is None or lon is None:
                continue

            school = row.get(COL_SCHOOL, '')
            fas    = _safe_float(row.get(COL_FAS))
            css    = _safe_float(row.get(COL_CSS))
            eei    = _safe_float(row.get(COL_EEI))
            sev    = _clean_severity(row.get(COL_SEVERITY, ''))

            overall = None
            if None not in (fas, css, eei):
                overall = round((fas + css + eei) / 3, 2)

            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feat['School']        = school
            feat['School_short']  = SCHOOL_SHORT.get(school, school)
            feat['Street']        = row.get(COL_STREET, '')
            feat['Severity']      = sev
            feat['FAS']           = fas
            feat['CSS']           = css
            feat['EEI']           = eei
            feat['Overall_score'] = overall
            feat['Distance_gate'] = _safe_float(row.get(COL_DIST))
            feat['Hazard_types']  = row.get(COL_HAZARDS, '')
            feat['Rec_type']      = row.get(COL_REC_TYPE, '')
            feat['Priority']      = row.get(COL_PRIORITY, '')
            feat['Cost_level']    = row.get(COL_COST, '')
            feat['Timeframe']     = row.get(COL_TIMEFRAME, '')
            feat['Hazard_desc']   = row.get(COL_HAZ_DESC, '')
            feat['Rec_desc']      = row.get(COL_REC_DESC, '')
            features.append(feat)

    provider.addFeatures(features)
    layer.updateExtents()
    return layer


def build_gates_layer(active_schools):
    """Return memory point layer for school gates — only schools present in the CSV."""
    fields = QgsFields()
    fields.append(QgsField('Name',    QVariant.String))
    fields.append(QgsField('Address', QVariant.String))

    layer = QgsVectorLayer('Point?crs=EPSG:4326', 'School Gates', 'memory')
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()

    features = []
    for name, info in SCHOOL_GATES.items():
        if name not in active_schools:
            print(f'      Skipping gate for {name} — no CSV data found')
            continue
        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(info['lon'], info['lat'])))
        feat['Name']    = name
        feat['Address'] = info['addr']
        features.append(feat)

    provider.addFeatures(features)
    layer.updateExtents()
    return layer


def build_buffer(gates_layer, distance_m, name):
    """
    Buffer school gates at distance_m metres.
    Reprojects to a metric CRS (EPSG:7855) for accurate distance, then back to WGS84.
    """
    reproj = processing.run('native:reprojectlayer', {
        'INPUT':      gates_layer,
        'TARGET_CRS': CRS_METRIC,
        'OUTPUT':     'TEMPORARY_OUTPUT',
    })['OUTPUT']

    buf = processing.run('native:buffer', {
        'INPUT':          reproj,
        'DISTANCE':       distance_m,
        'SEGMENTS':       48,
        'END_CAP_STYLE':  0,
        'JOIN_STYLE':     0,
        'MITER_LIMIT':    2,
        'DISSOLVE':       False,
        'OUTPUT':         'TEMPORARY_OUTPUT',
    })['OUTPUT']

    buf_wgs = processing.run('native:reprojectlayer', {
        'INPUT':      buf,
        'TARGET_CRS': CRS_WGS84,
        'OUTPUT':     'TEMPORARY_OUTPUT',
    })['OUTPUT']

    buf_wgs.setName(name)
    return buf_wgs


# ── SYMBOLOGY ─────────────────────────────────────────────────────────────────

def style_assessment_layer(layer):
    """Categorised circles coloured by Severity."""
    cats = []
    for sev, hex_col in SEV_COLOUR.items():
        sym = QgsMarkerSymbol.createSimple({
            'name':          'circle',
            'color':         hex_col,
            'outline_color': 'white',
            'outline_width': '0.5',
            'size':          '5',
        })
        cats.append(QgsRendererCategory(sev, sym, sev))
    layer.setRenderer(QgsCategorizedSymbolRenderer('Severity', cats))
    layer.triggerRepaint()


def style_gates_layer(layer):
    """Black star marker for school gates."""
    sym = QgsMarkerSymbol.createSimple({
        'name':          'star',
        'color':         '#1A1A1A',
        'outline_color': 'white',
        'outline_width': '0.6',
        'size':          '8',
    })
    layer.setRenderer(QgsSingleSymbolRenderer(sym))
    layer.triggerRepaint()


def style_buffer(layer, hex_col, fill_opacity=0.08, border_width='0.5'):
    """Semi-transparent fill for walking zone buffers."""
    fill = QColor(hex_col)
    fill.setAlphaF(fill_opacity)
    border = QColor(hex_col)
    sym = QgsFillSymbol.createSimple({
        'color':         fill.name(QColor.HexArgb),
        'outline_color': border.name(),
        'outline_width': border_width,
        'style':         'solid',
    })
    layer.setRenderer(QgsSingleSymbolRenderer(sym))
    layer.triggerRepaint()


# ── BASE MAP ─────────────────────────────────────────────────────────────────

def build_osm_layer():
    """Return an OpenStreetMap XYZ tile layer (raster, not exportable to GPKG)."""
    uri = (
        'type=xyz'
        '&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        '&zmax=19&zmin=0'
        '&crs=EPSG:3857'
    )
    layer = QgsRasterLayer(uri, 'OpenStreetMap', 'wms')
    if not layer.isValid():
        print('      WARNING: OSM tile layer failed to load (no internet?)')
    return layer


# ── EXPORT ────────────────────────────────────────────────────────────────────

def export_geopackage(layers, gpkg_path):
    """Write all layers to a single GeoPackage (overwrites if exists)."""
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'

    for i, lyr in enumerate(layers):
        options.layerName = lyr.name().replace(' ', '_')
        options.actionOnExistingFile = (
            QgsVectorFileWriter.CreateOrOverwriteFile if i == 0
            else QgsVectorFileWriter.CreateOrOverwriteLayer
        )
        err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            lyr, gpkg_path, QgsCoordinateTransformContext(), options
        )
        status = 'OK' if err == QgsVectorFileWriter.NoError else f'WARN: {msg}'
        print(f"      [{status}] {lyr.name()}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

print('\n' + '='*55)
print('  300,000 Streets — PyQGIS Pipeline')
print('='*55)

# 1 ── Load CSV
print('\n[1/6] Loading and cleaning CSV data...')
assess_layer = build_assessment_layer(CSV_FILE)
print(f'      {assess_layer.featureCount()} assessment points loaded')

# 2 ── School gates (only for schools with CSV data)
print('\n[2/6] Creating school gates layer...')
active_schools = {f['School'] for f in assess_layer.getFeatures()}
print(f'      Schools with data: {sorted(active_schools)}')
gates_layer = build_gates_layer(active_schools)
print(f'      {gates_layer.featureCount()} gates created')

# 3 ── Buffers
print('\n[3/6] Generating 400m and 800m walking zone buffers...')
buf_400 = build_buffer(gates_layer, 400, '400m Walking Zone')
buf_800 = build_buffer(gates_layer, 800, '800m Walking Zone')
print(f'      Buffers created for {buf_400.featureCount()} schools')

# 4 ── Symbology
print('\n[4/6] Applying symbology...')
style_assessment_layer(assess_layer)
style_gates_layer(gates_layer)
style_buffer(buf_400, '#333333', fill_opacity=0.10, border_width='0.7')
style_buffer(buf_800, '#888888', fill_opacity=0.04, border_width='0.4')
print('      Severity colours applied to assessment points')

# 5 ── Add to QGIS project
print('\n[5/6] Adding layers to QGIS project...')
project = QgsProject.instance()
project.clear()
project.setCrs(CRS_WGS84)

osm_layer = build_osm_layer()

# Layer order: OSM at bottom, then buffers, then points, gates on top
for lyr in [osm_layer, buf_800, buf_400, assess_layer, gates_layer]:
    project.addMapLayer(lyr)

print('      Layers added (bottom to top):')
print('        OpenStreetMap  →  800m Zone  →  400m Zone')
print('        Safety Assessment Points  →  School Gates')

# 6 ── Export
print('\n[6/6] Exporting GeoPackage and saving project...')
export_geopackage([gates_layer, assess_layer, buf_400, buf_800], GPKG_OUT)

project.setFileName(PROJ_OUT)
project.write()

print('\n' + '='*55)
print('  PIPELINE COMPLETE')
print('='*55)
print(f'  GeoPackage   -> {GPKG_OUT}')
print(f'  QGIS Project -> {PROJ_OUT}')
print('\n  Summary of assessment points:')
for feat in assess_layer.getFeatures():
    score = feat['Overall_score']
    score_str = f"{score:.2f}" if score is not None else 'N/A'
    print(f"    {feat['School_short']:<22} {feat['Street']:<18} "
          f"Severity={feat['Severity']:<8}  Overall={score_str}")
print('='*55)
print('\n  To update: replace school_data.csv and re-run this script.\n')
