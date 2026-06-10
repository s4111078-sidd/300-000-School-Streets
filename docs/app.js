/* ── 300,000 Streets — Dashboard app ──────────────────────── */

const HS_NAMES = {
  HS1:  'Pedestrians',
  HS2:  'Easy to cross',
  HS3:  'Shade & shelter',
  HS4:  'Rest places',
  HS5:  'Not too noisy',
  HS6:  'Active travel',
  HS7:  'Feel safe',
  HS8:  'Things to do',
  HS9:  'Feel relaxed',
  HS10: 'Clean air',
};
const HS_CODES = Object.keys(HS_NAMES);

// Colour helpers
function scoreColor(v) {
  if (v < 4.0) return '#C0392B';
  if (v < 6.0) return '#D35400';
  return '#1E8449';
}
function severityClass(s) {
  if (s === 'Major')    return 'badge badge-major';
  if (s === 'Moderate') return 'badge badge-moderate';
  return 'badge badge-minor';
}
function priorityClass(p) {
  if (p === 'High')   return 'badge priority-high';
  if (p === 'Medium') return 'badge priority-medium';
  return 'badge priority-low';
}

// ── State ──────────────────────────────────────────────────────
let appData         = null;
let activeSchoolIdx = 0;
let allRecs         = [];
let radarCharts     = {};

// ── Bootstrap ─────────────────────────────────────────────────
fetch('./data/data.json')
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(data => {
    appData = data;
    allRecs = data.schools.flatMap(s =>
      s.recommendations.map(r => ({ ...r, school: s.short_name }))
    );
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('main-content').classList.remove('hidden');
    initNavbar();
    initHero(data);
    initMap(data);
    initSchools(data.schools);
    initScenario(data);
    initAnalysis(data);
    initRecommendations(data.schools);
  })
  .catch(err => {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('error-banner').classList.remove('hidden');
    document.getElementById('error-msg').textContent = ' ' + err.message;
  });

// ── Navbar hamburger ──────────────────────────────────────────
function initNavbar() {
  const btn   = document.getElementById('hamburger');
  const menu  = document.getElementById('mobile-menu');
  const open  = document.getElementById('ham-open');
  const close = document.getElementById('ham-close');

  btn.addEventListener('click', () => {
    const shown = !menu.classList.contains('hidden');
    menu.classList.toggle('hidden', shown);
    open.classList.toggle('hidden', !shown);
    close.classList.toggle('hidden', shown);
  });

  menu.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      menu.classList.add('hidden');
      open.classList.remove('hidden');
      close.classList.add('hidden');
    });
  });
}

// ── HERO ──────────────────────────────────────────────────────
function initHero(data) {
  const stats = data.stats || {};
  const el    = document.getElementById('hero-stats');

  const items = [
    {
      value: stats.schools_assessed ?? 3,
      label: 'schools assessed',
    },
    {
      value: stats.major_hazards ?? 1,
      label: 'major hazard' + ((stats.major_hazards ?? 1) !== 1 ? 's' : ''),
      color: '#C0392B',
    },
    {
      value: stats.crash_darebin ? `${stats.crash_darebin}+` : '250+',
      label: 'Darebin crashes (2021–25)',
    },
    {
      value: `r = ${stats.equity_r ?? 0.84}`,
      label: 'equity–safety correlation',
      color: '#028090',
    },
    {
      value: stats.peak_crash_hour ?? '17:00',
      label: 'peak crash hour',
      color: '#D35400',
    },
  ];

  el.innerHTML = items.map(item => `
    <div class="hero-stat-card">
      <div class="hero-stat-value" style="${item.color ? `color:${item.color}` : ''}">
        ${item.value}
      </div>
      <div class="hero-stat-label">${item.label}</div>
    </div>
  `).join('');
}

