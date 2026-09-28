import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';
import { TANORE_AMAN_REPLAY, TANORE_RABI_REPLAY } from '../data/tanore_replay_data.ts';

export class WaterDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'water';
  readonly displayNameBangla = 'পানির নিরাপত্তা ও সেচ সাশ্রয়';
  readonly displayNameEnglish = 'Water Security & Irrigation Demand';
  readonly version = '1.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const amanCrop = context.crops.find(c => c.variety.includes('dhan') || c.cropName.includes('Aman'));
    const rabiCrop = context.crops.find(c => !c.variety.includes('dhan') || c.cropName.includes('Boro'));

    const amanData = TANORE_AMAN_REPLAY[amanCrop?.variety || 'BRRI dhan71'] || TANORE_AMAN_REPLAY['BRRI dhan71'];
    const rabiData = TANORE_RABI_REPLAY[rabiCrop?.variety || 'BARI Masur-8'] || TANORE_RABI_REPLAY['BARI Masur-8'];

    const amanRescueSeasons = amanData.floweringDroughtSeasons;
    const rabiNetWaterMm = rabiData.netIrrigationMm;

    let waterScore = 1.0 - (amanRescueSeasons / 25) * 0.35 - (rabiNetWaterMm / 1000) * 0.55;
    waterScore = Math.max(0.1, Math.min(0.98, Number(waterScore.toFixed(2))));

    const banglaSummary = `${amanData.variety} লাগালে ২৫ মৌসুমে মাত্র ${amanRescueSeasons} বার সম্পূরক সেচ লাগে। রবিতে ${rabiData.cropName}-এ মোট সেচ লাগবে মাত্র ${rabiNetWaterMm} মিমি।`;

    return {
      dimensionId: this.id,
      score: waterScore,
      confidence: 'high',
      summaryBangla: banglaSummary,
      summaryEnglish: `${amanData.variety} required rescue irrigation in ${amanRescueSeasons} of 25 seasons. Rabi ${rabiData.cropName} requires ${rabiNetWaterMm} mm net irrigation.`,
      metrics: {
        amanRescueIrrigationSeasons: amanRescueSeasons,
        totalSeasonsSimulated: 25,
        rabiNetIrrigationMm: rabiNetWaterMm,
        totalCropWaterUseMm: amanData.waterUseMm + rabiNetWaterMm,
      },
      provenance: {
        source: 'NASA POWER (ET0) + NASA GPM IMERG (Daily Rain, gauge-verified with BMD Rajshahi)',
        timePeriod: '2001-2025 (25 Historical Seasons)',
        spatialResolution: '0.1 deg (~10 km) Tanore Grid Cell',
        measuredOrModeled: 'modeled',
        notesBangla: 'FAO-56 পেনম্যান-মন্টিথ ও রেইনফেড ধানক্ষেতের ওয়াটার ব্যালেন্স মডেল দ্বারা নির্ধারিত।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    const rescue = result.metrics.amanRescueIrrigationSeasons;
    const rabiMm = result.metrics.rabiNetIrrigationMm;
    return {
      banglaBullets: [
        `২৫ বছরের নাসার বৃষ্টিপাত ও বাষ্পীভবন মডেলে ২৫ মৌসুমে মাত্র ${rescue} বার সম্পূরক সেচ লেগেছে।`,
        `রবি মৌসুমে ভূগর্ভস্থ পানি মাত্র ${rabiMm} মিমি খরচ হবে (বোরো ধানের চেয়ে প্রায় ৭০% কম)।`,
        `ফুল আসার সংবেদনশীল সময়ে ধানক্ষেতে পানির স্থায়িত্ব নিশ্চিত থাকে।`,
      ],
      englishBullets: [
        `Rescue irrigation needed in only ${rescue} of 25 historical seasons during sensitive flowering stage.`,
        `Rabi net irrigation requirement is ${rabiMm} mm (~70% savings compared to Boro rice).`,
      ],
    };
  }
}
