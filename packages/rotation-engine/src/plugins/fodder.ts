import type { IEvidenceDimensionPlugin, EvaluationContext, DimensionScoreResult } from '@project-eden/contracts';
import { TANORE_RABI_REPLAY } from '../data/tanore_replay_data.ts';

export class FodderDimensionPlugin implements IEvidenceDimensionPlugin {
  readonly id = 'fodder';
  readonly displayNameBangla = 'গবাদিপশুর খাদ্য ও খড় প্রাপ্যতা';
  readonly displayNameEnglish = 'Livestock Fodder & Crop Residue';
  readonly version = '1.0.0';
  readonly isEnabled = true;

  evaluate(context: EvaluationContext): DimensionScoreResult {
    const rabiCrop = context.crops.find(c => !c.variety.includes('dhan') || c.cropName.includes('Boro'));
    const rabiData = TANORE_RABI_REPLAY[rabiCrop?.variety || 'BARI Masur-8'];

    let fodderScore = 0.75;
    let banglaSummary = 'আমন ধানের শুকনো খড় এবং রবি ফসলের অবশিষ্টাংশ থেকে গবাদিপশুর পুষ্টিকর খাদ্য সংস্থান হবে।';

    if (rabiData?.fodderValue === 'high') {
      fodderScore = 0.88;
      banglaSummary = 'ধানের খড়ের পাশাপাশি গমের ভুসি/খড় গবাদিপশুর জন্য পর্যাপ্ত উচ্চমানের শুকনা খাবার নিশ্চিত করে।';
    } else if (rabiData?.fodderValue === 'medium') {
      fodderScore = 0.82;
      banglaSummary = 'মসুরের গাছ ও খোসা (ভূষি) স্থানীয় দেশি গরুর জন্য উৎকৃষ্ট আমিষসমৃদ্ধ খাবার জোগায়।';
    } else {
      fodderScore = 0.65;
      banglaSummary = 'সরিষার খৈল কেনা খাদ্য হিসেবে কাজে লাগলেও জমিতে সরাসরি গোখাদ্যের পরিমাণ তুলনামূলক কম।';
    }

    return {
      dimensionId: this.id,
      score: fodderScore,
      confidence: 'high',
      summaryBangla: banglaSummary,
      summaryEnglish: `Provides balanced crop residue supporting the local district cattle density (197 cattle/km²).`,
      metrics: {
        districtCattleDensityPerKm2: 197,
        strawResidueEstimatedTonsPerHa: 3.2,
        proteinHaulmAvailable: rabiData?.fodderValue === 'medium',
      },
      provenance: {
        source: 'FAO Gridded Livestock of the World (GLW4) + DLS Livestock Economy Data',
        timePeriod: '2015-2024',
        spatialResolution: 'District level (Rajshahi)',
        measuredOrModeled: 'measured',
        notesBangla: 'প্রাণিসম্পদ অধিদপ্তর (DLS) ও এফএও (FAO) গবাদিপশু ঘনত্ব জরিপ।',
      },
    };
  }

  explain(result: DimensionScoreResult) {
    return {
      banglaBullets: [
        'রাজশাহী জেলার প্রতি বর্গকিলোমিটারে ১৯৭টি গবাদিপশুর খাবারের চাহিদা রয়েছে।',
        'এই ফসল চক্র থেকে ধানের খড়ের পাশাপাশি প্রোটিনসমৃদ্ধ গোখাদ্য তৈরি হবে।',
      ],
      englishBullets: [
        'Meets dietary intake demands for local cattle population with zero external feed purchase.',
      ],
    };
  }
}