// ── MAP ────────────────────────────────────────────────────────
function initMap(data) {
  const schools       = data.schools       || [];
  const crashGeoJson  = data.crash_geojson || null;
  const heatPoints    = data.heatmap_points || [];
  const networks      = data.networks       || {};
  const spatialStats  = data.spatial_stats  || {};

  const map = L.map('map').setView([-37.72, 145.01], 14);

  // ── Base tiles ──
  const osmTile = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  });
  const darkTile = L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; CARTO',
    maxZoom: 19,
  });
  osmTile.addTo(map);

  // ── Layer groups ──
  const schoolLayer = L.layerGroup().addTo(map);
  const crashLayer  = L.layerGroup().addTo(map);
  const walkLayer   = L.layerGroup();
  const cycleLayer  = L.layerGroup().addTo(map);
  const heatLayer   = L.layerGroup().addTo(map);
  const seifaLayer  = L.layerGroup().addTo(map);

  // ── School markers ──
  schools.forEach((school, idx) => {
    const color = school.severity === 'Major' ? '#C0392B'
                : school.severity === 'Moderate' ? '#D35400' : '#1E8449';
    const isPulsing = school.severity === 'Major';
    const icon = L.divIcon({
      className: '',
      html: isPulsing
        ? `<div class="pulse-marker"></div>`
        : `<div style="width:18px;height:18px;border-radius:50%;background:${color};
               border:2px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,0.4)"></div>`,
      iconSize: [18, 18], iconAnchor: [9, 9],
    });

    const ss = spatialStats[school.short_name] || {};
    const statsHtml = ss.crossings_400m != null ? `
      <div style="margin-top:8px;font-size:11px;color:#555;border-top:1px solid #eee;padding-top:6px">
        <b>OSM features (400m)</b><br>
        🚶 Footpath: ${ss.footpath_pct_400m ?? '—'}% &nbsp;|&nbsp;
        🚦 Crossings: ${ss.crossings_400m ?? '—'}<br>
        🌳 Trees (100m): ${ss.tree_count_100m ?? '—'} &nbsp;|&nbsp;
        🪑 Benches: ${ss.bench_count_200m ?? '—'}<br>
        🚲 Cycling: ${ss.cycle_pct_400m ?? '—'}% &nbsp;|&nbsp;
        🚌 PT stops: ${ss.pt_stops_400m ?? '—'}<br>
        🌿 Green space: ${ss.green_pct_400m ?? '—'}% &nbsp;|&nbsp;
        ⛽ Arterial: ${ss.arterial_pct_400m ?? '—'}%
      </div>` : '';

    const seifa = school.seifa || {};
    const seifaHtml = seifa.irsd_decile ? `
      <div style="margin-top:6px;font-size:11px;color:#666">
        SEIFA Decile ${seifa.irsd_decile} — ${seifa.disadvantage_level}
      </div>` : '';

    const popup = L.popup({ maxWidth: 260, className: 'school-popup' }).setContent(`
      <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;line-height:1.5">
        <div class="map-popup-title">${school.name}</div>
        <div style="margin:4px 0">
          <span class="map-popup-score">${school.overall_score}</span>
          <span style="color:#888;font-size:11px"> / 10</span>
          &nbsp;<span class="${severityClass(school.severity)}">${school.severity}</span>
        </div>
        ${seifaHtml}${statsHtml}
        <button class="map-popup-btn" style="margin-top:8px" onclick="goToSchool(${idx})">
          View School Details →
        </button>
      </div>`);

    L.marker([school.lat, school.lng], { icon, zIndexOffset: 1000 })
      .addTo(schoolLayer)
      .bindPopup(popup);
  });

  // ── Crash markers ──
  const sevColor = { 1: '#7F1D1D', 2: '#DC2626', 3: '#F97316' };
  if (crashGeoJson && crashGeoJson.features) {
    crashGeoJson.features.forEach(feat => {
      const [lon, lat] = feat.geometry.coordinates;
      const p = feat.properties;
      const sev = p.severity || 3;
      const col = sevColor[sev] || '#F97316';

      const circle = L.circleMarker([lat, lon], {
        radius: sev === 1 ? 10 : sev === 2 ? 8 : 6,
        fillColor: col, color: '#fff', weight: 1.5,
        fillOpacity: 0.85, opacity: 1,
      });

      const speedStr = p.speed_zone ? `${p.speed_zone} km/h zone` : 'Unknown zone';
      const tooltip = `<b>${p.severity_label}</b><br>${p.type || 'Crash'}<br>${p.date} ${p.time}`;
      circle.bindTooltip(tooltip, { sticky: true, className: 'crash-tooltip' });
      circle.bindPopup(`
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:12px;min-width:200px">
          <div style="font-weight:700;font-size:14px;color:${col};margin-bottom:4px">
            ${p.severity_label}
          </div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="color:#888;padding:2px 6px 2px 0">Type</td><td>${p.type || '—'}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Date</td><td>${p.date} ${p.time}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Day</td><td>${p.day || '—'}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Speed zone</td><td>${speedStr}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Light</td><td>${p.light || '—'}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Road type</td><td>${p.road_geometry || '—'}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Killed</td><td>${p.killed ?? 0}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Serious injury</td><td>${p.injured_serious ?? 0}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Nearest school</td><td>${p.school || '—'}</td></tr>
            <tr><td style="color:#888;padding:2px 6px 2px 0">Distance to gate</td><td>${p.dist_m != null ? p.dist_m + 'm' : '—'}</td></tr>
          </table>
        </div>`, { maxWidth: 260 });
      circle.addTo(crashLayer);
    });
  }

  // ── Walk network ──
  if (networks.walk && networks.walk.features) {
    L.geoJSON(networks.walk, {
      style: () => ({ color: '#3B82F6', weight: 1.8, opacity: 0.7 }),
      onEachFeature: (feat, layer) => {
        if (feat.properties.highway) {
          layer.bindTooltip(`Walk: ${feat.properties.highway}`, { sticky: true });
        }
      }
    }).addTo(walkLayer);
  }

  // ── Cycling network ──
  if (networks.cycling && networks.cycling.features) {
    L.geoJSON(networks.cycling, {
      style: feat => {
        const hw = (feat.properties.highway || '').toLowerCase();
        const isProtected = hw.includes('cycleway') || hw.includes('path');
        return { color: isProtected ? '#10B981' : '#6EE7B7', weight: isProtected ? 2.5 : 1.5, opacity: 0.85 };
      },
      onEachFeature: (feat, layer) => {
        layer.bindTooltip(`Cycle: ${feat.properties.highway || 'route'}`, { sticky: true });
      }
    }).addTo(cycleLayer);
  }

  // ── Heatmap ──
  if (heatPoints.length > 0 && L.heatLayer) {
    L.heatLayer(heatPoints, {
      radius: 20, blur: 25, maxZoom: 17,
      gradient: { 0.2: '#FED7AA', 0.5: '#F97316', 0.8: '#DC2626', 1.0: '#7F1D1D' },
    }).addTo(heatLayer);
  }

  // ── SEIFA catchment circles ──
  const seifaColors = { 1: '#7F1D1D', 2: '#B91C1C', 3: '#DC2626', 4: '#F97316',
                        5: '#FBBF24', 6: '#A3E635', 7: '#4ADE80', 8: '#22C55E',
                        9: '#16A34A', 10: '#166534' };
  schools.forEach(school => {
    const s = school.seifa || {};
    if (!s.irsd_decile) return;
    const decile = Math.round(s.irsd_decile);
    const col = seifaColors[decile] || '#888';
    L.circle([school.lat, school.lng], {
      radius: 400, color: col, fillColor: col,
      fillOpacity: 0.12, weight: 2, dashArray: '6 4',
    })
    .bindTooltip(`
      <b>${school.short_name}</b><br>
      SEIFA IRSD Decile: ${s.irsd_decile}<br>
      ${s.disadvantage_level || ''}<br>
      Population: ${s.catchment_population?.toLocaleString() || '—'}`,
      { sticky: false })
    .addTo(seifaLayer);
  });

  // ── Layer control ──
  const baseMaps = { 'OpenStreetMap': osmTile, 'Dark': darkTile };
  const overlays = {
    '🏫 Schools':        schoolLayer,
    '💥 Crash spots':    crashLayer,
    '🔥 Crash heatmap':  heatLayer,
    '🚶 Walk network':   walkLayer,
    '🚲 Cycling network': cycleLayer,
    '📊 SEIFA catchments': seifaLayer,
  };
  L.control.layers(baseMaps, overlays, { collapsed: false, position: 'topright' }).addTo(map);

  // ── Legend ──
  const legend = L.control({ position: 'bottomleft' });
  legend.onAdd = () => {
    const div = L.DomUtil.create('div', 'map-legend');
    div.innerHTML = `
      <div style="font-family:-apple-system,sans-serif;font-size:11px;background:#fff;
           padding:8px 10px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,0.25);line-height:1.7">
        <b style="display:block;margin-bottom:4px">Crash severity</b>
        <span style="color:#DC2626">●</span> Serious injury &nbsp;
        <span style="color:#F97316">●</span> Other injury<br>
        <b style="display:block;margin:4px 0 2px">Networks</b>
        <span style="color:#3B82F6">━</span> Walk &nbsp;
        <span style="color:#10B981">━</span> Cycling (protected) &nbsp;
        <span style="color:#6EE7B7">━</span> Cycling<br>
        <b style="display:block;margin:4px 0 2px">SEIFA decile</b>
        <span style="color:#DC2626">●</span> Most disadvantaged (1–3) &nbsp;
        <span style="color:#22C55E">●</span> Least (8–10)
      </div>`;
    return div;
  };
  legend.addTo(map);
}

