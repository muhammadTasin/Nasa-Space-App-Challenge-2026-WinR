import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';

export class SoilDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'soil';
  readonly displayNameBangla = 'মাটি স্বাস্থ্য ও পুষ্টি ভারসাম্য';
  readonly displayNameEnglish = 'Soil Health & Nutrient Depletion';
  readonly version = '1.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const rabiCrop = context.crops.find(c => !c.variety.includes('dhan') || c.cropName.includes('Boro'));
    const isLegume = rabiCrop?.cropName.toLowerCase().includes('lentil') || rabiCrop?.cropName.toLowerCase().includes('masur');
    const isDoubleCereal = rabiCrop?.cropName.toLowerCase().includes('boro');

    // Legumes fix nitrogen and leave positive soil residual health
    // Double cereal (Aman -> Boro) severely depletes soil organic matter and zinc in Barind
    let soilScore = 0.70;
    let banglaSummary = 'মাটির স্বাভাবিক পুষ্টি ভারসাম্য বজায় থাকে।';

    if (isLegume) {
      soilScore = 0.90;
      banglaSummary = 'ডাল জাতীয় ফসল হওয়ায় মাটিতে ১৫-২০ কেজি/হেক্টর প্রাকৃতিক নাইট্রোজেন যুক্ত হবে এবং মাটির স্বাস্থ্য উন্নত হবে।';
    } else if (isDoubleCereal) {
      soilScore = 0.45;
      banglaSummary = 'টানা দুই মৌসুমে ধান চাষে বরেন্দ্র মাটির জৈব পদার্থ দ্রুত হ্রাস পায় এবং দস্তা ও বোরন ঘাটতি দেখা দেয়।';
    }

    return {
      dimensionId: this.id,
      score: soilScore,
      confidence: 'high',
      summaryBangla: banglaSummary,
      summaryEnglish: isLegume
        ? 'Legume crop fixes 15-20 kg N/ha, boosting organic matter and soil microbial activity.'
        : 'Continuous cereal-cereal cropping depletes soil organic matter and micronutrients.',
      metrics: {
        nitrogenFixationKgPerHa: isLegume ? 18 : 0,
        organicMatterTrend: isLegume ? 'positive' : (isDoubleCereal ? 'depleting' : 'neutral'),
        srdiFertilityClass: 'Medium (Talanda Loam)',
      },
      provenance: {
        source: 'SRDI Union Fertilizer Recommendation Card (Talanda, Tanore) + BARI Soil Guide',
        timePeriod: '2020-2025',
        spatialResolution: 'Union level (Talanda)',
        measuredOrModeled: 'measured',
        notesBangla: 'মৃত্তিকা সম্পদ উন্নয়ন ইনস্টিটিউট (SRDI) এর তালন্দ ইউনিয়ন মাটি সার নির্দেশিকা কার্ড।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    const isLegume = result.metrics.nitrogenFixationKgPerHa > 0;
    return {
      banglaBullets: [
        isLegume
          ? 'ডাল ফসল চাষের পর মাটিতে শিকড়ের অবশিষ্টাংশ প্রাকৃতিক ইউরিয়া হিসেবে কাজ করে।'
          : 'পরপর ধান চাষে ইউরিয়া ও অন্যান্য রাসায়নিক সারের খরচ প্রতি বছর বৃদ্ধি পায়।',
        'মাটির উপরিভাগের দোআঁশ স্তরের আর্দ্রতা ধরে রাখার ক্ষমতা বৃদ্ধি পায়।',
      ],
      englishBullets: [
        isLegume
          ? 'Biological nitrogen fixation offsets subsequent chemical fertilizer requirements.'
          : 'Monoculture rice sequences accelerate soil micro-nutrient fatigue.',
      ],
    };
  }
}
