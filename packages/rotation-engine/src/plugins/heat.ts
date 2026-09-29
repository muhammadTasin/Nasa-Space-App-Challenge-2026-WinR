import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';
import { amanOf, rabiOf, clampScore } from '../data/lookup.ts';
import { bnDate, bnDigits, enDate } from '../bn.ts';

export class HeatDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'heat';
  readonly displayNameBangla = 'তাপমাত্রার সহনশীলতা';
  readonly displayNameEnglish = 'Heat Stress at Sensitive Stages';
  readonly version = '2.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const { record: aman } = amanOf(context);
    const { record: rabi, catalog: rabiName } = rabiOf(context);
    const heat = rabi.heat;

    // Score = share of the sensitive stage that stays below the crop's heat threshold.
    const hotShare = heat ? heat.hotDays / heat.windowDays : 0;
    const heatScore = clampScore(1 - hotShare, 0.1, 0.95);

    const summaryBangla = heat
      ? `${heat.stageBangla} ${bnDigits(heat.windowDays)} দিনের মধ্যে প্রায় ${bnDigits(heat.hotDays)} দিন তাপমাত্রা ${bnDigits(heat.thresholdC)}°C ছাড়ায় (২৫ মৌসুমের মধ্যমা)।`
      : `${rabiName.cropBangla} ~${bnDate(rabi.harvest)} কাটা হয়, মার্চ-এপ্রিলের গরমের আগেই।`;
    const summaryEnglish = heat
      ? `About ${heat.hotDays} of ${heat.windowDays} days above ${heat.thresholdC} C at ${heat.stage} (median of 25 seasons).`
      : `${rabiName.crop} is harvested around ${enDate(rabi.harvest)}, before the March-April heat.`;

    return {
      dimensionId: this.id,
      score: heatScore,
      confidence: 'medium',
      summaryBangla,
      summaryEnglish,
      metrics: {
        hotDays: heat?.hotDays ?? 0,
        sensitiveWindowDays: heat?.windowDays ?? 0,
        thresholdC: heat?.thresholdC ?? 0,
        sensitiveStage: heat?.stage ?? 'none before harvest',
        amanFloweringNightTempC: aman.floweringNightTempC ?? 'not computed',
      },
      provenance: {
        source: 'NASA POWER daily Tmax, bias-corrected by month against BMD station 41895 Shah Mokhdum (NOAA GSOD); research/explore/heat_windows.py',
        timePeriod: '2001-2025',
        spatialResolution: 'POWER 0.5° x 0.625° cell at the Tanore pilot point',
        measuredOrModeled: 'modeled',
        notesBangla: 'বোরোতে ফুল আসার ১৫ দিনে ৩৫°C এর বেশি, গমে দানা পুষ্ট হওয়ার শেষ ৩০ দিনে ৩০°C এর বেশি দিন গোনা হয়েছে।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    const m = result.metrics;
    const hot = m.hotDays as number;
    return {
      banglaBullets: [
        hot === 0
          ? 'সংবেদনশীল পর্যায় গরম শুরুর আগেই শেষ হয়।'
          : `সংবেদনশীল ${bnDigits(m.sensitiveWindowDays as number)} দিনের ${bnDigits(hot)} দিন অতিরিক্ত গরম।`,
      ],
      englishBullets: [
        hot === 0
          ? 'The sensitive stage ends before the heat arrives.'
          : `${hot} of ${m.sensitiveWindowDays} sensitive days above ${m.thresholdC} C.`,
      ],
    };
  }
}