function goToSchool(idx) {
  document.getElementById('schools-section').scrollIntoView({ behavior: 'smooth' });
  setTimeout(() => activateTab(idx), 400);
}
window.goToSchool = goToSchool;

// ── SCHOOLS SECTION ────────────────────────────────────────────
function initSchools(schools) {
  const tabsEl    = document.getElementById('school-tabs');
  const contentEl = document.getElementById('school-content');

  schools.forEach((school, idx) => {
    const btn = document.createElement('button');
    btn.className = 'school-tab' + (idx === 0 ? ' active' : '');
    btn.textContent = school.short_name;
    btn.addEventListener('click', () => activateTab(idx));
    tabsEl.appendChild(btn);
  });

  schools.forEach((school, idx) => {
    const panel = buildSchoolPanel(school, idx);
    panel.id = `school-panel-${idx}`;
    panel.classList.toggle('hidden', idx !== 0);
    contentEl.appendChild(panel);
  });

  setTimeout(() => drawRadar(schools[0], 0), 50);
}

function activateTab(idx) {
  document.querySelectorAll('.school-tab').forEach((btn, i) => {
    btn.classList.toggle('active', i === idx);
  });
  document.querySelectorAll('[id^="school-panel-"]').forEach((panel, i) => {
    panel.classList.toggle('hidden', i !== idx);
  });
  activeSchoolIdx = idx;
  if (!radarCharts[idx]) {
    setTimeout(() => drawRadar(appData.schools[idx], idx), 50);
  }
}

