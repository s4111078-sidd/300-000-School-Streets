/* ── 300,000 Streets — Dashboard app ──────────────────────── */

const HS_NAMES = {
  HS1: 'Pedestrians',
  HS2: 'Easy to cross',
  HS3: 'Shade and shelter',
  HS4: 'Rest places',
  HS5: 'Not too noisy',
  HS6: 'Active travel',
  HS7: 'Feel safe',
  HS8: 'Things to do',
  HS9: 'Feel relaxed',
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
    initMap(data.schools);
    initSchools(data.schools);
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

// ── MAP ────────────────────────────────────────────────────────
function initMap(schools) {
  const map = L.map('map').setView([-37.72, 145.01], 13);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  schools.forEach((school, idx) => {
    const color =
      school.severity === 'Major'    ? '#C0392B' :
      school.severity === 'Moderate' ? '#D35400' : '#1E8449';

    const isPulsing = school.severity === 'Major';

    const icon = L.divIcon({
      className: '',
      html: isPulsing
        ? `<div class="pulse-marker"></div>`
        : `<div style="width:16px;height:16px;border-radius:50%;
               background:${color};border:2px solid #fff;
               box-shadow:0 1px 4px rgba(0,0,0,0.3)"></div>`,
      iconSize: isPulsing ? [18, 18] : [16, 16],
      iconAnchor: isPulsing ? [9, 9] : [8, 8],
    });

    const badgeHtml = `<span class="${severityClass(school.severity)}">${school.severity}</span>`;

    const popup = L.popup({ maxWidth: 220 }).setContent(`
      <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px">
        <div class="map-popup-title">${school.name}</div>
        <div style="margin:4px 0">
          <span class="map-popup-score">${school.overall_score}</span>
          <span style="color:#888;font-size:11px"> / 10</span>
        </div>
        ${badgeHtml}
        <br>
        <button class="map-popup-btn" onclick="goToSchool(${idx})">
          View School Details
        </button>
      </div>
    `);

    L.marker([school.lat, school.lng], { icon })
      .addTo(map)
      .bindPopup(popup);
  });
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
          grid:  { color: '#EEEEEE' },
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

// ── ANALYSIS SECTION ──────────────────────────────────────────
function initAnalysis(data) {
  buildHsCharts(data.charts);
  buildMlChart(data.ml_results);
  buildMlChartImages(data.charts);
  buildSeifaCards(data.schools);
  initLightbox();
}

function buildHsCharts(charts) {
  const el = document.getElementById('hs-charts');
  const items = [
    { file: charts.chart1, caption: charts.chart1_caption },
    { file: charts.chart2, caption: charts.chart2_caption },
    { file: charts.chart3, caption: charts.chart3_caption },
  ];
  el.innerHTML = items.map(item => `
    <div class="chart-card">
      <img src="./data/charts/${item.file}" alt="${item.caption}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
      <div style="display:none;padding:1rem;font-size:0.8rem;color:#999">
        Chart not found: ${item.file}
      </div>
      <div class="chart-caption">${item.caption}</div>
    </div>
  `).join('');
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
          callbacks: {
            label: ctx => ` MAE: ${ctx.raw.toFixed(3)}`,
          },
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
    { file: charts.feature_importance, caption: 'Ridge regression coefficients — top predictors per indicator' },
  ];
  el.innerHTML = items.map(item => `
    <div class="chart-card">
      <img src="./data/charts/${item.file}" alt="${item.caption}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
      <div style="display:none;padding:1rem;font-size:0.8rem;color:#999">
        Chart not found: ${item.file}
      </div>
      <div class="chart-caption">${item.caption}</div>
    </div>
  `).join('');
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

    const decilePct = Math.min((s.irsd_decile / 10) * 100, 100).toFixed(0);
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

// ── LIGHTBOX ──────────────────────────────────────────────────
function initLightbox() {
  const overlay  = document.getElementById('lightbox');
  const closeBtn = document.getElementById('lightbox-close');

  // Inject hint text — images are in the DOM at this point because
  // initLightbox() is called at the end of initAnalysis().
  document.querySelectorAll('.chart-card img').forEach(chartImg => {
    const hint = document.createElement('p');
    hint.className = 'chart-hint';
    hint.textContent = '🔍 Click to enlarge';
    const caption = chartImg.closest('.chart-card').querySelector('.chart-caption');
    if (caption) caption.before(hint);
  });

  // Event delegation — one listener on document covers all chart images.
  document.addEventListener('click', e => {
    if (!e.target.matches('.chart-card img')) return;
    const img = e.target;
    if (img.style.display === 'none') return;
    openLightbox(img.src, img.alt);
  });

  // Close on button click
  closeBtn.addEventListener('click', closeLightbox);

  // Close on backdrop click (the overlay div itself, not the enlarged image)
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeLightbox();
  });

  // Close on Escape key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeLightbox();
  });
}

function openLightbox(src, alt) {
  const overlay = document.getElementById('lightbox');
  const img     = document.getElementById('lightbox-img');
  img.src = src;
  img.alt = alt || '';
  overlay.classList.add('is-open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  const overlay = document.getElementById('lightbox');
  overlay.classList.remove('is-open');
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

  const tbody = document.getElementById('rec-tbody');
  tbody.innerHTML = recs.map(r => `
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

  const cards = document.getElementById('rec-cards');
  cards.innerHTML = recs.map(r => `
    <div class="rec-mobile-card">
      <div class="flex items-center gap-2 mb-1">
        <strong>${esc(r.school)}</strong>
        <span class="badge" style="background:#EEF8F9;color:#028090;font-size:0.65rem">
          ${esc(r.indicator)}
        </span>
        <span class="${priorityClass(r.priority)}">${esc(r.priority)}</span>
      </div>
      <dl>
        <dt>Hazard</dt>
        <dd>${esc(r.hazard)}</dd>
        <dt>Intervention</dt>
        <dd>${esc(r.recommendation)}</dd>
        <dt>Cost</dt>
        <dd>${esc(r.cost)}</dd>
        <dt>Timeframe</dt>
        <dd>${esc(r.timeframe)}</dd>
      </dl>
    </div>
  `).join('');
}

function downloadCsv() {
  const recs = getFilteredRecs();
  const headers = ['School', 'Indicator', 'Hazard', 'Recommendation', 'Priority', 'Cost', 'Timeframe'];
  const rows = recs.map(r => [
    r.school, r.indicator, r.hazard, r.recommendation,
    r.priority, r.cost, r.timeframe,
  ].map(csvCell).join(','));

  const csv = [headers.join(','), ...rows].join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'recommendations.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Helpers ───────────────────────────────────────────────────
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
