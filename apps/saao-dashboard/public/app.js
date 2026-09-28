/**
 * Project EDEN — Earth Data & Environment Navigator
 */

let currentAdvice = null;
let currentLanguage = 'bn';
let isAudioPlaying = false;
let audioTimer = null;

// Tab Switching
window.switchScreen = function(screenId) {
  document.querySelectorAll('.screen-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));

  const target = document.getElementById(screenId);
  if (target) target.classList.add('active');

  const tab = document.querySelector(`[data-screen="${screenId}"]`);
  if (tab) tab.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });
};

document.querySelectorAll('.nav-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const screenId = btn.getAttribute('data-screen');
    window.switchScreen(screenId);
  });
});

// Update Priority Sliders
window.updateWeights = function() {
  const wWater = document.getElementById('weightWater').value;
  const wIncome = document.getElementById('weightIncome').value;
  const wSoil = document.getElementById('weightSoil').value;

  document.getElementById('valWeightWater').innerText = `${wWater}%`;
  document.getElementById('valWeightIncome').innerText = `${wIncome}%`;
  document.getElementById('valWeightSoil').innerText = `${wSoil}%`;
};

// Run Planner Calculation
window.runPlannerCalculation = async function() {
  const landType = document.getElementById('planLandType').value;
  const wWater = parseFloat(document.getElementById('weightWater').value) / 100;
  const wIncome = parseFloat(document.getElementById('weightIncome').value) / 100;
  const wSoil = parseFloat(document.getElementById('weightSoil').value) / 100;

  try {
    const res = await fetch('/api/v1/advice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        unionId: 'talanda_tanore',
        unionNameBangla: 'তালন্দ ইউনিয়ন',
        upazila: 'Tanore',
        district: 'Rajshahi',
        landType,
        season: '2026-aman',
        farmerPriorities: { water: wWater, income: wIncome, soil: wSoil },
      }),
    });

    const data = await res.json();
    currentAdvice = data;
    renderPlannerResults(data);
    renderComparisonGrid(data);
    renderTimeline(data.options[0]);
    updatePreviewText(data.options[0]);
    window.switchScreen('screen-comparison');
  } catch (err) {
    console.error('Failed to calculate advice:', err);
  }
};

// Render Planner Results in Screen 2
function renderPlannerResults(advice) {
  const container = document.getElementById('plannerResultsContainer');
  if (!container) return;

  container.innerHTML = advice.options.map((opt, idx) => `
    <div class="candidate-card-summary ${idx === 0 ? 'selected' : ''}" onclick="selectCandidateOption('${opt.id}')">
      <div class="candidate-top">
        <h4>${opt.rank}. ${opt.nameBangla}</h4>
        <span class="candidate-score-pill">স্কোর: ${Math.round(opt.totalWeightedScore * 100)}%</span>
      </div>
      <p style="font-size: 12px; color: #64748b; margin-bottom: 6px;">
        আমন ধান কাটা: <strong>${opt.fieldFreeDateBangla}</strong> • রবি ফসল রোপণের আদর্শ সময় নিশ্চিত।
      </p>
      <div style="font-size: 11px; color: #166534;">
        ${opt.approvedActionBangla[0] || ''}
      </div>
    </div>
  `).join('');
}

