import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { RotationEngine } from '../../../packages/rotation-engine/src/engine.ts';
import { FeatureRegistry } from '../../../packages/rotation-engine/src/registry.ts';
import { DualGateNarrationValidator } from '../../../packages/narration-core/src/dual_gate_validator.ts';
import { TemplateNarrator } from '../../../packages/narration-core/src/template_narrator.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PUBLIC_DIR = path.resolve(__dirname, '../../../apps/saao-dashboard/public');

const featureRegistry = new FeatureRegistry();
const rotationEngine = new RotationEngine(featureRegistry);
const templateNarrator = new TemplateNarrator();
const dualGateValidator = new DualGateNarrationValidator();

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 4000;

function sendJSON(res: http.ServerResponse, statusCode: number, data: any) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(data));
}

function parseBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const pathname = url.pathname;

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  try {
    // API: SAAO Overview
    if (pathname === '/api/v1/overview' && req.method === 'GET') {
      return sendJSON(res, 200, {
        scope: {
          district: 'Rajshahi (রাজশাহী)',
          upazila: 'Tanore (তানোর)',
          union: 'Talanda (তালন্দ)',
          union_id: 'talanda_tanore',
          land_type: 'medium_high',
        },
        data_release: {
          version: 'bd-pilots-2026.10.1',
          releaseDate: '2026-09-28',
          status: 'healthy',
          missingInputs: [],
        },
        season_summary: {
          season: 'Aman 2026 (আমন ২০২৬)',
          dominantPaddy: 'T.Aman (BRRI dhan49 / BRRI dhan71)',
          croppingIntensity: '224%',
          activeFarmersInUnion: 342,
        },
        local_satellite_conditions: {
          imerg_rain_last_7d_mm: 14.2,
          imerg_rain_status: 'স্বাভাবিক (Normal)',
          smap_rootzone_moisture: 0.245,
          smap_moisture_status: 'পর্যাপ্ত (Optimal 0.24 m³/m³)',
          power_et0_current: 3.8,
          modis_harvest_expected: '25 Oct - 10 Nov',
        },
        active_alerts: [
          {
            id: 'alt_01',
            type: 'warning',
            titleBangla: 'অক্টোবর শেষভাগে সম্ভাব্য বৃষ্টিহীন দিন (Dry Spell)',
            titleEnglish: 'Potential dry spell during mid-October flowering stage',
            recommendationBangla: 'স্বল্পমেয়াদি জাত (ব্রি ধান৭১) নির্বাচন করলে খরা এড়ানো সম্ভব।',
          },
        ],
        recent_farmer_contacts: [
          { name: 'নমুনা কৃষক ০১', village: 'নমুনা গ্রাম ০১', status: 'IVR Delivered (Keypad: 1)', date: 'আজ, সকাল ৯:১৫' },
          { name: 'নমুনা কৃষক ০২', village: 'নমুনা গ্রাম ০২', status: 'SMS Delivered', date: 'গতকাল' },
        ],
      });
    }

    // API: Generate Rotation Advice
    if (pathname === '/api/v1/advice' && req.method === 'POST') {
      const body = await parseBody(req);
      const advice = rotationEngine.generateAdvice({
        unionId: body.unionId || 'talanda_tanore',
        unionNameBangla: body.unionNameBangla || 'তালন্দ ইউনিয়ন',
        upazila: body.upazila || 'Tanore',
        district: body.district || 'Rajshahi',
        landType: body.landType || 'medium_high',
        season: body.season || '2026-aman',
        farmerPriorities: body.farmerPriorities || {
          water: 0.5,
          income: 0.3,
          soil: 0.2,
        },
      });
      return sendJSON(res, 200, advice);
    }

    // API: Narrate Advice
    if (pathname === '/api/v1/narrate' && req.method === 'POST') {
      const body = await parseBody(req);
      const advice = body.advice;
      const selectedOptionId = body.selectedOptionId;
      const option = advice?.options?.find((o: any) => o.id === selectedOptionId) || advice?.options?.[0];

      if (!advice || !option) {
        return sendJSON(res, 400, { error: 'Advice object and option are required' });
      }

      // Check if user requested mock local LLM or template
      if (body.simulateLLM) {
        const mockLLM = {
          async generate() {
            return `${advice.scope.union_name_bangla}র জন্য ${option.nameBangla} অত্যন্ত উপযোগী। ২৫ বছরে মাত্র ${option.dimensionDetails.water.metrics.amanRescueIrrigationSeasons} বার সেচ লেগেছে এবং ${option.fieldFreeDateBangla}র মধ্যে জমি খালি হবে।`;
          },
        };
        const customValidator = new DualGateNarrationValidator(mockLLM);
        const result = await customValidator.narrate(advice, option);
        return sendJSON(res, 200, result);
      }

      const result = await dualGateValidator.narrate(advice, option);
      return sendJSON(res, 200, result);
    }

    // API: Channel Events (Simulate IVR Call & Keypad)
    if (pathname === '/api/v1/channel-events' && req.method === 'POST') {
      const body = await parseBody(req);
      const keypad = body.keypad || '1';
      const responseMessages: Record<string, string> = {
        '1': 'আপনার পছন্দ "পানির নিরাপত্তা" নথিভুক্ত হয়েছে। কম সেচের ফসল তালিকায় শীর্ষে রাখা হয়েছে।',
        '2': 'আপনার পছন্দ "সর্বোচ্চ আয়" নথিভুক্ত হয়েছে। লাভজনক ফসল তালিকায় শীর্ষে রাখা হয়েছে।',
        '3': 'আপনার পছন্দ "মাটি স্বাস্থ্য" নথিভুক্ত হয়েছে। ডাল ও জৈব সার সমৃদ্ধকারী ফসল অগ্রাধিকার পেয়েছে।',
        '9': 'উপজেলা কৃষি কর্মকর্তার সাথে সংযোগ স্থাপন করা হচ্ছে। অনুগ্রহ করে লাইনে থাকুন...',
      };

      return sendJSON(res, 200, {
        callId: `call_${Date.now()}`,
        farmerPhone: body.phone || '017XXXXXXXX',
        status: 'delivered',
        keypadInput: keypad,
        acknowledgementBangla: responseMessages[keypad] || responseMessages['1'],
        timestamp: new Date().toISOString(),
      });
    }

    // API: Data Quality & Provenance
    if (pathname === '/api/v1/data-release' && req.method === 'GET') {
      return sendJSON(res, 200, {
        releaseVersion: 'bd-pilots-2026.10.1',
        pilotSitesCovered: 5,
        totalPilotUnions: 48,
        datasets: [
          {
            name: 'NASA POWER AG',
            parameter: 'Tmax, Tmin, Dew Point, Radiation, Wind, PS -> FAO-56 ET0',
            timePeriod: '2001-2025 (Daily)',
            spatialResolution: '0.5 deg (downscaled to 0.1 deg)',
            latency: '24 hours',
            freshness: 'Fresh (Up to date)',
            groundCorrection: 'NOAA GSOD / BMD Rajshahi Weather Station',
            status: 'operational',
          },
          {
            name: 'NASA GPM IMERG Final Run',
            parameter: 'Daily precipitation (rain)',
            timePeriod: '2001-2025',
            spatialResolution: '0.1 deg (~10 km)',
            latency: 'Quarterly final / NRT Late Run for last 4 days',
            freshness: 'Fresh',
            groundCorrection: 'Rajshahi Gauge Station (+11% bias checked)',
            status: 'operational',
          },
          {
            name: 'NASA SMAP L4',
            parameter: 'Root-zone soil moisture (0-100 cm)',
            timePeriod: '2023-2025 (Nov-Dec focus)',
            spatialResolution: '9 km gridded',
            latency: 'Daily',
            freshness: 'Fresh',
            groundCorrection: 'SRDI Soil Moisture Profiles',
            status: 'operational',
          },
          {
            name: 'NASA MODIS (MOD13Q1)',
            parameter: 'NDVI Vegetation Greenness & Harvest Timing',
            timePeriod: '2001-2025 (16-day composite)',
            spatialResolution: '250 m',
            latency: '16 days',
            freshness: 'Fresh',
            groundCorrection: 'Ground phenology observations',
            status: 'operational',
          },
          {
            name: 'SRDI Fertilizer Guide (FRS)',
            parameter: 'Talanda Union Soil Series & Nutrient Recommendations',
            timePeriod: '2020-2026',
            spatialResolution: 'Union level (Talanda)',
            latency: 'Static baseline',
            freshness: 'Verified card #RAJ_TAN_TAL_04',
            groundCorrection: 'Soil sample laboratory assays',
            status: 'operational',
          },
          {
            name: 'BRRI & BARI Crop Handbooks',
            parameter: 'Durations, planting windows, fertilizer doses, yields',
            timePeriod: '10th Edition + Regional Papers',
            spatialResolution: 'National / Barind regional trials',
            latency: 'Static baseline',
            freshness: 'Verified',
            groundCorrection: 'Research station field trials',
            status: 'operational',
          },
        ],
        missingValuePolicy: 'Missing values are NEVER filled with zero. If precipitation or temperature is missing, spatial interpolation from BMD Rajshahi is logged and flagged as uncertain.',
      });
    }

    // Serve static files from apps/saao-dashboard/public
    let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }

    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes: Record<string, string> = {
      '.html': 'text/html; charset=utf-8',
      '.css': 'text/css; charset=utf-8',
      '.js': 'application/javascript; charset=utf-8',
      '.json': 'application/json; charset=utf-8',
      '.png': 'image/png',
      '.svg': 'image/svg+xml',
    };

    const contentType = mimeTypes[ext] || 'text/plain';
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch (err: any) {
    console.error('Server error:', err);
    sendJSON(res, 500, { error: err.message || 'Internal Server Error' });
  }
});

server.listen(PORT, () => {
  console.log(`✓ EDEN API & SAAO Dashboard server listening on http://localhost:${PORT}`);
});
