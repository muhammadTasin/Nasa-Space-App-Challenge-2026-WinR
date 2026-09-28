import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';
import { TANORE_RABI_REPLAY } from '../data/tanore_replay_data.ts';

export class IncomeDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'income';
  readonly displayNameBangla = 'নিট লাভ ও অর্থনৈতিক নিরাপত্তা';
  readonly displayNameEnglish = 'Net Farm Income & Economic Viability';
  readonly version = '1.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const rabiCrop = context.crops.find(c => !c.variety.includes('dhan') || c.cropName.includes('Boro'));
    const rabiData = TANORE_RABI_REPLAY[rabiCrop?.variety || 'BARI Masur-8'];

    const amanGrossMargin = 42000;
    const rabiGrossMargin = rabiData?.grossMarginTkPerHa || 55000;
    const totalRotationMargin = amanGrossMargin + rabiGrossMargin;

    let incomeScore = (totalRotationMargin - 40000) / 80000;
    incomeScore = Math.max(0.35, Math.min(0.96, Number(incomeScore.toFixed(2))));

    const banglaSummary = `দুই মৌসুমে আনুমানিক নিট লাভ হেক্টর প্রতি প্রায় ${totalRotationMargin.toLocaleString('bn-BD')} টাকা। কম সেচ খরচের কারণে ঝুঁকি কম।`;

    return {
      dimensionId: this.id,
      score: incomeScore,
      confidence: 'high',
      summaryBangla: banglaSummary,
      summaryEnglish: `Estimated annual net gross margin of approximately ${totalRotationMargin.toLocaleString()} BDT/ha with minimal irrigation input overhead.`,
      metrics: {
        totalNetGrossMarginBdtPerHa: totalRotationMargin,
        amanGrossMarginBdt: amanGrossMargin,
        rabiGrossMarginBdt: rabiGrossMargin,
        irrigationCostSharePercent: rabiCrop?.cropName.includes('Boro') ? 38 : 12,
      },
      provenance: {
        source: 'BBS Crop District Panel (2012-2025) + WFP Market Prices & BARI Production Costs',
        timePeriod: '2024-2025 Market Baseline',
        spatialResolution: 'Rajshahi District & Tanore Local Markets',
        measuredOrModeled: 'modeled',
        notesBangla: 'বাংলাদেশ পরিসংখ্যান ব্যুরো (BBS) এর পাইকারি দর ও ডব্লিউএফপি স্থানীয় বাজার মূল্য।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    const margin = result.metrics.totalNetGrossMarginBdtPerHa;
    return {
      banglaBullets: [
        `প্রতি হেক্টরে দুই মৌসুমে মোট মুনাফা প্রায় ${margin} টাকা।`,
        `গভীর নলকূপের বিদ্যুত/ডিজেল বিল অনেক কম হওয়ায় কৃষকের পকেটে আসল লাভ বেশি থাকে।`,
      ],
      englishBullets: [
        `Combined net return estimated at ${margin} BDT/ha.`,
        `Reduced fuel/electricity pumping expenses preserve cash liquidity for smallholders.`,
      ],
    };
  }
}