function buildSchoolPanel(school, idx) {
  const panel = document.createElement('div');
  panel.className = 'card p-6';

  panel.innerHTML = `
    <div class="flex flex-col md:flex-row gap-6">

      <!-- LEFT: radar chart -->
      <div class="md:w-2/5 flex flex-col items-center justify-start">
        <div class="radar-wrap">
          <canvas id="radar-${idx}"></canvas>
        </div>
      </div>

      <!-- RIGHT: details -->
      <div class="md:w-3/5">
        <div class="flex flex-wrap items-center gap-3 mb-1">
          <h3 class="text-xl font-bold text-gray-900">${school.name}</h3>
          <span class="${severityClass(school.severity)}">${school.severity}</span>
        </div>
        <p class="text-sm text-gray-400 mb-3">${school.address}</p>

        <!-- Overall score -->
        <div class="flex items-baseline gap-1 mb-4">
          <span style="font-size:3rem;font-weight:800;color:#028090;line-height:1">
            ${school.overall_score}
          </span>
          <span class="text-gray-400 text-lg">/10</span>
          <span class="text-xs text-gray-400 ml-2">overall HS score</span>
        </div>

        <!-- Indicator bars -->
        <div class="space-y-0.5">
          ${HS_CODES.map(code => {
            const val   = school.hs_scores[code] ?? 0;
            const color = scoreColor(val);
            const pct   = (val / 10 * 100).toFixed(1);
            return `
              <div class="indicator-row">
                <span class="indicator-label">${code} — ${HS_NAMES[code]}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="width:${pct}%;background:${color}"></div>
                </div>
                <span class="bar-score" style="color:${color}">${val}</span>
              </div>`;
          }).join('')}
        </div>

        <!-- Key hazard -->
        ${school.key_hazard ? `
          <div class="hazard-box">
            <strong>Key hazard</strong>
            ${esc(school.key_hazard)}
            ${school.key_recommendation
              ? `<br><span class="text-gray-500 text-xs mt-1 block">
                   Recommended: ${esc(school.key_recommendation)}
                 </span>`
              : ''}
          </div>` : ''}
      </div>
    </div>
  `;
  return panel;
}

