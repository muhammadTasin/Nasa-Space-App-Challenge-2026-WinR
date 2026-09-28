import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';
import { TANORE_AMAN_REPLAY, TANORE_RABI_REPLAY } from '../data/tanore_replay_data.ts';

export class HeatDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'heat';
  readonly displayNameBangla = 'তাপমাত্রার সহনশীলতা ও খরা ঝুঁকি';
  readonly displayNameEnglish = 'Thermal Tolerance & Heat Stress';
  readonly version = '1.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const amanCrop = context.crops.find(c => c.variety.includes('dhan') || c.cropName.includes('Aman'));
    const rabiCrop = context.crops.find(c => !c.variety.includes('dhan') || c.cropName.includes('Boro'));

    const amanData = TANORE_AMAN_REPLAY[amanCrop?.variety || 'BRRI dhan71'] || TANORE_AMAN_REPLAY['BRRI dhan71'];
    const rabiData = TANORE_RABI_REPLAY[rabiCrop?.variety || 'BARI Masur-8'] || TANORE_RABI_REPLAY['BARI Masur-8'];

    const heatDays = rabiData.heatStressRiskDays;
    let heatScore = 1.0 - (heatDays / 35.0);
    heatScore = Math.max(0.2, Math.min(0.95, Number(heatScore.toFixed(2))));

    const banglaSummary = heatDays === 0
      ? `আগাম আমন কাটার কারণে রবি ফসল মার্চ মাসের তীব্র গরমের আগেই ঘরে তোলা যাবে (তাপমাত্রা ঝুঁকি শূন্য)।`
      : `দানা পুষ্ট হওয়ার সময়ে আনুমানিক ${heatDays} দিন উচ্চ তাপমাত্রার (৩০°C+) সম্মুখীন হতে পারে।`;

    return {
      dimensionId: this.id,
      score: heatScore,
      confidence: 'high',
      summaryBangla: banglaSummary,
      summaryEnglish: heatDays === 0
        ? `Early harvest avoids terminal heat stress entirely before March temperatures rise.`
        : `Faces approximately ${heatDays} days of terminal heat stress during grain filling stage.`,
      metrics: {
        terminalHeatStressDays: heatDays,
        criticalThresholdTempC: 30.0,
      },
      provenance: {
        source: 'NASA POWER Temperature (Tmax/Tmin) + BMD Rajshahi Weather Station Corrections',
        timePeriod: '2001-2025',
        spatialResolution: '0.1 deg (~10 km) Grid Cell',
        measuredOrModeled: 'modeled',
        notesBangla: 'বিএমডি রাজশাহীর ৩০ বছরের চরম তাপমাত্রা রেকর্ডের সাথে ক্যালিব্রেট করা।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    const days = result.metrics.terminalHeatStressDays;
    return {
      banglaBullets: [
        days === 0
          ? `ফসল মার্চ মাসের প্রচণ্ড তাপদাহ আসার আগেই পেকে যায়।`
          : `দেরিতে বোনার ফলে দানা অপুষ্ট থাকার ঝুঁকি বাড়ে (${days} দিন তাপ ঝুঁকি)।`,
      ],
      englishBullets: [
        days === 0
          ? `Harvest completed before peak summer temperatures in March.`
          : `Late sowing increases risk of shriveled grains due to ${days} heat stress days.`,
      ],
    };
  }
}
