"""
PyQGIS pipeline — builds a QGIS project with styled layers, buffers, and per-school map exports.

Guards: all QGIS imports are wrapped in try/except ImportError so this module can be imported
without QGIS installed (the run_qgis_pipeline() function will raise ImportError at call time).

Usage:
    python run_qgis.py           — standalone (sets up offscreen QGIS)
    In QGIS Console: exec(open('run_qgis.py').read())
"""
import os
import csv
import sys

from config import PROJECT_ROOT, SCHOOL_GATES, SCHOOL_SHORT_NAMES

BASE_DIR = str(PROJECT_ROOT)
CSV_FILE = os.path.join(BASE_DIR, 'school_data.csv')
OUT_DIR  = os.path.join(BASE_DIR, 'outputs')
GPKG_OUT    = os.path.join(OUT_DIR, 'school_streets.gpkg')
PROJ_OUT    = os.path.join(OUT_DIR, 'school_streets.qgz')
CRASH_CSV   = os.path.join(OUT_DIR, 'crash_data_darebin.csv')

# Raw CSV column names (with Unicode em dash U+2014)
COL_SCHOOL    = 'School name'
COL_STREET    = 'Street or location being assessed'
COL_LAT       = 'Latitude (decimal degrees)'
COL_LON       = 'Longitude (decimal degrees)'
COL_SEVERITY  = 'Overall hazard severity at this location'
COL_FAS       = 'Footpath Accessibility Score — FAS (0 to 10)'
COL_CSS       = 'Crossing Safety Score — CSS (0 to 10)'
COL_EEI       = 'Environmental Exposure Indicator — EEI (0 to 10)'
COL_DIST      = 'Approximate distance from school gate (metres)'
COL_HAZARDS   = 'Hazard types observed at this location (select all that apply)'
COL_REC_TYPE  = 'Recommended intervention type'
COL_PRIORITY  = 'Recommendation priority level'
COL_COST      = 'Estimated cost level'
COL_TIMEFRAME = 'Suggested implementation timeframe'
COL_HAZ_DESC  = 'Detailed hazard description'
COL_REC_DESC  = 'Detailed intervention description'

SEV_COLOUR = {
    'Major':    '#C0392B',
    'Moderate': '#D35400',
    'Minor':    '#1E8449',
    'Unknown':  '#888888',
}


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
    return {k.strip(): v.strip() for k, v in row.items()}


