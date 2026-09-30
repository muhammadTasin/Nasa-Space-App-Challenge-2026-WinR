/**
 * Project EDEN — Earth Data & Environment Navigator (SAAO dashboard)
 *
 * Every number comes from the API, which reads the generated research release.
 * Language: static text carries data-i18n (Bangla in index.html, English in i18n.js); dynamic text is built
 * here with tr(bangla, english). Switching language re-renders everything from the cached API responses.
 */
import { EN } from './i18n.js';

let lang = 'bn';
let currentAdvice = null;
let currentOverview = null;
let currentNarration = null;
let currentDataRelease = null;
let selectedOptionId = null;
let officers = [];
let officerSession = null; // { token, officer }
let officerDesk = null;
let officerKnowledge = null;
let officerNotice = null; // result of the last saved observation
let audioState = 'idle'; // idle | playing | done | novoice
let audioTimer = null;

const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
const BN_MONTHS = ['জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'];
const EN_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const tr = (bn, en) => (lang === 'en' ? en : bn);
const bnDigits = (value) => String(value).replace(/\d/g, d => BN_DIGITS[Number(d)]);
// Digits in the current language; a leading minus becomes '−' but ranges like 2003-07 keep their hyphen
const num = (value) => (lang === 'en' ? String(value) : bnDigits(value)).replace(/(^|[\s(:])-(?=[0-9০-৯])/g, '$1−');
const bigNum = (value) => Math.round(value).toLocaleString(lang === 'en' ? 'en-US' : 'bn-BD');
const isoDate = (iso) => {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return lang === 'en' ? `${d} ${EN_MONTHS[m - 1]} ${y}` : `${bnDigits(d)} ${BN_MONTHS[m - 1]} ${bnDigits(y)}`;
};
const bnDateOf = (text) => (text.endsWith('ি') || text.endsWith('ে') ? `${text}র` : text.endsWith('ই') ? `${text}য়ের` : `${text}ের`);
const escapeHtml = (text) => String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (id) => document.getElementById(id);
const setText = (id, text) => {
  const el = $(id);
  if (el) el.textContent = text;
};
const setHtml = (id, html) => {
  const el = $(id);
  if (el) el.innerHTML = html;
};

const LAND = {
  high: ['উঁচু জমি', 'High land'],
  medium_high: ['মাঝারি উঁচু জমি', 'Medium-high land'],
  medium_low: ['মাঝারি নিচু জমি', 'Medium-low land'],
  low: ['নিচু জমি', 'Low land'],
  very_low: ['খুব নিচু জমি', 'Very low land'],
};
const AMAN = {
  'BRRI dhan71': 'ব্রি ধান৭১',
  'BRRI dhan87': 'ব্রি ধান৮৭',
  'BRRI dhan103': 'ব্রি ধান১০৩',
  'BRRI dhan49': 'ব্রি ধান৪৯',
  'BRRI dhan75': 'ব্রি ধান৭৫',
};
const land = (key) => tr(...(LAND[key] || [key, key]));
const amanName = (variety) => tr(AMAN[variety] || variety, variety);

// ---------------------------------------------------------------------------
// Language
// ---------------------------------------------------------------------------

function applyStaticText() {
  document.documentElement.lang = lang;
  document.title = tr('Project EDEN — Earth Data & Environment Navigator · ফসল চক্র সিদ্ধান্ত সহায়ক সেবা', 'Project EDEN — Earth Data & Environment Navigator · crop rotation decision support');
  document.querySelectorAll('[data-i18n]').forEach(el => {
    if (el.dataset.bn === undefined) el.dataset.bn = el.innerHTML;
    const english = EN[el.dataset.i18n];
    el.innerHTML = lang === 'en' && english !== undefined ? english : el.dataset.bn;
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    if (el.dataset.bnTitle === undefined) el.dataset.bnTitle = el.title;
    const english = EN[el.dataset.i18nTitle];
    el.title = lang === 'en' && english !== undefined ? english : el.dataset.bnTitle;
  });
  document.querySelectorAll('[data-num]').forEach(el => {
    el.textContent = num(el.dataset.num);
  });
  $('langBn').classList.toggle('active', lang === 'bn');
  $('langEn').classList.toggle('active', lang === 'en');
}

window.setLanguage = function(next) {
  lang = next === 'en' ? 'en' : 'bn';
  try {
    localStorage.setItem('eden.lang', lang);
  } catch {
    // storage blocked: the choice lasts for this page only
  }
  applyStaticText();
  renderAll();
};

function renderAll() {
  if (currentOverview) renderOverview(currentOverview);
  if (currentAdvice) {
    renderPlannerResults(currentAdvice);
    renderComparisonGrid(currentAdvice);
    renderTimeline(selectedOption());
    renderEvidence(currentAdvice);
    renderCompanion(currentAdvice);
    renderIpm(currentAdvice);
  }
  renderNarration();
  if (currentDataRelease) renderQuality(currentDataRelease);
  renderProfile();
  renderOfficer();
  renderAudioButton();
  window.updateWeights();
  window.updateObsWeights();
}

// ---------------------------------------------------------------------------
// Navigation and sliders
// ---------------------------------------------------------------------------

window.switchScreen = function(screenId) {
  document.querySelectorAll('.screen-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
  $(screenId)?.classList.add('active');
  document.querySelector(`[data-screen="${screenId}"]`)?.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

document.querySelectorAll('.nav-tab').forEach(btn => {
  btn.addEventListener('click', () => window.switchScreen(btn.getAttribute('data-screen')));
});

window.updateWeights = function() {
  for (const [slider, label] of [['weightWater', 'valWeightWater'], ['weightIncome', 'valWeightIncome'], ['weightSoil', 'valWeightSoil'], ['weightPest', 'valWeightPest']]) {
    setText(label, `${num($(slider).value)}%`);
  }
};

window.updateObsWeights = function() {
  for (const [slider, label] of [['obsWater', 'valObsWater'], ['obsIncome', 'valObsIncome'], ['obsSoil', 'valObsSoil'], ['obsPestPriority', 'valObsPest']]) {
    setText(label, `${num($(slider).value)}%`);
  }
};

// ---------------------------------------------------------------------------
// SCREEN 1: overview (dated research values, sample farmer rows, field pest reports)
// ---------------------------------------------------------------------------

async function loadOverview() {
  const res = await fetch('/api/v1/overview');
  currentOverview = await res.json();
  renderOverview(currentOverview);
}

function renderOverview(o) {
  setText('releaseTag', `${tr('রিলিজ', 'Release')}: ${o.data_release.version}`);

  const rain = o.local_satellite_conditions.rain_last_30_days;
  const pct = rain.pctOfNormal;
  setText('statRainValue', `${num(Math.round(rain.imergLateMm))} ${tr('মিমি', 'mm')}`);
  setText('statRainSub', tr(
    `${rain.verdictBangla}: স্বাভাবিকের ${num(pct.imergLate)}% (IMERG Late), ${num(pct.imergAdjusted)}% (সমন্বিত), ${num(pct.merra2)}% (MERRA-2); ${isoDate(rain.to)} পর্যন্ত`,
    `${rain.verdict.charAt(0).toUpperCase()}${rain.verdict.slice(1)}: ${pct.imergLate}% of normal (IMERG Late), ${pct.imergAdjusted}% (corrected), ${pct.merra2}% (MERRA-2); to ${isoDate(rain.to)}`,
  ));

  const smap = o.local_satellite_conditions.smap;
  if (smap) {
    setText('statSmapValue', `${num(smap.rootZoneM3M3.toFixed(2))} m³/m³`);
    const past = smap.sameDatePastYears.map(p => tr(`${num(p.year)} সালে ${num(p.rootZoneM3M3.toFixed(2))}`, `${p.year}: ${p.rootZoneM3M3.toFixed(2)}`)).join(', ');
    setText('statSmapSub', `${isoDate(smap.date)}; ${tr('একই সময়ে', 'same time in')} ${past}`);
    setText('dataDateBadge', `${tr('সর্বশেষ ডেটা', 'Latest data')}: ${isoDate(smap.date)}`);
  }

  setText('statVarietyValue', tr(o.recommended.amanVarietyBangla, o.recommended.amanVariety));
  setText('statVarietySub', tr(`${bnDateOf(o.recommended.fieldFreeDateBangla)} মধ্যে জমি খালি`, `Field free by ${o.recommended.fieldFreeDateEnglish}`));

  setText('mapPinLabel', `${tr('তানোর পাইলট পয়েন্ট', 'Tanore pilot point')} (${num(o.scope.lat)}° N, ${num(o.scope.lon)}° E)`);
  setText('specSoil', tr(`${o.context.soilTypeBangla}, ${o.context.landTypeBangla}`, `${o.context.soilTypeEnglish}, ${o.context.landTypeEnglish}`));
  const gw = o.context.groundwater;
  setText('specGroundwater', tr(
    `বছরে ${num(gw.trendMmPerYear)} মিমি (${num(gw.period.replace(' to ', ' থেকে '))}: ${num(gw.changeMm)} মিমি)`,
    `${gw.trendMmPerYear} mm a year (${gw.changeMm} mm, ${gw.period})`,
  ));
  const green = o.context.winterGreenness;
  setText('specGreenness', `NDVI ${num(green.early.peakNdvi)} → ${num(green.recent.peakNdvi)}; ${tr('বছরে ফসল', 'crops a year')} ${num(green.early.cyclesPerYear)} → ${num(green.recent.cyclesPerYear)}`);
  setText('specBmd', tr(
    `${o.context.bmdStationBangla} (${num(o.context.bmdStationKm)} কিমি দূরে)`,
    `Shah Mokhdum, Rajshahi (41895), ${o.context.bmdStationKm} km away`,
  ));

  const alert = o.active_alerts[0];
  if (alert) {
    setText('alertTitle', `${tr('সতর্কতা', 'Alert')}: ${tr(alert.titleBangla, alert.titleEnglish)}`);
    setText('alertText', tr(alert.textBangla, alert.textEnglish));
    setText('alertSolution', tr(alert.recommendationBangla, alert.recommendationEnglish));
  }

  const status = {
    callback: ['badge-warning', 'কল-ব্যাক অনুরোধ', 'Call-back requested'],
    verified: ['badge-success', 'কর্মকর্তা যাচাইকৃত', 'Officer-verified'],
    pending: ['badge-neutral', 'মাঠ যাচাই বাকি', 'Field check pending'],
  };
  setHtml('recentFarmersTable', o.recent_farmer_contacts.map(f => {
    const [cls, bn, en] = status[f.status] || status.pending;
    return `
    <tr>
      <td><strong>${escapeHtml(tr(f.name, f.nameEnglish))}</strong> <span class="tag tag-yellow">${tr('নমুনা', 'sample')}</span></td>
      <td>${escapeHtml(tr(f.village, f.villageEnglish))} (${escapeHtml(land(f.landType))})</td>
      <td>${f.nextSeasonRotation ? `<small>${tr('এ মৌসুম', 'This season')}:</small> ` : ''}<span class="tag tag-green">${escapeHtml(tr(f.rotation, f.rotationEnglish))}</span>${f.nextSeasonRotation ? `<br><small>${tr('আগামী মৌসুম', 'Next season')}: ${escapeHtml(tr(f.nextSeasonRotation, f.nextSeasonRotationEnglish))}</small>` : ''}</td>
      <td><span class="badge ${cls}">${tr(bn, en)}</span></td>
      <td><button class="btn btn-sm" onclick="switchScreen('screen-officer')">${tr('কর্মকর্তা ডেস্ক', 'Officer desk')}</button></td>
    </tr>`;
  }).join(''));

  const reports = pestReportsHtml(o.pest_reports || []);
  setHtml('overviewPestReports', reports);
  setHtml('ipmField', reports);
  setText('policyRelease', o.data_release.version);
  if (o.early_warnings) renderWarnings(o.early_warnings, o.aman_replay);
}

// "3 of 5" -> "৫টির ৩টি" in Bangla, unchanged in English
const ofText = (s) => {
  const m = /^(\d+) of (\d+)$/.exec(s || '');
  return m ? tr(`${num(m[2])}টির ${num(m[1])}টি`, s) : s;
};
const monthName = (m) => tr(BN_MONTHS[m - 1], EN_MONTHS[m - 1]);

function haorChartSvg(h) {
  const W = 560, H = 190, L = 34, R = 8, T = 12, B = 26, max = 400;
  const bw = (W - L - R) / h.seasons.length;
  const y = (v) => T + (H - T - B) * (1 - Math.min(v, max) / max);
  const fill = (s) => (s.label === 'flood' ? '#d97706' : s.label === 'no flood' ? '#0284c7' : '#94a3b8');
  const bars = h.seasons.map((s, i) => `<rect x="${(L + i * bw + 2).toFixed(1)}" y="${y(s.sohraMax3Mm).toFixed(1)}" width="${(bw - 4).toFixed(1)}" height="${(H - B - y(s.sohraMax3Mm)).toFixed(1)}" rx="2" fill="${fill(s)}"><title>${s.year}: ${s.sohraMax3Mm} mm</title></rect>`).join('');
  const rule = (v, dash, label) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#b91c1c" stroke-width="1.5" stroke-dasharray="${dash}"/><text x="${W - R}" y="${y(v) - 4}" text-anchor="end" font-size="11" fill="#b91c1c">${label}</text>`;
  const years = h.seasons.map((s, i) => (s.year % 4 === 1 ? `<text x="${(L + i * bw + bw / 2).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#64748b">${num(s.year)}</text>` : '')).join('');
  const axis = [0, 100, 200, 300, 400].map(v => `<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="#94a3b8">${num(v)}</text>`).join('');
  const label = tr('সোহরায় বসন্তের সর্বোচ্চ ৩ দিনের বৃষ্টি, ২০০১–২০২৫', 'Largest 3-day spring rain at Sohra, 2001–2025');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" aria-label="${label}">${axis}${bars}${rule(h.watchMm, '5 4', tr(`সতর্কতা ${num(h.watchMm)} মিমি`, `watch ${h.watchMm} mm`))}${rule(h.warningMm, '2 3', tr(`বিপদ ${num(h.warningMm)} মিমি`, `warning ${h.warningMm} mm`))}${years}</svg>`;
}

function cattleChartSvg(c) {
  const W = 560, H = 150, L = 34, R = 8, T = 10, B = 24;
  const bw = (W - L - R) / 12;
  const y = (v) => T + (H - T - B) * (1 - v);
  const bars = c.months.map((m, i) => `<rect x="${(L + i * bw + 3).toFixed(1)}" y="${y(m.dangerShare).toFixed(1)}" width="${(bw - 6).toFixed(1)}" height="${(H - B - y(m.dangerShare)).toFixed(1)}" rx="2" fill="${c.noReliefMonths.includes(m.month) ? '#b91c1c' : '#f59e0b'}"><title>${EN_MONTHS[m.month - 1]}: ${Math.round(m.dangerShare * 100)}%</title></rect>`).join('');
  const months = c.months.map((m, i) => `<text x="${(L + i * bw + bw / 2).toFixed(1)}" y="${H - 7}" text-anchor="middle" font-size="10" fill="#64748b">${escapeHtml(monthName(m.month).slice(0, lang === 'en' ? 3 : 4))}</text>`).join('');
  const axis = [0, 0.5, 1].map(v => `<text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="#94a3b8">${num(Math.round(v * 100))}%</text>`).join('');
  const label = tr('মাসভিত্তিক বিপদসীমার ঘণ্টা', 'Share of hours in the danger bands, by month');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" aria-label="${label}">${axis}${bars}${months}</svg>`;
}

function renderWarnings(w, amanReplay) {
  const h = w.haor;
  const badge = $('haorStatus');
  if (h.status.state === 'in_season') {
    badge.className = 'badge badge-warning';
    badge.textContent = tr('মৌসুম চলছে: নজরদারি', 'In season: monitoring');
  } else {
    badge.className = 'badge badge-neutral';
    badge.textContent = tr(`মৌসুম শুরু ${isoDate(h.status.nextStart)}`, `Season opens ${isoDate(h.status.nextStart)}`);
  }
  setText('haorRule', tr(
    `১৫ মার্চ–১৫ মে: মেঘালয়ের সোহরায় (চেরাপুঞ্জি) ৩ দিনে ${num(h.watchMm)} মিমি বৃষ্টি হলে সতর্কতা, ${num(h.warningMm)} মিমি হলে বিপদবার্তা। সেই পানি ১–৩ দিনে সুনামগঞ্জের হাওরে নামে।`,
    `15 Mar–15 May: ${h.watchMm} mm of rain in 3 days at Sohra (Cherrapunji, Meghalaya) raises a watch, ${h.warningMm} mm a warning. That water reaches the Sunamganj haors in 1–3 days.`,
  ));
  setHtml('haorChart', haorChartSvg(h));
  setText('haorLegend', tr('কমলা: বন্যার বছর (FFWC) • নীল: বন্যাহীন বছর • ধূসর: রিপোর্ট নেই', 'Orange: flood years (FFWC) • Blue: no-flood years • Grey: no report'));
  const watch = h.skill.find(s => s.thresholdMm === h.watchMm);
  const dhan28 = h.escapeOnCalendar.find(e => e.variety === 'BRRI dhan28');
  const others = h.escapeOnCalendar.filter(e => e.variety !== 'BRRI dhan28');
  const othersEarly = h.escapeTwoWeeksEarly.filter(e => e.variety !== 'BRRI dhan28');
  const worstOther = Math.max(...others.map(e => e.burstsBeforeHarvest));
  const worstEarly = Math.max(...othersEarly.map(e => e.burstsBeforeHarvest));
  setHtml('haorFacts', [
    watch ? tr(
      `<li><strong>২৫ বছরের পরীক্ষা:</strong> ${num(h.watchMm)} মিমি নিয়মে বন্যার বছর ধরা পড়ে ${ofText(watch.floodYearsCaught)}, বন্যাহীন বছরে ভুল সংকেত ${ofText(watch.noFloodYearsFlagged)}; সংকেত ${ofText(watch.seasonsFlagged)} মৌসুমে।</li>`,
      `<li><strong>25-year hindcast:</strong> the ${h.watchMm} mm rule catches ${watch.floodYearsCaught} flood years, with false alarms in ${watch.noFloodYearsFlagged} no-flood years; it flags ${watch.seasonsFlagged} springs.</li>`,
    ) : '',
    dhan28 ? tr(
      `<li><strong>কোন বোরো বাঁচে:</strong> ${num(h.warningMm)} মিমির ঢলে ব্রি ধান২৮ পাকার আগে ধরা পড়েছে ${num(dhan28.bursts)}টির ${num(dhan28.burstsBeforeHarvest)}টিতে; অন্য ${num(others.length)}টি জাত (${others.map(e => num(e.variety.replace('BRRI dhan', ''))).join(', ')}) সর্বোচ্চ ${num(worstOther)}টিতে; দুই সপ্তাহ আগে বুনলে ${num(worstEarly)}টিতে।</li>`,
      `<li><strong>Which Boro escapes:</strong> ${h.warningMm} mm bursts caught BRRI dhan28 before harvest in ${dhan28.burstsBeforeHarvest} of ${dhan28.bursts}; the other ${others.length} varieties (BRRI dhan${others.map(e => e.variety.replace('BRRI dhan', '')).join(', ')}) in at most ${worstOther}; sown two weeks early, ${worstEarly}.</li>`,
    ) : '',
    tr('<li>হাওরের ফসল চক্র এখনো মডেল করা হয়নি; এটি আগাম সতর্কতা ব্যবস্থা।</li>', '<li>Rotation advice is not modelled for the haor yet; this is the early-warning system.</li>'),
  ].join(''));

  const n = w.warmNights;
  const flower = (variety) => amanReplay?.find(r => r.variety === variety);
  const f71 = flower('BRRI dhan71');
  const f49 = flower('BRRI dhan49');
  const sig = (t) => (t.kendallP < 0.05 ? tr('তাৎপর্যপূর্ণ', 'significant') : tr(`স্পষ্ট নয় (p ${num(t.kendallP.toFixed(2))})`, `not clear (p ${t.kendallP.toFixed(2)})`));
  setHtml('nightFacts', [
    tr(
      `<li><strong>ব্রি ধান৭১</strong> (ফুল ~${f71?.floweringBangla ?? ''}): রাতের গড় ${num(n.dhan71.mean1991to2005.toFixed(1))}°C (১৯৯১–২০০৫) থেকে ${num(n.dhan71.mean2011to2025.toFixed(1))}°C (২০১১–২০২৫); প্রতি দশকে +${num(n.dhan71.trendPerDecade)}°C, ${sig(n.dhan71)}।</li>`,
      `<li><strong>BRRI dhan71</strong> (flowers ~${f71?.floweringEnglish ?? ''}): nights averaged ${n.dhan71.mean1991to2005.toFixed(1)}°C in 1991–2005 and ${n.dhan71.mean2011to2025.toFixed(1)}°C in 2011–2025; +${n.dhan71.trendPerDecade}°C a decade, ${sig(n.dhan71)}.</li>`,
    ),
    tr(
      `<li><strong>ব্রি ধান৪৯</strong> (ফুল ~${f49?.floweringBangla ?? ''}): প্রতি দশকে +${num(n.dhan49.trendPerDecade)}°C, ${sig(n.dhan49)}।</li>`,
      `<li><strong>BRRI dhan49</strong> (flowers ~${f49?.floweringEnglish ?? ''}): +${n.dhan49.trendPerDecade}°C a decade, ${sig(n.dhan49)}.</li>`,
    ),
    tr(
      `<li><strong>সুখবর:</strong> ২০ নভেম্বরে বোনা গমে দানা পুষ্টের গরম দিন প্রতি দশকে ${num(Math.abs(n.wheat20Nov.trendPerDecade).toFixed(1))}টি কমেছে (${sig(n.wheat20Nov)})।</li>`,
      `<li><strong>Good news:</strong> hot days at grain filling for wheat sown on 20 Nov fell by ${Math.abs(n.wheat20Nov.trendPerDecade).toFixed(1)} a decade (${sig(n.wheat20Nov)}).</li>`,
    ),
    tr('<li>আগাম আমন পানি ও সময় বাঁচায়, কিন্তু উষ্ণ রাতে ফুল আসে; কর্মকর্তারা চিটা ও ফলন নজরে রাখবেন।</li>', '<li>Early Aman saves water and time but flowers into warmer nights; officers should watch for empty grains and yield.</li>'),
  ].join(''));

  const c = w.cattleHeat;
  const noRelief = c.noReliefMonths.map(monthName);
  const peak = Math.round(c.peakDangerShare * 100);
  const cattleBadge = $('cattleBadge');
  cattleBadge.textContent = tr(`${num(c.noReliefMonths.length)} মাস রাতেও স্বস্তি নেই`, `${c.noReliefMonths.length} months without night relief`);
  setText('cattleLead', tr(
    `${noRelief[0]}–${noRelief[noRelief.length - 1]}: রাতেও তাপ-আর্দ্রতা সূচক (THI) ৭২-এর নিচে নামে না; ${monthName(c.peakMonth)}-এ ${num(peak)}% ঘণ্টা বিপদসীমায়।`,
    `${noRelief[0]}–${noRelief[noRelief.length - 1]}: the temperature-humidity index (THI) stays above 72 even at night; in ${monthName(c.peakMonth)} ${peak}% of hours are in the danger bands.`,
  ));
  setHtml('cattleChart', cattleChartSvg(c));
  const [first, , , last] = c.coolestHours;
  setHtml('cattleFacts', [
    tr(
      `<li>দিনের সবচেয়ে ঠান্ডা সময় রাত ${num(first)}–${num(last)}: খাওয়ানো ও ভারী কাজ ভোরের দিকে রাখুন, ছায়া ও পানি দিন।</li>`,
      `<li>The coolest hours are ${first}–${last}: keep feeding and heavy work near dawn; give shade and water.</li>`,
    ),
    tr('<li>উৎস: নাসা POWER ঘণ্টাভিত্তিক তাপমাত্রা ও আর্দ্রতা (২০২৩–২০২৫), THI (NRC ১৯৭১)।</li>', '<li>Source: NASA POWER hourly temperature and humidity (2023–2025), THI (NRC 1971).</li>'),
  ].join(''));
}

function renderLedger(advice) {
  const rows = advice.options.filter(o => o.ledger);
  const yesNo = (v) => (v ? tr('হ্যাঁ', 'yes') : tr('না', 'no'));
  setHtml('ledgerTable', `
    <table class="data-table ledger-table">
      <thead><tr>
        <th>${tr('চক্র', 'Rotation')}</th>
        <th>${tr('ভূগর্ভস্থ পানি তোলা (ঘনমিটার/হেক্টর)', 'Groundwater pumped (m³/ha)')}</th>
        <th>${tr('জলাবদ্ধ ধানের দিন (মিথেন সূচক)', 'Flooded-rice days (methane proxy)')}</th>
        <th>${tr('ইউরিয়া (কেজি/হেক্টর)', 'Urea (kg/ha)')}</th>
        <th>${tr('ডাল ফসল', 'Legume')}</th>
        <th>${tr('খালি জমির দিন', 'Bare days')}</th>
        <th>${tr('বালাই স্কোর', 'Pest score')}</th>
      </tr></thead>
      <tbody>${rows.map(o => `
        <tr class="${o.isBaseline ? 'baseline-row' : o.rank === 1 ? 'top-row' : ''}">
          <td>${escapeHtml(tr(o.nameBangla, o.nameEnglish))}${o.isBaseline ? ` <span class="tag tag-yellow">${tr('প্রচলিত', 'current practice')}</span>` : ''}</td>
          <td>${bigNum(o.ledger.groundwaterPumpedM3PerHa)}</td>
          <td>${num(o.ledger.floodedRiceDays)}</td>
          <td>${num(o.ledger.ureaKgHa)}</td>
          <td>${yesNo(o.ledger.legume)}</td>
          <td>${num(o.ledger.bareDays)}</td>
          <td>${num(Math.round((o.scores.pest ?? 0) * 100))}</td>
        </tr>`).join('')}
      </tbody>
    </table>`);
}

function pestReportsHtml(reports) {
  if (!reports.length) {
    return `<p class="muted">${tr('এখনো কোনো বালাইয়ের খবর নেই। কর্মকর্তা মাঠে বালাই দেখলে এখানে আসবে।', 'No pest reports yet. They appear here when an officer logs a pest in the field.')}</p>`;
  }
  return reports.map(r => `
    <div class="pest-report">
      <span class="pest-name">🐛 ${escapeHtml(tr(r.bn, r.en))}</span>
      <span>${tr(`${num(r.fields)}টি জমি`, `${r.fields} field${r.fields === 1 ? '' : 's'}`)}${r.highSeverity ? ` • <span class="badge badge-danger">${tr(`${num(r.highSeverity)}টিতে বেশি`, `${r.highSeverity} severe`)}</span>` : ''}</span>
    </div>`).join('');
}

// ---------------------------------------------------------------------------
// SCREENS 2-3: planner and comparison, from /api/v1/advice
// ---------------------------------------------------------------------------

window.runPlannerCalculation = async function(options = {}) {
  const weight = (id) => parseFloat($(id).value) / 100;
  try {
    const res = await fetch('/api/v1/advice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        unionId: 'talanda_tanore',
        unionNameBangla: 'তালন্দ ইউনিয়ন',
        upazila: 'Tanore',
        district: 'Rajshahi',
        landType: $('planLandType').value,
        currentAmanCrop: $('planAmanCrop').value,
        season: '2026-aman',
        farmerPriorities: { water: weight('weightWater'), income: weight('weightIncome'), soil: weight('weightSoil'), pest: weight('weightPest') },
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setHtml('plannerResultsContainer', `<p class="officer-error">${escapeHtml(data.error || tr('পরামর্শ তৈরি করা যায়নি', 'Could not build the advice'))}</p>`);
      return;
    }
    currentAdvice = data;
    selectedOptionId = data.options[0].id;
    renderPlannerResults(data);
    renderComparisonGrid(data);
    renderTimeline(selectedOption());
    renderEvidence(data);
    renderCompanion(data);
    renderIpm(data);
    await loadNarration(selectedOption());
    if (options.switchScreenAfter !== false) window.switchScreen('screen-comparison');
  } catch (err) {
    console.error('Failed to calculate advice:', err);
  }
};

function selectedOption() {
  return currentAdvice?.options.find(o => o.id === selectedOptionId) || currentAdvice?.options[0];
}

function renderPlannerResults(advice) {
  setText('plannerCountBadge', tr(`${num(advice.options.length)}টি বিকল্প তৈরি হয়েছে`, `${advice.options.length} options generated`));

  const note = $('thisSeasonNote');
  note.hidden = !advice.this_season;
  note.textContent = advice.this_season ? tr(`এই মৌসুম: ${advice.this_season.noteBangla}`, `This season: ${advice.this_season.noteEnglish}`) : '';

  setHtml('plannerResultsContainer', advice.options.map((opt, idx) => `
    <div class="candidate-card-summary ${idx === 0 ? 'selected' : ''}" onclick="selectCandidateOption('${opt.id}')">
      <div class="candidate-top">
        <h4>${num(opt.rank)}. ${escapeHtml(tr(opt.nameBangla, opt.nameEnglish))}</h4>
        <span class="candidate-score-pill">${tr('স্কোর', 'Score')}: ${num(Math.round(opt.totalWeightedScore * 100))}%</span>
      </div>
      <p class="candidate-meta">
        ${tr('জমি খালি', 'Field free')}: <strong>${escapeHtml(tr(opt.fieldFreeDateBangla, opt.fieldFreeDateEnglish))}</strong>${opt.isBaseline ? ` • ${tr('বর্তমান প্রচলিত চক্র', 'current practice')}` : ''}${opt.id === advice.this_season_option_id ? ` <span class="tag tag-green">${tr('এ মৌসুমে সম্ভব', 'possible this season')}</span>` : ''}
      </p>
      <div class="candidate-action">${escapeHtml(tr(opt.approvedActionBangla[2] || '', (opt.approvedActionEnglish || [])[2] || ''))}</div>
    </div>
  `).join(''));
}

const DIMENSIONS = {
  water: ['পানির সাশ্রয় (Water)', 'Water saving'],
  heat: ['তাপমাত্রা সহনশীলতা (Heat)', 'Heat tolerance'],
  flood: ['প্লাবন নিরাপত্তা (Flood)', 'Flood safety'],
  soil: ['মাটি স্বাস্থ্য (Soil)', 'Soil health'],
  fodder: ['গবাদিপশুর খাদ্য (Fodder)', 'Livestock fodder'],
  income: ['আয় (Income)', 'Income'],
  pest: ['বালাই চাপ ও কীটনাশক (Pest)', 'Pest pressure & pesticide'],
};

function dimensionTag(detail) {
  if (detail?.staleOrMissing) return tr('নমুনা', 'sample');
  if (detail?.provenance?.measuredOrModeled === 'assumed') return tr('অনুমান', 'assumed');
  return '';
}

function renderComparisonGrid(advice) {
  setHtml('comparisonCardsGrid', advice.options.map(opt => {
    const isRec = opt.rank === 1;
    return `
      <div class="comp-card ${isRec ? 'recommended' : ''}">
        <div class="comp-card-badge">
          ${isRec ? `<span class="badge badge-success">${tr('⭐ সর্বোচ্চ সুপারিশকৃত (Rank #১)', '⭐ Top recommendation (rank #1)')}</span>` : `<span class="badge badge-neutral">${tr(`বিকল্প #${num(opt.rank)}`, `Option #${opt.rank}`)}</span>`}
          ${opt.isBaseline ? `<span class="badge badge-warning">${tr('বর্তমান প্রচলিত', 'Current practice')}</span>` : ''}
        </div>
        <h3 class="comp-card-title">${escapeHtml(tr(opt.nameBangla, opt.nameEnglish))}</h3>
        <div class="dimensions-breakdown">
          ${Object.entries(opt.scores).map(([dimId, score]) => {
            const pct = Math.round(score * 100);
            const detail = opt.dimensionDetails[dimId];
            const tag = dimensionTag(detail);
            return `
              <div class="dim-item">
                <div class="dim-header">
                  <span>${tr(...(DIMENSIONS[dimId] || [dimId, dimId]))}${tag ? ` <span class="tag tag-yellow">${tag}</span>` : ''}</span>
                  <span>${num(pct)}/${num(100)}</span>
                </div>
                <div class="dim-bar-wrap"><div class="dim-bar-fill ${dimId}" style="width: ${pct}%"></div></div>
                <span class="dim-note">${escapeHtml(tr(detail?.summaryBangla, detail?.summaryEnglish))}</span>
              </div>`;
          }).join('')}
        </div>
        <div class="field-free-indicator">
          <span>${tr('জমি খালি হওয়ার তারিখ:', 'Field free by:')}</span>
          <strong>${escapeHtml(tr(opt.fieldFreeDateBangla, opt.fieldFreeDateEnglish))}</strong>
        </div>
        <button class="btn btn-sm ${isRec ? 'btn-primary' : 'btn-secondary'}" style="margin-top: 12px;" onclick="selectCandidateOption('${opt.id}')">
          ${isRec ? tr('এই চক্রটি নিশ্চিত করুন', 'Confirm this rotation') : tr('বিস্তারিত দেখুন', 'See details')}
        </button>
      </div>`;
  }).join(''));
}

function renderTimeline(option) {
  if (!option) return;
  setHtml('timelineContainer', option.timeline.map(slot => `
    <div class="timeline-month-col">
      <div class="month-label">${tr(slot.monthNameBangla, slot.monthNameEnglish)}</div>
      <div class="slot-indicator ${slot.status}">${escapeHtml(tr(slot.cropName, slot.cropNameEnglish))}</div>
    </div>
  `).join(''));
}

window.selectCandidateOption = async function(optionId) {
  if (!currentAdvice) return;
  selectedOptionId = optionId;
  renderTimeline(selectedOption());
  await loadNarration(selectedOption());
  window.switchScreen('screen-delivery');
};

// ---------------------------------------------------------------------------
// SCREEN 4: evidence built from the advice and the overview
// ---------------------------------------------------------------------------

function renderEvidence(advice) {
  const top = advice.options[0];
  const [aman, rabi] = top.cropSequence;
  const water = top.dimensionDetails.water?.metrics || {};
  const soil = top.dimensionDetails.soil?.metrics || {};
  const income = top.dimensionDetails.income?.metrics || {};
  const boro = advice.options.find(o => o.isBaseline);
  const o = currentOverview;

  setText('evidenceTitle', tr(`${aman.varietyBangla} → ${rabi.cropBangla} কেন তালন্দ ইউনিয়নের জন্য শীর্ষে?`, `Why ${aman.variety} → ${rabi.crop.toLowerCase()} tops the list for Talanda union`));
  setText('evidenceRelease', `${advice.release.id}, ${tr('গবেষণা কমিট', 'research commit')} ${advice.release.researchCommit}`);

  setText('evRescueBig', `${num(water.amanRescueIrrigationSeasons)} / ${num(water.totalSeasonsSimulated)}`);
  setText('evRescueText', tr(
    `২০০১–২০২৫ সালের ${num(water.totalSeasonsSimulated)} মৌসুমের ${num(water.amanRescueIrrigationSeasons)}টিতে ${aman.varietyBangla}-এ ফুল আসার সময় সম্পূরক সেচ লেগেছে (বছর: ${num(water.rescueYears)})।`,
    `In ${water.amanRescueIrrigationSeasons} of the ${water.totalSeasonsSimulated} seasons from 2001 to 2025, ${aman.variety} needed rescue irrigation at flowering (years: ${water.rescueYears}).`,
  ));
  if (o) {
    setHtml('evRescueList', [
      ...o.aman_replay.map(r => tr(
        `<li><strong>${escapeHtml(r.varietyBangla)}</strong> (${escapeHtml(r.noteBangla)}): ফুল ~${r.floweringBangla}, ${num(r.rescueSeasons)}/${num(r.totalSeasons)} মৌসুমে সেচ, জমি খালি ~${r.fieldFreeBangla}</li>`,
        `<li><strong>${escapeHtml(r.variety)}</strong> (${escapeHtml(r.noteEnglish)}): flowers ~${r.floweringEnglish}, irrigation in ${r.rescueSeasons}/${r.totalSeasons} seasons, field free ~${r.fieldFreeEnglish}</li>`,
      )),
      tr('<li><strong>তথ্যসূত্র:</strong> NASA POWER (FAO-56 ET0) ও GPM IMERG Final দৈনিক বৃষ্টি, ধানক্ষেতের পানির হিসাব।</li>', '<li><strong>Source:</strong> NASA POWER (FAO-56 ET0) and GPM IMERG Final daily rain in a paddy water balance.</li>'),
      tr('<li><strong>স্থানিক স্কেল:</strong> তানোর পাইলট পয়েন্টের গ্রিড সেল; একক জমির মাপ নয়।</li>', '<li><strong>Scale:</strong> the grid cell at the Tanore pilot point, not a single field.</li>'),
      o.soil_carbon ? tr(
        `<li><strong>যাচাই (SMAP GPP):</strong> শুকনো মৌসুমে আমনের উৎপাদন কমেনি (rho ${num(o.soil_carbon.dryDaysVsAmanGppRho)}, ${num(o.soil_carbon.dryDaysVsAmanGppSeasons)} মৌসুম): কৃষক সেচ দেন, তাই সম্পূরক সেচকে খরচ ধরা হয়েছে, ফসলহানি নয়।</li>`,
        `<li><strong>Check (SMAP GPP):</strong> Aman productivity did not drop in the dry seasons (rho ${o.soil_carbon.dryDaysVsAmanGppRho}, ${o.soil_carbon.dryDaysVsAmanGppSeasons} seasons): farmers irrigate, so rescue water counts as a cost, not a lost crop.</li>`,
      ) : '',
    ].join(''));
  }

  const smap = o?.local_satellite_conditions?.smap;
  const gldas = o?.context?.rootZoneGldasMm;
  const years = smap?.nov10Years || [];
  setText('evSoilBig', smap ? `${num(smap.nov10TypicalM3M3.toFixed(2))} m³/m³` : '—');
  setText('evSoilText', smap ? tr(
    `১০ নভেম্বরে শিকড় অঞ্চলের গড় আর্দ্রতা (SMAP L4, ${num(years[0])}–${num(years[years.length - 1])})। আমন আগে কাটলে এই রস রবির বীজ পায়।`,
    `Typical root-zone moisture on 10 Nov (SMAP L4, ${years[0]}–${years[years.length - 1]}). Harvest Aman early and the Rabi seed gets this moisture.`,
  ) : '');
  const boroSoil = boro?.dimensionDetails.soil?.metrics;
  setHtml('evSoilList', [
    gldas ? tr(
      `<li><strong>GLDAS-2.2:</strong> ১০ থেকে ১৯ নভেম্বরে শিকড় অঞ্চল থেকে আরও ~${num(gldas.lostNov10To19)} মিমি পানি শুকায়; SMAP-এর সাথে মিল (Spearman ${num(gldas.smapSpearman)})।</li>`,
      `<li><strong>GLDAS-2.2:</strong> the root zone loses another ~${gldas.lostNov10To19} mm between 10 and 19 Nov; it agrees with SMAP (Spearman ${gldas.smapSpearman}).</li>`,
    ) : '',
    tr(
      `<li><strong>SRDI তালন্দ কার্ড:</strong> ${escapeHtml(soil.srdiSoilType || '')}; ইউরিয়া ${num(soil.rabiUreaKgHa)} কেজি/হেক্টর (${rabi.cropBangla})।</li>`,
      `<li><strong>SRDI Talanda card:</strong> Kharia soil; urea ${soil.rabiUreaKgHa} kg/ha for ${rabi.crop.toLowerCase()}.</li>`,
    ),
    boroSoil ? tr(
      `<li><strong>পুরো চক্রে ইউরিয়া:</strong> ${num(soil.rotationUreaKgHa)} কেজি/হেক্টর, বোরো চক্রে ${num(boroSoil.rotationUreaKgHa)} কেজি।</li>`,
      `<li><strong>Urea for the whole rotation:</strong> ${soil.rotationUreaKgHa} kg/ha, against ${boroSoil.rotationUreaKgHa} kg/ha with Boro.</li>`,
    ) : '',
    o?.soil_carbon ? tr(
      `<li><strong>SMAP L4 কার্বন:</strong> মাটির জৈব কার্বন ~${bigNum(o.soil_carbon.soilCarbonGm2)} গ্রাম/বর্গমিটার (২০১৬–২০২৫), বছরে ${num('+' + o.soil_carbon.soilCarbonTrendGm2PerYear)}।</li>`,
      `<li><strong>SMAP L4 carbon:</strong> soil organic carbon ~${bigNum(o.soil_carbon.soilCarbonGm2)} g/m² (2016–2025), ${'+' + o.soil_carbon.soilCarbonTrendGm2PerYear} a year.</li>`,
    ) : '',
  ].join(''));

  if (o) {
    const gw = o.context.groundwater;
    const green = o.context.winterGreenness;
    const boroWater = boro?.dimensionDetails.water?.metrics;
    setText('evGroundBig', tr(`বছরে ${num(gw.trendMmPerYear)} মিমি`, `${gw.trendMmPerYear} mm a year`));
    setText('evGroundText', tr(
      `তানোরে GRACE-নির্ভর GLDAS-2.2 অনুযায়ী ভূগর্ভস্থ পানি কমছে: ${num(gw.period.replace(' to ', ' থেকে '))} সময়ে ${num(gw.changeMm)} মিমি।`,
      `GRACE-based GLDAS-2.2 shows Tanore’s groundwater falling: ${gw.changeMm} mm from ${gw.period}.`,
    ));
    setHtml('evGroundList', [
      tr(
        `<li><strong>MODIS:</strong> শীতের সর্বোচ্চ সবুজ (NDVI) ${num(green.early.peakNdvi)} থেকে ${num(green.recent.peakNdvi)}; বছরে গড় ফসল ${num(green.early.cyclesPerYear)} থেকে ${num(green.recent.cyclesPerYear)}।</li>`,
        `<li><strong>MODIS:</strong> peak winter greenness (NDVI) rose from ${green.early.peakNdvi} to ${green.recent.peakNdvi}; crops a year from ${green.early.cyclesPerYear} to ${green.recent.cyclesPerYear}.</li>`,
      ),
      tr(
        `<li><strong>প্রধান চক্র (${num(o.season_summary.landUseYear)}):</strong> ${escapeHtml(o.season_summary.dominantPatternBangla)}, উপজেলার ${num(o.season_summary.dominantPatternPct)}% জমি; ফসলের নিবিড়তা ${num(o.season_summary.croppingIntensity)}।</li>`,
        `<li><strong>Main rotation (${o.season_summary.landUseYear}):</strong> ${escapeHtml(o.season_summary.dominantPattern)} on ${o.season_summary.dominantPatternPct}% of the upazila’s land; cropping intensity ${o.season_summary.croppingIntensity}.</li>`,
      ),
      boroWater ? tr(
        `<li><strong>রবিতে সেচ:</strong> বোরো ~${num(boroWater.rabiNetIrrigationMm)} মিমি, ${rabi.cropBangla} ~${num(water.rabiNetIrrigationMm)} মিমি।</li>`,
        `<li><strong>Rabi irrigation:</strong> Boro ~${boroWater.rabiNetIrrigationMm} mm, ${rabi.crop.toLowerCase()} ~${water.rabiNetIrrigationMm} mm.</li>`,
      ) : '',
    ].join(''));
  }

  setText('evIncomeBig', tr(`${bigNum(income.illustrativeTotalBdtPerHa || 0)} ৳`, `BDT ${bigNum(income.illustrativeTotalBdtPerHa || 0)}`));
  setText('evIncomeText', tr('দুই মৌসুমের নিট লাভের নমুনা হিসাব (দলের অনুমান), যাচাই করা বাজারদর নয়।', 'Sample net profit over two seasons (team estimate), not verified market prices.'));
  setHtml('evIncomeList', [
    o ? tr(
      `<li><strong>গবাদিপশু:</strong> রাজশাহীতে প্রতি বর্গকিমিতে ~${num(Math.round(o.context.cattlePerKm2))}টি গরু (FAO GLW4, ২০১৫)।</li>`,
      `<li><strong>Livestock:</strong> about ${Math.round(o.context.cattlePerKm2)} cattle per km² in Rajshahi (FAO GLW4, 2015).</li>`,
    ) : '',
    typeof income.districtYieldTPerHa === 'number' ? tr(
      `<li><strong>জেলার গড় ফলন:</strong> ${rabi.cropBangla} ${num(income.districtYieldTPerHa)} টন/হেক্টর (BBS ২০২৪-২৫)।</li>`,
      `<li><strong>District yield:</strong> ${rabi.crop.toLowerCase()} ${income.districtYieldTPerHa} t/ha (BBS 2024-25).</li>`,
    ) : '',
    tr('<li><strong>বাকি:</strong> DAM খামার-দর ও কৃষকের খরচ সংগ্রহের পর আয়ের স্কোর বদলাবে।</li>', '<li><strong>Pending:</strong> the income score will change once DAM farm-gate prices and farmer costs are in.</li>'),
  ].join(''));
}

// ---------------------------------------------------------------------------
// SCREEN 5: less pesticide (IPM)
// ---------------------------------------------------------------------------

function renderIpm(advice) {
  renderLedger(advice);
  const top = advice.options[0];
  const boro = advice.options.find(o => o.isBaseline);
  const column = (opt) => {
    const m = opt.dimensionDetails.pest?.metrics || {};
    const yesNo = (v) => (v ? tr('হ্যাঁ', 'yes') : tr('না', 'no'));
    const resistant = m.resistantVariety && m.resistantVariety !== 'none listed' ? tr('আছে (BWMRI)', `${m.resistantVariety} (BWMRI)`) : tr('তালিকাভুক্ত নেই', 'none listed');
    return `
      <div class="ipm-column ${opt.isBaseline ? 'baseline' : 'recommended'}">
        <h4>${escapeHtml(tr(opt.nameBangla, opt.nameEnglish))}</h4>
        <div class="ipm-score">${num(Math.round((opt.scores.pest ?? 0) * 100))}<small>/${num(100)}</small></div>
        <ul class="kv-list">
          <li><span>${tr('ধানের পোকার চক্র ভাঙে', 'Breaks the rice-pest cycle')}</span><strong>${yesNo(m.breaksRicePestCycle)}</strong></li>
          <li><span>${tr('পুরো চক্রে ইউরিয়া (SRDI)', 'Rotation urea (SRDI)')}</span><strong>${num(m.rotationUreaKgHa)} ${tr('কেজি/হেক্টর', 'kg/ha')}</strong></li>
          <li><span>${tr('রোগ প্রতিরোধী জাত', 'Disease-resistant variety')}</span><strong>${resistant}</strong></li>
          <li><span>${tr('সময়মতো বোনা', 'Sown on time')}</span><strong>${yesNo(m.sownOnTime)}</strong></li>
        </ul>
      </div>`;
  };
  const topUrea = top.dimensionDetails.pest?.metrics.rotationUreaKgHa;
  const boroUrea = boro?.dimensionDetails.pest?.metrics.rotationUreaKgHa;
  const less = topUrea && boroUrea ? Math.round((100 * (boroUrea - topUrea)) / boroUrea) : null;
  setHtml('ipmCompare', `
    ${column(top)}
    ${boro && boro.id !== top.id ? column(boro) : ''}
    ${less !== null && less > 0 ? `<p class="ipm-summary">${tr(`প্রস্তাবিত চক্রে বছরে ইউরিয়া ${num(less)}% কম, আর ধানের পোকার চক্র ভাঙে। কম নাইট্রোজেন আর খাবারের বিরতি মানে কম পোকা, তাই কম স্প্রে।`, `The recommended rotation uses ${less}% less urea a year and breaks the rice-pest cycle. Less nitrogen and a break in the food supply mean fewer pests, so fewer sprays.`)}</p>` : ''}
  `);

  setHtml('ipmSteps', (top.ipmActions || []).map(tip => `
    <li><span>${escapeHtml(tr(tip.bn, tip.en))}</span> <span class="ipm-source">${escapeHtml(tip.source)}</span></li>
  `).join(''));

  setHtml('ipmRanking', [...advice.options].sort((a, b) => (b.scores.pest ?? 0) - (a.scores.pest ?? 0)).map(opt => {
    const pct = Math.round((opt.scores.pest ?? 0) * 100);
    return `
      <div class="dim-item">
        <div class="dim-header"><span>${escapeHtml(tr(opt.nameBangla, opt.nameEnglish))}</span><span>${num(pct)}/${num(100)}</span></div>
        <div class="dim-bar-wrap"><div class="dim-bar-fill pest" style="width: ${pct}%"></div></div>
        <span class="dim-note">${escapeHtml(tr(opt.dimensionDetails.pest?.summaryBangla, opt.dimensionDetails.pest?.summaryEnglish))}</span>
      </div>`;
  }).join(''));
}

// ---------------------------------------------------------------------------
// SCREEN 6: Krishi officer desk
// ---------------------------------------------------------------------------

async function loadOfficers() {
  officers = await (await fetch('/api/v1/officers')).json();
  renderOfficerSelect();
}

function renderOfficerSelect() {
  const select = $('officerSelect');
  const chosen = select.value;
  select.innerHTML = officers.map(o => `<option value="${escapeHtml(o.id)}">${escapeHtml(tr(`${o.nameBangla}, ${o.blockBangla}`, `${o.nameEnglish}, ${o.blockEnglish}`))}</option>`).join('');
  if (chosen) select.value = chosen;
}

async function officerFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${officerSession?.token}` },
  });
  if (res.status === 401) {
    window.officerSignOut();
    throw new Error('Officer session expired');
  }
  return res;
}

window.officerSignIn = async function(event) {
  event.preventDefault();
  const error = $('officerLoginError');
  error.hidden = true;
  const res = await fetch('/api/v1/officer/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ officerId: $('officerSelect').value, accessCode: $('officerCode').value }),
  });
  if (!res.ok) {
    error.textContent = tr('কর্মকর্তা বা প্রবেশ কোড ভুল।', 'Wrong officer or access code.');
    error.hidden = false;
    return;
  }
  officerSession = await res.json();
  $('officerCode').value = '';
  try {
    sessionStorage.setItem('eden.officer', JSON.stringify(officerSession));
  } catch {
    // storage blocked: the session lasts until this page closes
  }
  await loadOfficerDesk();
};

window.officerSignOut = function() {
  officerSession = null;
  officerDesk = null;
  officerKnowledge = null;
  officerNotice = null;
  try {
    sessionStorage.removeItem('eden.officer');
  } catch {
    // nothing stored
  }
  renderOfficer();
  renderProfile();
};

async function loadOfficerDesk() {
  if (!officerSession) return;
  try {
    const [deskRes, knowledgeRes] = await Promise.all([officerFetch('/api/v1/officer/desk'), officerFetch('/api/v1/officer/knowledge')]);
    officerDesk = await deskRes.json();
    officerKnowledge = await knowledgeRes.json();
  } catch {
    return;
  }
  renderOfficer();
  renderProfile();
  if (!$('obsFarmer').dataset.chosen) window.prefillObservation(officerDesk.queue[0]?.farmerId);
}

function farmerEntry(farmerId) {
  return officerDesk?.farmers.find(f => f.farmer.id === farmerId);
}

function renderProfile() {
  if (officerSession) {
    const o = officerSession.officer;
    setText('saaoName', tr(o.nameBangla, o.nameEnglish));
    setText('saaoRole', tr(`SAAO, ${o.blockBangla} • প্রবেশ করেছেন`, `SAAO, ${o.blockEnglish} • signed in`));
  } else {
    setText('saaoName', tr('নমুনা কর্মকর্তা', 'Sample officer'));
    setText('saaoRole', tr('SAAO, তালন্দ ব্লক', 'SAAO, Talanda block'));
  }
}

function renderOfficer() {
  renderOfficerSelect();
  const signedIn = Boolean(officerSession && officerDesk);
  $('officerLogin').hidden = signedIn;
  $('officerWorkspace').hidden = !signedIn;
  const badge = $('officerStateBadge');
  badge.className = `badge ${signedIn ? 'badge-success' : 'badge-warning'}`;
  badge.textContent = signedIn
    ? tr(`প্রবেশ করেছেন: ${officerSession.officer.nameBangla}`, `Signed in: ${officerSession.officer.nameEnglish}`)
    : tr('শুধু কর্মকর্তাদের জন্য', 'Officers only');
  if (!signedIn) return;
  renderQueue();
  renderFarmerOptions();
  renderRegister();
  renderKnowledge();
  renderObservationResult();
}

const LEVELS = {
  urgent: ['badge-danger', 'জরুরি', 'Urgent'],
  high: ['badge-warning', 'বেশি', 'High'],
  normal: ['badge-neutral', 'সাধারণ', 'Normal'],
};

function renderQueue() {
  setHtml('officerQueue', officerDesk.queue.map(item => {
    const f = farmerEntry(item.farmerId)?.farmer;
    const [cls, bn, en] = LEVELS[item.level];
    return `
      <div class="queue-item ${item.level}">
        <div class="queue-top">
          <strong>${escapeHtml(tr(f?.nameBangla, f?.nameEnglish))}</strong>
          <span class="badge ${cls}">${tr(bn, en)} • ${num(item.score)}</span>
        </div>
        <ul class="reason-list">${item.reasons.map(r => `<li>${escapeHtml(tr(r.bn, r.en))}</li>`).join('')}</ul>
        <div class="queue-actions">
          <button class="btn btn-sm btn-primary" type="button" onclick="prefillObservation('${item.farmerId}', true)">${tr('পর্যবেক্ষণ লিখুন', 'Record observation')}</button>
          ${item.openCallbackId ? `<button class="btn btn-sm btn-secondary" type="button" onclick="resolveCallback('${item.openCallbackId}')">${tr('কল করা হয়েছে', 'Called back')}</button>` : ''}
        </div>
      </div>`;
  }).join(''));
}

function renderFarmerOptions() {
  const select = $('obsFarmer');
  const chosen = select.value;
  select.innerHTML = officerDesk.farmers.map(({ farmer }) => `<option value="${farmer.id}">${escapeHtml(tr(`${farmer.nameBangla} (${farmer.villageBangla})`, `${farmer.nameEnglish} (${farmer.villageEnglish})`))}</option>`).join('');
  if (chosen) select.value = chosen;
}

function renderRegister() {
  setHtml('officerFarmers', officerDesk.farmers.map(({ farmer, observation, queue, advice }) => {
    const current = observation?.currentAmanCrop ?? farmer.currentAmanCrop;
    const landType = observation?.landType ?? farmer.landType;
    const status = observation
      ? `<span class="badge badge-success">${tr('কর্মকর্তা যাচাইকৃত', 'Officer-verified')}</span><br><small>${isoDate(observation.date)}${observation.pestSeen !== 'none' ? ` • 🐛 ${escapeHtml(tr(officerDesk.pestNames[observation.pestSeen].bn, officerDesk.pestNames[observation.pestSeen].en))}` : ''}</small>`
      : `<span class="badge badge-neutral">${tr('মাঠ যাচাই বাকি', 'Field check pending')}</span>`;
    const callback = queue?.openCallbackId ? ` <span class="badge badge-warning">${tr('কল-ব্যাক', 'Call-back')}</span>` : '';
    return `
      <tr>
        <td><strong>${escapeHtml(tr(farmer.nameBangla, farmer.nameEnglish))}</strong> <span class="tag tag-yellow">${tr('নমুনা', 'sample')}</span><br><small>${escapeHtml(farmer.phoneMasked)}</small></td>
        <td>${escapeHtml(land(landType))}<br><small>${escapeHtml(amanName(current))}</small></td>
        <td>${advice.thisSeasonOptionBangla && advice.thisSeasonOptionBangla !== advice.topOptionBangla
          ? `<small>${tr('এ মৌসুম', 'This season')}:</small> ${escapeHtml(tr(advice.thisSeasonOptionBangla, advice.thisSeasonOptionEnglish))}<br><small>${tr('আগামী মৌসুম', 'Next season')}: ${escapeHtml(tr(advice.topOptionBangla, advice.topOptionEnglish))}</small>`
          : `${escapeHtml(tr(advice.topOptionBangla, advice.topOptionEnglish))}<br><small>${tr('জমি খালি', 'Field free')}: ${escapeHtml(tr(advice.fieldFreeBangla, advice.fieldFreeEnglish))}</small>`}</td>
        <td><small>${escapeHtml(advice.thisSeason ? tr(advice.thisSeason.noteBangla, advice.thisSeason.noteEnglish) : '')}</small></td>
        <td>${status}${callback}</td>
      </tr>`;
  }).join(''));
}

function renderKnowledge() {
  const k = officerKnowledge;
  if (!k) return;
  const kg = (v) => num(Number.isInteger(v) ? v : v.toFixed(1));
  setHtml('officerKnowledge', `
    <div class="knowledge-block">
      <h4>${tr('SRDI তালন্দ কার্ড (মাঝারি উঁচু জমি, কেজি/হেক্টর)', 'SRDI Talanda card (medium-high land, kg/ha)')}</h4>
      <p class="muted">${escapeHtml(tr(`${k.srdi.soilTypeBangla}; কৃষকের অ্যাপে শুধু ইউরিয়া, টিএসপি, এমওপি যায়।`, 'Kharia soil; the farmer app shows only urea, TSP and MoP.'))}</p>
      <div class="table-responsive"><table class="data-table compact">
        <thead><tr><th>${tr('ফসল', 'Crop')}</th><th>${tr('ইউরিয়া', 'Urea')}</th><th>TSP</th><th>MoP</th><th>${tr('জিপসাম', 'Gypsum')}</th><th>${tr('জিংক সালফেট', 'Zinc sulphate')}</th><th>${tr('বরিক এসিড', 'Boric acid')}</th></tr></thead>
        <tbody>${k.srdi.rows.map(r => `<tr><td>${escapeHtml(tr(r.cropBangla, r.cropEnglish))}</td><td>${kg(r.dose.ureaKgHa)}</td><td>${kg(r.dose.tspKgHa)}</td><td>${kg(r.dose.mopKgHa)}</td><td>${kg(r.dose.gypsumKgHa)}</td><td>${kg(r.dose.zincSulphateKgHa)}</td><td>${kg(r.dose.boricAcidKgHa)}</td></tr>`).join('')}</tbody>
      </table></div>
    </div>
    <div class="knowledge-block">
      <h4>${tr('আমন রি-প্লে (২০০১–২০২৫)', 'Aman replay (2001–2025)')}</h4>
      <div class="table-responsive"><table class="data-table compact">
        <thead><tr><th>${tr('জাত', 'Variety')}</th><th>${tr('ফুল', 'Flowering')}</th><th>${tr('জমি খালি', 'Field free')}</th><th>${tr('সম্পূরক সেচের বছর', 'Rescue-irrigation years')}</th></tr></thead>
        <tbody>${k.amanReplay.map(r => `<tr><td>${escapeHtml(tr(r.varietyBangla, r.variety))}</td><td>${escapeHtml(tr(r.floweringBangla, r.floweringEnglish))}</td><td>${escapeHtml(tr(r.fieldFreeBangla, r.fieldFreeEnglish))}</td><td>${num(r.rescueSeasons)}/${num(r.totalSeasons)}: ${num(r.rescueYears.join(', '))}</td></tr>`).join('')}</tbody>
      </table></div>
    </div>
    <div class="knowledge-block">
      <h4>${tr('রবি রি-প্লে', 'Rabi replay')}</h4>
      <div class="table-responsive"><table class="data-table compact">
        <thead><tr><th>${tr('ফসল', 'Crop')}</th><th>${tr('বপন (সময়সীমা)', 'Sowing (window)')}</th><th>${tr('সেচ, মিমি (p10–p90)', 'Irrigation, mm (p10–p90)')}</th><th>${tr('অতিরিক্ত গরম', 'Heat exposure')}</th></tr></thead>
        <tbody>${k.rabiReplay.map(r => `<tr><td>${escapeHtml(tr(r.cropBangla, r.cropEnglish))}${r.key.includes('(') ? ` <small>${escapeHtml(r.key.slice(r.key.indexOf('(')))}</small>` : ''}</td><td>${escapeHtml(tr(r.sowingBangla, r.sowingEnglish))}${r.windowEnglish ? ` <small>(${escapeHtml(r.windowEnglish)}, ${escapeHtml(r.windowSource)})</small>` : ''}</td><td>${num(r.netIrrigationMm)} (${num(r.netIrrigationRangeMm[0])}–${num(r.netIrrigationRangeMm[1])})</td><td>${r.heat ? tr(`${num(r.heat.hotDays)}/${num(r.heat.windowDays)} দিন > ${num(r.heat.thresholdC)}°C`, `${r.heat.hotDays}/${r.heat.windowDays} days > ${r.heat.thresholdC}°C`) : '—'}</td></tr>`).join('')}</tbody>
      </table></div>
    </div>
    <div class="knowledge-block">
      <h4>${tr('তথ্যের সীমাবদ্ধতা', 'Data caveats')}</h4>
      <ul class="evidence-list">${k.caveats.map(c => `<li>${escapeHtml(tr(c.bn, c.en))}</li>`).join('')}</ul>
      <h4>${tr('প্রযুক্তিগত নোট (ইংরেজি)', 'Technical notes')}</h4>
      <p class="muted">${escapeHtml(k.saaoNotes)}</p>
    </div>
  `);
}

window.prefillObservation = function(farmerId, scroll = false) {
  const entry = farmerEntry(farmerId);
  if (!entry) return;
  const { farmer, observation } = entry;
  const select = $('obsFarmer');
  select.value = farmer.id;
  select.dataset.chosen = farmer.id;
  $('obsLand').value = observation?.landType ?? farmer.landType;
  $('obsAman').value = observation?.currentAmanCrop ?? farmer.currentAmanCrop;
  $('obsIrrigation').value = observation?.irrigation ?? farmer.irrigation;
  $('obsPest').value = observation?.pestSeen ?? 'none';
  $('obsSeverity').value = observation?.pestSeverity ?? 'low';
  const p = observation?.priorities ?? { water: 0.5, income: 0.2, soil: 0.2, pest: 0.1 };
  $('obsWater').value = Math.round(p.water * 100);
  $('obsIncome').value = Math.round(p.income * 100);
  $('obsSoil').value = Math.round(p.soil * 100);
  $('obsPestPriority').value = Math.round(p.pest * 100);
  $('obsNote').value = observation?.noteBangla ?? '';
  window.updateObsWeights();
  if (scroll) $('observationForm').scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window.submitObservation = async function(event) {
  event.preventDefault();
  const weight = (id) => parseFloat($(id).value) / 100;
  const body = {
    farmerId: $('obsFarmer').value,
    landType: $('obsLand').value,
    currentAmanCrop: $('obsAman').value,
    irrigation: $('obsIrrigation').value,
    pestSeen: $('obsPest').value,
    pestSeverity: $('obsSeverity').value,
    priorities: { water: weight('obsWater'), income: weight('obsIncome'), soil: weight('obsSoil'), pest: weight('obsPestPriority') },
    noteBangla: $('obsNote').value,
    resolveCallbacks: $('obsResolve').checked,
  };
  const res = await officerFetch('/api/v1/officer/observations', { method: 'POST', body: JSON.stringify(body) });
  const data = await res.json();
  officerNotice = res.ok ? { farmerId: body.farmerId, advice: data.advice } : { error: data.error };
  if (res.ok) {
    await Promise.all([loadOfficerDesk(), loadOverview()]);
  }
  renderObservationResult();
};

function renderObservationResult() {
  const box = $('observationResult');
  if (!officerNotice) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  if (officerNotice.error) {
    box.className = 'obs-result error';
    box.textContent = officerNotice.error;
    return;
  }
  const farmer = farmerEntry(officerNotice.farmerId)?.farmer;
  const advice = officerNotice.advice;
  const top = advice.options[0];
  const now = advice.options.find(o => o.id === advice.this_season_option_id);
  box.className = 'obs-result';
  box.innerHTML = `
    <strong>${escapeHtml(tr(`${farmer?.nameBangla ?? ''}-এর পরামর্শ হালনাগাদ হয়েছে`, `Advice updated for ${farmer?.nameEnglish ?? ''}`))}</strong>
    ${now && now.id !== top.id ? `<p>${tr('এ মৌসুমে', 'This season')}: ${escapeHtml(tr(now.nameBangla, now.nameEnglish))}</p>` : ''}
    <p>${now && now.id !== top.id ? tr('আগামী মৌসুমে', 'Next season') : tr('শীর্ষ চক্র', 'Top rotation')}: ${escapeHtml(tr(top.nameBangla, top.nameEnglish))}</p>
    ${advice.this_season ? `<p>${escapeHtml(tr(advice.this_season.noteBangla, advice.this_season.noteEnglish))}</p>` : ''}
    ${advice.verification ? `<p><span class="badge badge-success">${tr('কর্মকর্তা যাচাইকৃত', 'Officer-verified')}</span> ${escapeHtml(advice.verification.noteBangla)}</p>` : ''}
  `;
}

window.resolveCallback = async function(callbackId) {
  await officerFetch(`/api/v1/officer/callbacks/${encodeURIComponent(callbackId)}/resolve`, { method: 'POST', body: '{}' });
  await Promise.all([loadOfficerDesk(), loadOverview()]);
};

window.officerReset = async function() {
  await officerFetch('/api/v1/officer/reset', { method: 'POST', body: '{}' });
  officerNotice = null;
  delete $('obsFarmer').dataset.chosen;
  await Promise.all([loadOfficerDesk(), loadOverview()]);
};

// ---------------------------------------------------------------------------
// SCREEN 8: the spoken text comes from the server's checked template
// ---------------------------------------------------------------------------

async function loadNarration(opt) {
  if (!opt || !currentAdvice) return;
  try {
    const res = await fetch('/api/v1/narrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ advice: currentAdvice, selectedOptionId: opt.id }),
    });
    currentNarration = await res.json();
    renderNarration();
  } catch (err) {
    console.error('Narration failed:', err);
  }
}

function renderNarration() {
  if (!currentNarration) return;
  // Farmers always hear Bangla; English mode adds a translation underneath
  setText('previewBanglaText', currentNarration.banglaSpeechText);
  const gloss = $('previewEnglishGloss');
  gloss.hidden = lang !== 'en' || !currentNarration.englishGloss;
  gloss.textContent = currentNarration.englishGloss ? `English translation: ${currentNarration.englishGloss}` : '';
  setText('audioTime', tr(`~${num(currentNarration.durationSecondsEstimate)} সেকেন্ড`, `~${currentNarration.durationSecondsEstimate} seconds`));
  setText('narrationEngineTag', currentNarration.status === 'verified_template' ? tr('✓ ভেরিফাইড টেমপ্লেট (Verified Template)', '✓ Verified template') : `✓ ${currentNarration.status}`);
}

function renderAudioButton() {
  const labels = {
    idle: tr('বাংলা ভয়েস শুনুন (Audio Preview)', 'Play the Bangla voice (audio preview)'),
    playing: tr('ভয়েস প্লে হচ্ছে...', 'Playing...'),
    done: tr('পুনরায় শুনুন (Replay)', 'Replay'),
    novoice: tr('এই ব্রাউজারে বাংলা ভয়েস নেই', 'No Bangla voice in this browser'),
  };
  setText('audioPlayText', labels[audioState]);
  setText('audioPlayIcon', audioState === 'playing' ? '⏸' : '▶');
}

// Audio preview: the browser's Bangla voice when available, otherwise a progress bar only
window.toggleAudioPreview = function() {
  const progress = $('audioProgress');
  const text = $('previewBanglaText')?.textContent?.trim() || '';

  if (audioState === 'playing') {
    clearInterval(audioTimer);
    window.speechSynthesis?.cancel();
    audioState = 'idle';
    progress.style.width = '0%';
    renderAudioButton();
    return;
  }

  const voice = window.speechSynthesis?.getVoices().find(v => v.lang.toLowerCase().startsWith('bn'));
  if (voice && text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.onend = () => {
      audioState = 'done';
      renderAudioButton();
    };
    window.speechSynthesis.speak(utterance);
    audioState = 'playing';
  } else {
    audioState = 'novoice';
  }
  renderAudioButton();

  let current = 0;
  clearInterval(audioTimer);
  audioTimer = setInterval(() => {
    current += 2.5;
    progress.style.width = `${Math.min(current, 100)}%`;
    if (current >= 100) clearInterval(audioTimer);
  }, 100);
};

// Dispatch Advice Call (simulation only, nothing is sent)
window.dispatchAdviceCall = function() {
  const t = () => new Date().toLocaleTimeString(lang === 'en' ? 'en-GB' : 'bn-BD');
  const sim = tr('[সিমুলেশন]', '[simulation]');
  setHtml('liveCallLog', `
    <span class="log-line">[${t()}] ${sim} ${tr('আউটগোয়িং IVR কল শুরু হচ্ছে', 'Outgoing IVR call starting')}: 01712-XXXXXX</span>
    <span class="log-line">[${t()}] ${sim} ${tr('টেলকো গেটওয়ে: কল রিং হচ্ছে...', 'Telco gateway: ringing...')}</span>
    <span class="log-line">[${t()}] ${sim} ${tr('কৃষক কল রিসিভ করেছেন', 'Farmer answered')}</span>
    <span class="log-line">[${t()}] ${sim} ${tr('অনুমোদিত বাংলা ভয়েস বাজানো হচ্ছে...', 'Playing the approved Bangla voice...')}</span>
  `);
};

// Simulate farmer keypad: 1-4 re-rank for that priority; 9 puts a call-back on the officer desk
window.simulateFarmerKeypad = async function(key) {
  const logBox = $('liveCallLog');
  const t = () => new Date().toLocaleTimeString(lang === 'en' ? 'en-GB' : 'bn-BD');
  logBox.innerHTML += `<span class="log-line key-line">[${t()}] ${tr('কৃষকের কিপ্যাড ইনপুট', 'Farmer pressed')}: [ ${num(key)} ]</span>`;
  try {
    const res = await fetch('/api/v1/channel-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keypad: key, phone: '017XX-XXX01', farmerId: 'F01' }),
    });
    const data = await res.json();
    logBox.innerHTML += `<span class="log-line">[${t()}] ${tr('সিস্টেম', 'System')}: ${escapeHtml(tr(data.acknowledgementBangla, data.acknowledgementEnglish))}</span>`;
    if (data.callbackId) {
      logBox.innerHTML += `<span class="log-line">[${t()}] ${tr('কর্মকর্তা ডেস্কের তালিকায় কল-ব্যাক অনুরোধ যোগ হয়েছে।', 'Call-back request added to the officer desk queue.')}</span>`;
      await Promise.all([loadOverview(), loadOfficerDesk()]);
    }
  } catch (err) {
    console.error('Keypad simulation error:', err);
  }
};

// ---------------------------------------------------------------------------
// SCREEN 9: companion phone mock-up
// ---------------------------------------------------------------------------

function renderCompanion(advice) {
  const top = advice.options[0];
  const water = top.dimensionDetails.water?.metrics || {};
  const heat = top.dimensionDetails.heat?.metrics || {};
  const soil = top.dimensionDetails.soil?.metrics || {};
  const english = top.approvedActionEnglish || [];
  setText('compAction', tr(top.approvedActionBangla[1] || '', english[1] || ''));
  setText('compActionText', tr(top.approvedActionBangla[2] || '', english[2] || ''));
  setText('compRotation', `${tr('ফসল চক্র', 'Rotation')}: ${tr(top.nameBangla, top.nameEnglish)}`);
  setText('compWater', `${num(water.rabiNetIrrigationMm)} ${tr('মিমি', 'mm')}`);
  setText('compHeat', `${num(heat.hotDays ?? 0)} ${tr('দিন', 'days')}`);
  setText('compUrea', `${num(Math.round(soil.rotationUreaKgHa || 0))} ${tr('কেজি', 'kg')}`);
  setText('compFooter', `${tr('রিলিজ', 'Release')} ${advice.release.id} • ${tr('ক্যাশড ভার্সন', 'cached version')}`);
}

// ---------------------------------------------------------------------------
// SCREEN 10: data quality table
// ---------------------------------------------------------------------------

const STATUS = {
  operational: ['সক্রিয়', 'Live', 'badge-success'],
  'cross-checked': ['যাচাইসহ সক্রিয়', 'Live, cross-checked', 'badge-info'],
  missing: ['বাকি', 'Pending', 'badge-warning'],
};

async function loadDataQualityTable() {
  try {
    currentDataRelease = await (await fetch('/api/v1/data-release')).json();
    renderQuality(currentDataRelease);
  } catch (err) {
    console.error('Failed to load data quality:', err);
  }
}

function renderQuality(data) {
  setHtml('qualityTableBody', data.datasets.map(d => {
    const [bn, en, cls] = STATUS[d.status] || [d.status, d.status, 'badge-neutral'];
    return `
      <tr>
        <td><strong>${escapeHtml(d.name)}</strong><br><span class="muted small">${escapeHtml(d.parameter)}</span></td>
        <td>${escapeHtml(d.timePeriod)}<br><span class="small" style="color: var(--water);">${escapeHtml(d.spatialResolution)}</span></td>
        <td><span class="tag ${d.status === 'missing' ? 'tag-yellow' : 'tag-green'}">${escapeHtml(d.freshness)}</span><br><span class="small">${tr('ল্যাটেন্সি', 'Latency')}: ${escapeHtml(d.latency)}</span></td>
        <td><span class="small" style="color: var(--success);">${escapeHtml(d.groundCorrection)}</span></td>
        <td><span class="badge ${cls}">${tr(bn, en)}</span></td>
      </tr>`;
  }).join(''));
  const missing = data.datasets.filter(d => d.status === 'missing').length;
  setText('qualityBadge', tr(`${num(data.datasets.length - missing)}টি সচল, ${num(missing)}টি বাকি`, `${data.datasets.length - missing} live, ${missing} pending`));
}

// ---------------------------------------------------------------------------
// Initial load: language, overview, advice, data quality, officer list (and desk if signed in)
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const saved = localStorage.getItem('eden.lang');
    if (saved === 'en' || saved === 'bn') lang = saved;
    const session = sessionStorage.getItem('eden.officer');
    if (session) officerSession = JSON.parse(session);
  } catch {
    // storage blocked: start in Bangla, signed out
  }
  applyStaticText();
  await loadOverview();
  await window.runPlannerCalculation({ switchScreenAfter: false });
  await loadDataQualityTable();
  await loadOfficers();
  if (officerSession) await loadOfficerDesk();
  renderAll();
});