function drawRadar(school, idx) {
  const canvas = document.getElementById(`radar-${idx}`);
  if (!canvas || radarCharts[idx]) return;

  const scores = HS_CODES.map(c => school.hs_scores[c] ?? 0);
  const labels = HS_CODES.map(c => `${c}\n${HS_NAMES[c]}`);

  radarCharts[idx] = new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [
        {
          label: school.short_name,
          data: scores,
          backgroundColor: 'rgba(2,128,144,0.25)',
          borderColor: '#028090',
          borderWidth: 2,
          pointBackgroundColor: '#028090',
          pointRadius: 3,
        },
        {
          label: 'Min threshold (6.0)',
          data: Array(10).fill(6),
          backgroundColor: 'rgba(0,0,0,0)',
          borderColor: '#AAAAAA',
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        r: {
          min: 0,
          max: 10,
          ticks: { stepSize: 2, font: { size: 9 }, color: '#999' },
          pointLabels: { font: { size: 9 }, color: '#555' },
          grid:       { color: '#EEEEEE' },
          angleLines: { color: '#DDDDDD' },
        },
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 10 }, boxWidth: 12, padding: 8 },
        },
      },
    },
  });
}

// ── SCENARIO SECTION ──────────────────────────────────────────
function initScenario(data) {
  const scenarios = data.scenarios;
  const schools   = data.schools;

  if (!scenarios || Object.keys(scenarios).length === 0) {
    document.getElementById('scenario-section').innerHTML = `
      <div class="max-w-7xl mx-auto px-4 py-12">
        <h2 class="section-heading">What-if Scenario Analysis</h2>
        <p class="section-sub mt-2">
          Run <code>python prepare_data.py</code> after the full pipeline to enable scenarios.
        </p>
      </div>`;
    return;
  }

  const tabsEl = document.getElementById('scenario-tabs');
  let activeSchool = schools[0].short_name;
  let scenarioChart = null;

  // School tabs
  schools.forEach((school, i) => {
    const btn = document.createElement('button');
    btn.className = 'school-tab' + (i === 0 ? ' active' : '');
    btn.textContent = school.short_name;
    btn.addEventListener('click', () => {
      tabsEl.querySelectorAll('.school-tab').forEach((b, j) =>
        b.classList.toggle('active', j === i)
      );
      activeSchool = school.short_name;
      renderInterventionGrid(activeSchool);
      clearScenarioResult();
    });
    tabsEl.appendChild(btn);
  });

  renderInterventionGrid(activeSchool);
  clearScenarioResult();

  function renderInterventionGrid(schoolName) {
    const grid         = document.getElementById('intervention-grid');
    const schoolScenarios = scenarios[schoolName] || {};

    grid.innerHTML = Object.entries(schoolScenarios).map(([key, s]) => {
      const sign  = s.delta_overall >= 0 ? '+' : '';
      const color = s.delta_overall > 0.05 ? '#1E8449' :
                    s.delta_overall < -0.05 ? '#C0392B' : '#888';
      return `
        <button class="iv-pill" data-key="${key}"
                onclick="selectIntervention('${key}', '${schoolName}')">
          <span class="iv-name">${esc(s.label)}</span>
          <span class="iv-badge">
            <span style="color:${color};font-weight:700">
              ${sign}${s.delta_overall.toFixed(2)}
            </span>
            &nbsp;·&nbsp;${esc(s.timeframe)}
          </span>
        </button>`;
    }).join('');
  }

  window.selectIntervention = function(key, schoolName) {
    document.querySelectorAll('.iv-pill').forEach(p =>
      p.classList.toggle('active', p.dataset.key === key)
    );
    const s = (scenarios[schoolName] || {})[key];
    if (s) renderScenarioResult(s, schoolName, scenarioChart, c => { scenarioChart = c; });
  };

  function clearScenarioResult() {
    document.getElementById('scenario-result').classList.add('hidden');
    document.getElementById('scenario-placeholder').classList.remove('hidden');
    document.querySelectorAll('.iv-pill').forEach(p => p.classList.remove('active'));
    if (scenarioChart) { scenarioChart.destroy(); scenarioChart = null; }
  }
}