def run_qgis_pipeline():
    """
    Run the full PyQGIS pipeline.
    Raises ImportError if qgis.core is not available.
    """
    # ── QGIS imports ─────────────────────────────────────────────────────────
    try:
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsField, QgsFields, QgsCoordinateReferenceSystem,
            QgsCoordinateTransformContext, QgsVectorFileWriter,
            QgsMarkerSymbol, QgsFillSymbol, QgsCategorizedSymbolRenderer,
            QgsRendererCategory, QgsSingleSymbolRenderer, QgsRasterLayer,
            QgsRasterShader, QgsColorRampShader, QgsSingleBandPseudoColorRenderer,
            QgsRasterTransparency, QgsMapSettings, QgsMapRendererSequentialJob,
            QgsRectangle,
        )
        from qgis.PyQt.QtCore import QVariant, QSize
        from qgis.PyQt.QtGui import QColor
        import processing
    except ImportError as exc:
        raise ImportError(
            "QGIS Python bindings not found. "
            "Run this script from within the QGIS application console, or "
            "install QGIS and set up the Python environment correctly."
        ) from exc

    # ── Standalone init (skip when already running inside QGIS) ──────────────
    _standalone = not ('qgis.core' in sys.modules or 'qgis' in sys.modules)
    if _standalone:
        QGIS_PREFIX = '/Applications/QGIS.app/Contents/MacOS'
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        sys.path.insert(0, os.path.join(QGIS_PREFIX, 'lib', 'python3', 'dist-packages'))
        _app = QgsApplication([], False)  # noqa: F821
        _app.setPrefixPath(QGIS_PREFIX, True)
        _app.initQgis()
        from processing.core.Processing import Processing as _ProcCore
        _ProcCore.initialize()

    CRS_WGS84  = QgsCoordinateReferenceSystem('EPSG:4326')
    CRS_METRIC = QgsCoordinateReferenceSystem('EPSG:7855')
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Layer builders ────────────────────────────────────────────────────────

    def build_assessment_layer(csv_path):
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
                overall = round((fas + css + eei) / 3, 2) if None not in (fas, css, eei) else None
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                feat['School']        = school
                feat['School_short']  = SCHOOL_SHORT_NAMES.get(school, school)
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
        reproj = processing.run('native:reprojectlayer', {
            'INPUT': gates_layer, 'TARGET_CRS': CRS_METRIC, 'OUTPUT': 'TEMPORARY_OUTPUT',
        })['OUTPUT']
        buf = processing.run('native:buffer', {
            'INPUT': reproj, 'DISTANCE': distance_m, 'SEGMENTS': 48,
            'END_CAP_STYLE': 0, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2,
            'DISSOLVE': False, 'OUTPUT': 'TEMPORARY_OUTPUT',
        })['OUTPUT']
        buf_wgs = processing.run('native:reprojectlayer', {
            'INPUT': buf, 'TARGET_CRS': CRS_WGS84, 'OUTPUT': 'TEMPORARY_OUTPUT',
        })['OUTPUT']
        buf_wgs.setName(name)
        return buf_wgs

    def style_assessment_layer(layer):
        cats = []
        for sev, hex_col in SEV_COLOUR.items():
            sym = QgsMarkerSymbol.createSimple({
                'name': 'circle', 'color': hex_col,
                'outline_color': 'white', 'outline_width': '0.5', 'size': '5',
            })
            cats.append(QgsRendererCategory(sev, sym, sev))
        layer.setRenderer(QgsCategorizedSymbolRenderer('Severity', cats))
        layer.triggerRepaint()

    def style_gates_layer(layer):
        sym = QgsMarkerSymbol.createSimple({
            'name': 'star', 'color': '#1A1A1A',
            'outline_color': 'white', 'outline_width': '0.6', 'size': '8',
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))
        layer.triggerRepaint()

    def style_buffer(layer, hex_col, fill_opacity=0.08, border_width='0.5'):
        fill = QColor(hex_col)
        fill.setAlphaF(fill_opacity)
        border = QColor(hex_col)
        sym = QgsFillSymbol.createSimple({
            'color': fill.name(QColor.HexArgb), 'outline_color': border.name(),
            'outline_width': border_width, 'style': 'solid',
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))
        layer.triggerRepaint()

    def build_crash_layer(crash_csv):
        if not os.path.exists(crash_csv):
            print('      WARNING: crash_data_darebin.csv not found — run crash_analysis.py first.')
            return None
        fields = QgsFields()
        for name, vtype in [
            ('nearest_school', QVariant.String),
            ('dist_to_gate_m', QVariant.Double),
            ('ACCIDENT_NO',    QVariant.String),
            ('ACCIDENTDATE',   QVariant.String),
            ('PED_OR_CYC',     QVariant.String),
        ]:
            fields.append(QgsField(name, vtype))
        layer = QgsVectorLayer('Point?crs=EPSG:4326', 'Road Crashes (Ped/Cyc)', 'memory')
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        features = []
        try:
            with open(crash_csv, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                lat_col  = next((h for h in headers if h.upper() in ('LAT', 'LATITUDE', 'Y')), None)
                lon_col  = next((h for h in headers if h.upper() in ('LON', 'LONG', 'LONGITUDE', 'X')), None)
                acc_col  = next((h for h in headers if 'ACCIDENT_NO' in h.upper()), headers[0] if headers else None)
                date_col = next((h for h in headers if 'DATE' in h.upper()), None)
                if not lat_col or not lon_col:
                    print(f'      WARNING: lat/lon columns not found. Columns: {headers[:8]}')
                    return None
                for raw in reader:
                    lat = _safe_float(raw.get(lat_col))
                    lon = _safe_float(raw.get(lon_col))
                    if lat is None or lon is None:
                        continue
                    feat = QgsFeature(layer.fields())
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
                    feat['nearest_school'] = raw.get('nearest_school', '')
                    feat['dist_to_gate_m'] = _safe_float(raw.get('dist_to_gate_m'))
                    feat['ACCIDENT_NO']    = raw.get(acc_col, '') if acc_col else ''
                    feat['ACCIDENTDATE']   = raw.get(date_col, '') if date_col else ''
                    feat['PED_OR_CYC']     = str(raw.get('PED_OR_CYC', 'True'))
                    features.append(feat)
        except Exception as e:
            print(f'      WARNING: Could not load crash data: {e}')
            return None
        provider.addFeatures(features)
        layer.updateExtents()
        return layer

    def style_crash_layer(layer):
        sym = QgsMarkerSymbol.createSimple({
            'name': 'diamond', 'color': '#2980B9',
            'outline_color': 'white', 'outline_width': '0.5', 'size': '5',
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))
        layer.triggerRepaint()

    def build_osm_layer():
        uri = ('type=xyz'
               '&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png'
               '&zmax=19&zmin=0&crs=EPSG:3857')
        layer = QgsRasterLayer(uri, 'OpenStreetMap', 'wms')
        if not layer.isValid():
            print('      WARNING: OSM tile layer failed to load (no internet?)')
        return layer

    def load_kde_layer(kde_path):
        if not os.path.exists(kde_path):
            print('      WARNING: kde_heatmap.tif not found — run main.py first.')
            return None
        layer = QgsRasterLayer(kde_path, 'Hazard Heatmap (KDE)', 'gdal')
        if not layer.isValid():
            print(f'      WARNING: KDE raster could not be loaded from {kde_path}')
            return None
        return layer

    def style_kde_layer(layer):
        provider = layer.dataProvider()
        stats    = provider.bandStatistics(1)
        min_val  = max(stats.minimumValue, 0.001)
        max_val  = stats.maximumValue
        mid_val  = (min_val + max_val) / 2
        ramp_items = [
            QgsColorRampShader.ColorRampItem(min_val, QColor('#1E8449'), 'Low'),
            QgsColorRampShader.ColorRampItem(mid_val, QColor('#F4D03F'), 'Medium'),
            QgsColorRampShader.ColorRampItem(max_val, QColor('#C0392B'), 'High'),
        ]
        ramp = QgsColorRampShader()
        ramp.setColorRampType(QgsColorRampShader.Interpolated)
        ramp.setColorRampItemList(ramp_items)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(ramp)
        renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
        renderer.setClassificationMin(min_val)
        renderer.setClassificationMax(max_val)
        layer.setRenderer(renderer)
        t_pixel = QgsRasterTransparency.TransparentSingleValuePixel()
        t_pixel.min = -9999
        t_pixel.max = 0.0
        t_pixel.percentTransparent = 100
        transparency = QgsRasterTransparency()
        transparency.setTransparentSingleValuePixelList([t_pixel])
        layer.renderer().setRasterTransparency(transparency)
        layer.setOpacity(0.65)
        layer.triggerRepaint()

    def export_school_maps(active_schools, osm_layer, kde_layer, crash_layer,
                           buf_800, buf_400, assess_layer, gates_layer, out_dir):
        D_LAT = 1.8 / 111.0
        D_LON = 1.8 / 87.8
        render_stack = [l for l in
                        [gates_layer, assess_layer, crash_layer, buf_400, buf_800, kde_layer, osm_layer]
                        if l and l.isValid()]
        exported = []
        for school_name, info in SCHOOL_GATES.items():
            if school_name not in active_schools:
                continue
            lat, lon  = info['lat'], info['lon']
            short     = SCHOOL_SHORT_NAMES.get(school_name, school_name)
            safe_name = short.replace(' ', '_').replace('/', '_')
            out_path  = os.path.join(out_dir, f'map_{safe_name}.png')
            extent = QgsRectangle(lon - D_LON, lat - D_LAT, lon + D_LON, lat + D_LAT)
            settings = QgsMapSettings()
            settings.setLayers(render_stack)
            settings.setOutputSize(QSize(1200, 900))
            settings.setExtent(extent)
            settings.setDestinationCrs(CRS_WGS84)
            job = QgsMapRendererSequentialJob(settings)
            job.start()
            job.waitForFinished()
            job.renderedImage().save(out_path)
            print(f'      Saved -> {out_path}')
            exported.append(out_path)
        return exported

    def export_geopackage(layers, gpkg_path):
        file_exists = os.path.exists(gpkg_path)
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        for i, lyr in enumerate(layers):
            options.layerName = lyr.name().replace(' ', '_')
            options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteFile if (i == 0 and not file_exists)
                else QgsVectorFileWriter.CreateOrOverwriteLayer
            )
            err, msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                lyr, gpkg_path, QgsCoordinateTransformContext(), options
            )
            status = 'OK' if err == QgsVectorFileWriter.NoError else f'WARN: {msg}'
            print(f"      [{status}] {lyr.name()}")

    # ── Pipeline ──────────────────────────────────────────────────────────────
    print('\n' + '='*55)
    print('  300,000 Streets — PyQGIS Pipeline')
    print('='*55)

    print('\n[1/7] Loading and cleaning CSV data...')
    assess_layer = build_assessment_layer(CSV_FILE)
    print(f'      {assess_layer.featureCount()} assessment points loaded')

    print('\n[2/7] Creating school gates layer...')
    active_schools = {f['School'] for f in assess_layer.getFeatures()}
    print(f'      Schools with data: {sorted(active_schools)}')
    gates_layer = build_gates_layer(active_schools)
    print(f'      {gates_layer.featureCount()} gates created')

    print('\n[3/7] Generating 400m and 800m walking zone buffers...')
    buf_400 = build_buffer(gates_layer, 400, '400m Walking Zone')
    buf_800 = build_buffer(gates_layer, 800, '800m Walking Zone')
    print(f'      Buffers created for {buf_400.featureCount()} schools')

    print('\n[4/7] Applying symbology...')
    style_assessment_layer(assess_layer)
    style_gates_layer(gates_layer)
    style_buffer(buf_400, '#333333', fill_opacity=0.10, border_width='0.7')
    style_buffer(buf_800, '#888888', fill_opacity=0.04, border_width='0.4')
    print('      Severity colours applied to assessment points')

    print('\n[5/8] Loading KDE heatmap...')
    kde_layer = load_kde_layer(os.path.join(OUT_DIR, 'kde_heatmap.tif'))
    if kde_layer:
        style_kde_layer(kde_layer)
        print('      KDE raster loaded and styled with green-yellow-red gradient')
    else:
        print('      Skipping KDE — run main.py first')

    print('\n[6/8] Loading road crash data...')
    crash_layer = build_crash_layer(CRASH_CSV)
    if crash_layer:
        style_crash_layer(crash_layer)
        print(f'      {crash_layer.featureCount()} crash points loaded')
    else:
        print('      Skipping crash layer — run crash_downloader.py first')

    print('\n[7/8] Adding layers to QGIS project...')
    project = QgsProject.instance()
    project.clear()
    project.setCrs(CRS_WGS84)

    osm_layer = build_osm_layer()

    NETWORKS_GPKG = os.path.join(OUT_DIR, 'networks.gpkg')
    _net_cfg = [
        ('walk_400m',    'Walk Network 400m',    QColor('#27AE60'), 1.5),
        ('walk_800m',    'Walk Network 800m',    QColor('#5DBB82'), 1.0),
        ('cycling_400m', 'Cycling Network 400m', QColor('#1A8FC1'), 2.0),
        ('cycling_800m', 'Cycling Network 800m', QColor('#5BAFD4'), 1.5),
        ('roads_400m',   'Arterial Roads 400m',  QColor('#C0392B'), 2.5),
        ('roads_800m',   'Arterial Roads 800m',  QColor('#D46A5B'), 2.0),
    ]
    network_layers = []
    if os.path.exists(NETWORKS_GPKG):
        for _key, _label, _colour, _width in _net_cfg:
            _lyr = QgsVectorLayer(f'{NETWORKS_GPKG}|layername={_key}', _label, 'ogr')
            if _lyr.isValid():
                _sym = _lyr.renderer().symbol()
                _sym.setColor(_colour)
                _sym.setWidth(_width)
                network_layers.append(_lyr)
        if network_layers:
            print(f'      Loaded {len(network_layers)} network layers from networks.gpkg')
    else:
        print('      networks.gpkg not found — run osm_extractor.py to add network layers')

    for lyr in ([osm_layer, kde_layer, buf_800, buf_400]
                + network_layers
                + [crash_layer, assess_layer, gates_layer]):
        if lyr and lyr.isValid():
            project.addMapLayer(lyr)

    print('      Layers added (bottom to top):')
    print('        OSM → KDE → 800m/400m Zone → Walk/Cycling/Roads networks')
    print('        Road Crashes → Safety Assessment Points → School Gates')

    _iface = globals().get('iface')
    if _iface:
        _iface.mapCanvas().zoomToFullExtent()
        _iface.mapCanvas().refresh()
        print('      Canvas refreshed — all layers now visible in QGIS')

    print('\n[8/8] Exporting per-school map images...')
    export_school_maps(active_schools, osm_layer, kde_layer, crash_layer,
                       buf_800, buf_400, assess_layer, gates_layer, OUT_DIR)

    print('      Exporting GeoPackage and saving project...')
    gpkg_layers = [l for l in [gates_layer, assess_layer, buf_400, buf_800, crash_layer] if l]
    export_geopackage(gpkg_layers, GPKG_OUT)

    project.setFileName(PROJ_OUT)
    project.write()

    print('\n' + '='*55)
    print('  PIPELINE COMPLETE')
    print('='*55)
    print(f'  GeoPackage   -> {GPKG_OUT}')
    print(f'  QGIS Project -> {PROJ_OUT}')
    print(f'  KDE Raster   -> {os.path.join(OUT_DIR, "kde_heatmap.tif")}')
    print(f'  Crash Data   -> {CRASH_CSV}')
    print(f'  School maps  -> outputs/map_<school>.png')
    print('\n  Summary of assessment points:')
    for feat in assess_layer.getFeatures():
        score = feat['Overall_score']
        score_str = f"{score:.2f}" if score is not None else 'N/A'
        print(f"    {feat['School_short']:<22} {feat['Street']:<18} "
              f"Severity={feat['Severity']:<8}  Overall={score_str}")
    print('='*55)
    print('\n  To update: replace school_data.csv and re-run python run_qgis.py\n')


if __name__ == '__main__':
    run_qgis_pipeline()