// Render 6-Dimension Comparison Cards in Screen 3
function renderComparisonGrid(advice) {
  const container = document.getElementById('comparisonCardsGrid');
  if (!container) return;

  const dimNames = {
    water: 'পানির সাশ্রয় (Water)',
    heat: 'তাপমাত্রা সহনশীলতা (Heat)',
    flood: 'প্লাবন নিরাপত্তা (Flood)',
    soil: 'মাটি স্বাস্থ্য (Soil)',
    income: 'নিট মুনাফা (Income)',
    fodder: 'গবাদিপশুর খাদ্য (Fodder)',
  };

  container.innerHTML = advice.options.map(opt => {
    const isRec = opt.rank === 1;
    return `
      <div class="comp-card ${isRec ? 'recommended' : ''}">
        <div class="comp-card-badge">
          ${isRec ? '<span class="badge badge-success">⭐ সর্বোচ্চ সুপারিশকৃত (Rank #1)</span>' : `<span class="badge badge-neutral">বিকল্প #${opt.rank}</span>`}
        </div>
        <h3 class="comp-card-title">${opt.nameBangla}</h3>

        <div class="dimensions-breakdown">
          ${Object.entries(opt.scores).map(([dimId, score]) => {
            const pct = Math.round(score * 100);
            const detail = opt.dimensionDetails[dimId];
            return `
              <div class="dim-item">
                <div class="dim-header">
                  <span>${dimNames[dimId] || dimId}</span>
                  <span>${pct}/১০০</span>
                </div>
                <div class="dim-bar-wrap">
                  <div class="dim-bar-fill ${dimId}" style="width: ${pct}%"></div>
                </div>
                <span class="dim-note">${detail?.summaryBangla || ''}</span>
              </div>
            `;
          }).join('')}
        </div>

        <div class="field-free-indicator">
          <span>আমন ধান কাটার তারিখ:</span>
          <strong>${opt.fieldFreeDateBangla}</strong>
        </div>

        <button class="btn btn-sm ${isRec ? 'btn-primary' : 'btn-secondary'}" style="margin-top: 12px;" onclick="selectCandidateOption('${opt.id}')">
          ${isRec ? 'এই চক্রটি নিশ্চিত করুন' : 'বিস্তারিত দেখুন'}
        </button>
      </div>
    `;
  }).join('');
}

// Render Timeline in Screen 3
function renderTimeline(option) {
  const container = document.getElementById('timelineContainer');
  if (!container || !option) return;

  container.innerHTML = option.timeline.map(slot => `
    <div class="timeline-month-col">
      <div class="month-label">${slot.monthNameBangla}</div>
      <div class="slot-indicator ${slot.status}">
        ${slot.cropName || (slot.status === 'available' ? 'জমি ফাঁকা' : 'ফসল চলছে')}
      </div>
    </div>
  `).join('');
}

// Select an option to update previews
window.selectCandidateOption = function(optionId) {
  if (!currentAdvice) return;
  const opt = currentAdvice.options.find(o => o.id === optionId);
  if (opt) {
    renderTimeline(opt);
    updatePreviewText(opt);
    window.switchScreen('screen-delivery');
  }
};

function updatePreviewText(opt) {
  const previewBox = document.getElementById('previewBanglaText');
  if (!previewBox || !opt) return;

  const waterMetric = opt.dimensionDetails['water']?.metrics;
  const rescueCount = waterMetric?.amanRescueIrrigationSeasons ?? 6;
  const rabiMm = waterMetric?.rabiNetIrrigationMm ?? 198;

  previewBox.innerText = `EDEN থেকে বলছি। ${currentAdvice?.scope?.union_name_bangla || 'তালন্দ ইউনিয়ন'}র মাঝারি উঁচু জমির জন্য আপনার অনুমোদিত ফসল চক্র: ${opt.nameBangla}। আমন ধান লাগালে ২৫ মৌসুমে মাত্র ${rescueCount} বার বাড়তি সেচের প্রয়োজন হয়েছিল। ${opt.fieldFreeDateBangla}র মধ্যে ধান কেটে ফেললে রবি ফসল চাষে মাত্র ${rabiMm} মিলিমিটার সেচের প্রয়োজন হবে এবং খরার ঝুঁকি এড়ানো যাবে। ধন্যবাদ।`;
}

// Audio Player Simulation
window.toggleAudioPreview = function() {
  const progress = document.getElementById('audioProgress');
  const btnText = document.getElementById('audioPlayText');
  const btnIcon = document.getElementById('audioPlayIcon');

  if (isAudioPlaying) {
    clearInterval(audioTimer);
    isAudioPlaying = false;
    btnText.innerText = 'বাংলা ভয়েস শুনুন (Audio Preview)';
    btnIcon.innerText = '▶';
    progress.style.width = '0%';
    return;
  }

  isAudioPlaying = true;
  btnText.innerText = 'ভয়েস প্লে হচ্ছে...';
  btnIcon.innerText = '⏸';

  let current = 0;
  audioTimer = setInterval(() => {
    current += 2.5;
    progress.style.width = `${current}%`;
    if (current >= 100) {
      clearInterval(audioTimer);
      isAudioPlaying = false;
      btnText.innerText = 'পুনরায় শুনুন (Replay)';
      btnIcon.innerText = '▶';
      progress.style.width = '100%';
    }
  }, 100);
};

// Dispatch Advice Call
window.dispatchAdviceCall = function() {
  const logBox = document.getElementById('liveCallLog');
  logBox.innerHTML = `
    <span class="log-line">[${new Date().toLocaleTimeString()}] আউটগোয়িং IVR কল শুরু হচ্ছে: 01712-XXXXXX</span>
    <span class="log-line">[${new Date().toLocaleTimeString()}] টেলকো গেটওয়ে: কল রিং হচ্ছে...</span>
    <span class="log-line">[${new Date().toLocaleTimeString()}] কৃষক কল রিসিভ করেছেন (Answered)</span>
    <span class="log-line">[${new Date().toLocaleTimeString()}] অনুমোদিত বাংলা ভয়েস অডিও বাজানো হচ্ছে...</span>
  `;
};

// Simulate Farmer Keypad Interaction
window.simulateFarmerKeypad = async function(key) {
  const logBox = document.getElementById('liveCallLog');
  logBox.innerHTML += `<span class="log-line" style="color: #4ade80;">[${new Date().toLocaleTimeString()}] কৃষকের কিপ্যাড ইনপুট: [ বোতাম ${key} ]</span>`;

  try {
    const res = await fetch('/api/v1/channel-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keypad: key, phone: '01712-XXXXXX' }),
    });
    const data = await res.json();
    logBox.innerHTML += `<span class="log-line">[${new Date().toLocaleTimeString()}] সিস্টেম অ্যাকশন: ${data.acknowledgementBangla}</span>`;
  } catch (err) {
    console.error('Keypad simulation error:', err);
  }
};

// Load Data Quality Table in Screen 8
async function loadDataQualityTable() {
  const tbody = document.getElementById('qualityTableBody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/v1/data-release');
    const data = await res.json();

    tbody.innerHTML = data.datasets.map(d => `
      <tr>
        <td><strong>${d.name}</strong><br><span style="font-size: 11px; color: #64748b;">${d.parameter}</span></td>
        <td>${d.timePeriod}<br><span style="font-size: 11px; color: #0284c7;">${d.spatialResolution}</span></td>
        <td><span class="tag tag-green">${d.freshness}</span><br><span style="font-size: 11px;">ল্যাটেন্সি: ${d.latency}</span></td>
        <td><span style="font-size: 12px; color: #166534;">${d.groundCorrection}</span></td>
        <td><span class="badge badge-success">সক্রিয়</span></td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load data quality:', err);
  }
}

// Initial Load
document.addEventListener('DOMContentLoaded', async () => {
  // Load initial advice
  await window.runPlannerCalculation();
  await loadDataQualityTable();
});