function renderScenarioResult(s, schoolName, existingChart, setChart) {
  document.getElementById('scenario-placeholder').classList.add('hidden');
  document.getElementById('scenario-result').classList.remove('hidden');

  const sevSame   = s.baseline_severity === s.scenario_severity;
  const sevHtml   = sevSame
    ? `<span class="${severityClass(s.baseline_severity)}">${s.baseline_severity}</span>
       <span class="text-gray-400 text-xs ml-1">(no change)</span>`
    : `<span class="${severityClass(s.baseline_severity)}">${s.baseline_severity}</span>
       <span class="text-gray-400 mx-1">→</span>
       <span class="${severityClass(s.scenario_severity)}">${s.scenario_severity}</span>`;

  const dSign  = s.delta_overall >= 0 ? '+' : '';
  const dColor = s.delta_overall > 0.05 ? '#1E8449' :
                 s.delta_overall < -0.05 ? '#C0392B' : '#888';

  document.getElementById('scenario-meta').innerHTML = `
    <div class="scenario-stat">
      <div class="scenario-stat-label">HS Overall</div>
      <div class="scenario-stat-val">
        <span class="text-gray-500">${s.baseline_overall}</span>
        <span class="text-gray-300 mx-1">→</span>
        <strong>${s.scenario_overall}</strong>
        <span style="color:${dColor};font-size:0.8rem;margin-left:4px">
          (${dSign}${s.delta_overall})
        </span>
      </div>
    </div>
    <div class="scenario-stat">
      <div class="scenario-stat-label">Severity</div>
      <div class="scenario-stat-val">${sevHtml}</div>
    </div>
    <div class="scenario-stat">
      <div class="scenario-stat-label">Cost</div>
      <div class="scenario-stat-val text-sm">${esc(s.cost)}</div>
    </div>
    <div class="scenario-stat">
      <div class="scenario-stat-label">Timeframe</div>
      <div class="scenario-stat-val text-sm">${esc(s.timeframe)}</div>
    </div>
  `;

  // Draw chart
  const canvas = document.getElementById('scenario-chart');
  if (existingChart) existingChart.destroy();

  const baseline = HS_CODES.map(c => s.baseline[c] ?? 0);
  const scenario = HS_CODES.map(c => s.scenario[c] ?? 0);

  const newChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: HS_CODES.map(c => `${c}\n${HS_NAMES[c]}`),
      datasets: [
        {
          label: 'Baseline',
          data: baseline,
          backgroundColor: 'rgba(150,150,150,0.45)',
          borderRadius: 3,
        },
        {
          label: 'After intervention',
          data: scenario,
          backgroundColor: scenario.map((v, i) =>
            v > baseline[i] + 0.05 ? 'rgba(30,132,73,0.75)' :
            v < baseline[i] - 0.05 ? 'rgba(192,57,43,0.75)' :
            'rgba(2,128,144,0.5)'
          ),
          borderRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${Number(ctx.raw).toFixed(2)}`,
          },
        },
      },
      scales: {
        x: { ticks: { font: { size: 10 }, maxRotation: 0 } },
        y: {
          min: 0, max: 10,
          title: { display: true, text: 'HS Score (0–10)', font: { size: 11 } },
          grid: { color: '#EEEEEE' },
        },
      },
    },
  });
  setChart(newChart);
}

// ── ANALYSIS SECTION ──────────────────────────────────────────
function initAnalysis(data) {
  buildHsCharts(data.charts);
  buildMlChart(data.ml_results);
  buildMlChartImages(data.charts);
  buildSeifaCards(data.schools);
  buildExtraCharts(data.charts);
  initLightbox();
}

function buildHsCharts(charts) {
  const el = document.getElementById('hs-charts');
  const items = [
    { file: charts.chart1, caption: charts.chart1_caption },
    { file: charts.chart2, caption: charts.chart2_caption },
    { file: charts.chart3, caption: charts.chart3_caption },
  ];
  el.innerHTML = items.map(item => chartCardHtml(item.file, item.caption)).join('');
}

function buildMlChart(mlResults) {
  const canvas = document.getElementById('ml-chart');
  const labels = mlResults.map(r => `${r.indicator} — ${r.name}`);
  const values = mlResults.map(r => r.mae);
  const colors = values.map(v =>
    v < 1.5 ? '#1E8449' : v < 3.0 ? '#D35400' : '#C0392B'
  );

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'MAE',
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` MAE: ${ctx.raw.toFixed(3)}` },
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Mean Absolute Error (lower = better)',
            font: { size: 11 },
            color: '#666',
          },
          min: 0,
          grid: { color: '#EEEEEE' },
        },
        y: {
          ticks: { font: { size: 11 } },
          grid: { display: false },
        },
      },
    },
  });
}

function buildMlChartImages(charts) {
  const el = document.getElementById('ml-chart-images');
  const items = [
    { file: charts.prediction,         caption: 'LOO-CV predicted vs actual HS scores per school' },
    { file: charts.feature_importance, caption: 'Ridge coefficients — top predictors per HS indicator' },
  ];
  el.innerHTML = items.map(item => chartCardHtml(item.file, item.caption)).join('');
}

function buildSeifaCards(schools) {
  const el = document.getElementById('seifa-cards');
  el.innerHTML = schools.map(school => {
    const s = school.seifa;
    if (!s || !s.irsd_score) return `
      <div class="seifa-card">
        <p class="text-sm font-semibold text-gray-700">${school.short_name}</p>
        <p class="text-xs text-gray-400 mt-1">SEIFA data not available</p>
      </div>`;

    const decilePct  = Math.min((s.irsd_decile / 10) * 100, 100).toFixed(0);
    const decileColor =
      s.irsd_decile <= 3 ? '#C0392B' :
      s.irsd_decile <= 6 ? '#D35400' : '#1E8449';

    return `
      <div class="seifa-card">
        <p class="text-sm font-semibold text-gray-700 mb-1">${school.short_name}</p>
        <p class="text-xs text-gray-400">${s.suburb}</p>
        <div class="seifa-score mt-2">${s.irsd_score}</div>
        <p class="text-xs text-gray-400 mt-0.5">IRSD Score</p>
        <div class="mt-3">
          <div class="flex justify-between text-xs text-gray-500 mb-1">
            <span>Decile ${s.irsd_decile.toFixed(1)} / 10</span>
          </div>
          <div class="decile-bar-track">
            <div class="decile-bar-fill" style="width:${decilePct}%;background:${decileColor}"></div>
          </div>
        </div>
        <p class="text-xs mt-2 font-medium" style="color:${decileColor}">
          ${s.disadvantage_level}
        </p>
        ${s.implication ? `<p class="text-xs text-gray-400 mt-1 italic">${s.implication}</p>` : ''}
      </div>`;
  }).join('');
}

function buildExtraCharts(charts) {
  const pairs = [
    { id: 'equity-chart',       file: charts.equity,       caption: 'Equity analysis: SEIFA disadvantage × Healthy Streets scores (Pearson r = 0.84)' },
    { id: 'crash-chart',        file: charts.crash_trends,  caption: 'Ped/cyc crash trends 2021–2025 — Darebin LGA year trend, school-hours breakdown, time-of-day' },
    { id: 'demographics-chart', file: charts.demographics,  caption: 'ABS Census 2021 — median income, no-car households, PT mode share, Reservoir & Preston' },
  ];
  pairs.forEach(({ id, file, caption }) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!file) {
      el.innerHTML = `<p class="text-sm text-gray-400 italic">
        Chart not available — run <code>python prepare_data.py</code> to generate.</p>`;
      return;
    }
    el.innerHTML = chartCardHtml(file, caption);
  });
}

// ── LIGHTBOX ──────────────────────────────────────────────────
function initLightbox() {
  const overlay  = document.getElementById('lightbox');
  const closeBtn = document.getElementById('lightbox-close');

  document.querySelectorAll('.chart-card img').forEach(chartImg => {
    const hint = document.createElement('p');
    hint.className = 'chart-hint';
    hint.textContent = 'Click to enlarge';
    const caption = chartImg.closest('.chart-card').querySelector('.chart-caption');
    if (caption) caption.before(hint);
  });

  document.addEventListener('click', e => {
    if (!e.target.matches('.chart-card img')) return;
    const img = e.target;
    if (img.style.display === 'none') return;
    openLightbox(img.src, img.alt);
  });

  closeBtn.addEventListener('click', closeLightbox);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeLightbox(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });
}

function openLightbox(src, alt) {
  const overlay = document.getElementById('lightbox');
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox-img').alt = alt || '';
  overlay.classList.add('is-open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  document.getElementById('lightbox').classList.remove('is-open');
  document.body.style.overflow = '';
}

// ── RECOMMENDATIONS SECTION ───────────────────────────────────
function initRecommendations(schools) {
  const schoolSelect = document.getElementById('filter-school');
  schools.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.short_name;
    opt.textContent = s.short_name;
    schoolSelect.appendChild(opt);
  });

  schoolSelect.addEventListener('change', renderRecs);
  document.getElementById('filter-priority').addEventListener('change', renderRecs);
  document.getElementById('download-csv').addEventListener('click', downloadCsv);

  renderRecs();
}

function getFilteredRecs() {
  const school   = document.getElementById('filter-school').value;
  const priority = document.getElementById('filter-priority').value;
  return allRecs.filter(r =>
    (!school   || r.school   === school) &&
    (!priority || r.priority === priority)
  );
}

function renderRecs() {
  const recs = getFilteredRecs();
  document.getElementById('rec-count').textContent =
    `Showing ${recs.length} of ${allRecs.length} recommendations`;

  document.getElementById('rec-tbody').innerHTML = recs.map(r => `
    <tr>
      <td>${esc(r.school)}</td>
      <td><strong>${esc(r.indicator)}</strong></td>
      <td>${esc(r.hazard)}</td>
      <td>${esc(r.recommendation)}</td>
      <td><span class="${priorityClass(r.priority)}">${esc(r.priority)}</span></td>
      <td>${esc(r.cost)}</td>
      <td>${esc(r.timeframe)}</td>
    </tr>
  `).join('');

  document.getElementById('rec-cards').innerHTML = recs.map(r => `
    <div class="rec-mobile-card">
      <div class="flex items-center gap-2 mb-1">
        <strong>${esc(r.school)}</strong>
        <span class="badge" style="background:#EEF8F9;color:#028090;font-size:0.65rem">
          ${esc(r.indicator)}
        </span>
        <span class="${priorityClass(r.priority)}">${esc(r.priority)}</span>
      </div>
      <dl>
        <dt>Hazard</dt>      <dd>${esc(r.hazard)}</dd>
        <dt>Intervention</dt><dd>${esc(r.recommendation)}</dd>
        <dt>Cost</dt>        <dd>${esc(r.cost)}</dd>
        <dt>Timeframe</dt>   <dd>${esc(r.timeframe)}</dd>
      </dl>
    </div>
  `).join('');
}

function downloadCsv() {
  const recs    = getFilteredRecs();
  const headers = ['School', 'Indicator', 'Hazard', 'Recommendation', 'Priority', 'Cost', 'Timeframe'];
  const rows    = recs.map(r =>
    [r.school, r.indicator, r.hazard, r.recommendation, r.priority, r.cost, r.timeframe]
      .map(csvCell).join(',')
  );
  const csv  = [headers.join(','), ...rows].join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'recommendations.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Helpers ───────────────────────────────────────────────────
function chartCardHtml(file, caption) {
  if (!file) return '';
  return `
    <div class="chart-card">
      <img src="./data/charts/${file}" alt="${esc(caption)}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
      <div style="display:none;padding:1rem;font-size:0.8rem;color:#999">
        Chart not found: ${file}
      </div>
      <div class="chart-caption">${esc(caption)}</div>
    </div>`;
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function csvCell(v) {
  const s = String(v ?? '');
  return s.includes(',') || s.includes('"') || s.includes('\n')
    ? `"${s.replace(/"/g, '""')}"`
    : s;
}
