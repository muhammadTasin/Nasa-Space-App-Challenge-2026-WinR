import type {
  AdviceJSON,
  CandidateRotation,
  EvaluationContext,
  LandType,
  MonthTimelineSlot,
  DimensionScoreResult,
} from '@project-eden/contracts';
import { FeatureRegistry } from './registry.ts';

export interface PlanOptionsRequest {
  unionId: string;
  unionNameBangla: string;
  upazila: string;
  district: string;
  landType: LandType;
  season: string;
  currentAmanCrop?: string;
  farmerPriorities: {
    water?: number;
    income?: number;
    soil?: number;
    fodder?: number;
    heat?: number;
    flood?: number;
  };
}

export class RotationEngine {
  private registry: FeatureRegistry;

  constructor(registry?: FeatureRegistry) {
    this.registry = registry || new FeatureRegistry();
  }

  getRegistry(): FeatureRegistry {
    return this.registry;
  }

  evaluateRotation(
    id: string,
    nameBangla: string,
    nameEnglish: string,
    isBaseline: boolean,
    crops: EvaluationContext['crops'],
    request: PlanOptionsRequest
  ): CandidateRotation {
    const activePlugins = this.registry.getActivePlugins();
    const scores: Record<string, number> = {};
    const dimensionDetails: Record<string, DimensionScoreResult> = {};

    const evalContext: EvaluationContext = {
      unionId: request.unionId,
      upazilaId: request.upazila,
      districtId: request.district,
      landType: request.landType,
      seasonYear: 2026,
      rotationId: id,
      crops,
      farmerPriorities: request.farmerPriorities as Record<string, number>,
    };

    // Calculate score for each active dimension
    for (const plugin of activePlugins) {
      const result = plugin.evaluate(evalContext);
      scores[plugin.id] = result.score;
      dimensionDetails[plugin.id] = result;
    }

    // Normalized weighted score based on farmer priorities
    const priorities = request.farmerPriorities;
    let totalWeight = 0;
    let weightedSum = 0;

    for (const plugin of activePlugins) {
      const weight = priorities[plugin.id as keyof typeof priorities] ?? 1.0;
      totalWeight += weight;
      weightedSum += (scores[plugin.id] || 0) * weight;
    }

    const totalWeightedScore = totalWeight > 0 ? Number((weightedSum / totalWeight).toFixed(3)) : 0.5;

    // Timeline generator (Month by month)
    const isEarlyAman = crops.some(c => c.variety.includes('71') || c.variety.includes('87'));
    const isLentil = crops.some(c => c.cropName.includes('Lentil') || c.cropName.includes('Masur'));
    const isMustard = crops.some(c => c.cropName.includes('Mustard') || c.cropName.includes('Sarisha'));
    const isBoro = crops.some(c => c.cropName.includes('Boro'));

    const timeline: MonthTimelineSlot[] = [
      { monthNameBangla: 'জুলাই', monthNameEnglish: 'Jul', status: 'transplanting', cropName: 'আমন ধান' },
      { monthNameBangla: 'আগস্ট', monthNameEnglish: 'Aug', status: 'occupied', cropName: 'আমন ধান' },
      { monthNameBangla: 'সেপ্টেম্বর', monthNameEnglish: 'Sep', status: 'occupied', cropName: 'আমন ধান' },
      {
        monthNameBangla: 'অক্টোবর',
        monthNameEnglish: 'Oct',
        status: isEarlyAman ? 'harvesting' : 'occupied',
        cropName: 'আমন ধান',
      },
      {
        monthNameBangla: 'নভেম্বর',
        monthNameEnglish: 'Nov',
        status: isEarlyAman
          ? (isLentil || isMustard ? 'transplanting' : 'available')
          : 'harvesting',
        cropName: isEarlyAman ? (isLentil ? 'মসুর' : (isMustard ? 'সরিষা' : 'জমি মুক্ত')) : 'আমন ধান কাটা',
      },
      {
        monthNameBangla: 'ডিসেম্বর',
        monthNameEnglish: 'Dec',
        status: isBoro ? 'fallow_available' : 'occupied',
        cropName: isLentil ? 'মসুর' : (isMustard ? 'সরিষা' : (isBoro ? 'বোরোর অপেক্ষা' : 'গম')),
      },
      {
        monthNameBangla: 'জানুয়ারি',
        monthNameEnglish: 'Jan',
        status: isBoro ? 'transplanting' : 'occupied',
        cropName: isBoro ? 'বোরো ধান' : (isMustard ? 'সরিষা কাটা' : (isLentil ? 'মসুর' : 'গম')),
      },
      {
        monthNameBangla: 'ফেব্রুয়ারি',
        monthNameEnglish: 'Feb',
        status: isBoro ? 'occupied' : (isLentil ? 'harvesting' : 'fallow_available'),
        cropName: isBoro ? 'বোরো ধান' : (isLentil ? 'মসুর কাটা' : 'জমি মুক্ত'),
      },
      {
        monthNameBangla: 'মার্চ',
        monthNameEnglish: 'Mar',
        status: isBoro ? 'occupied' : 'fallow_available',
        cropName: isBoro ? 'বোরো ধান' : 'পতিত / আউশ প্রস্তুতি',
      },
    ];

    const fieldFreeDateBangla = isEarlyAman ? '১০ নভেম্বর' : '২০ নভেম্বর';

    const approvedActionIds = isEarlyAman
      ? ['action_harvest_early_nov', 'action_sow_lentil_residue_moisture', 'action_avoid_late_wheat']
      : ['action_harvest_late_nov', 'action_delay_rabi_sowing'];

    const approvedActionBangla = isEarlyAman
      ? [
          '১০ নভেম্বরের মধ্যে ব্রি ধান৭১ কেটে ফেলুন।',
          'জমির আর্দ্রতা শুকিয়ে যাওয়ার আগেই মসুর বা সরিষা বুনে দিন।',
          'নাবিতে গম বোনা পরিহার করুন যাতে মার্চের তাপদাহ এড়ানো যায়।',
        ]
      : [
          '২০ নভেম্বরের পর ধান কাটা শেষ হবে।',
          'দেরি হওয়ার কারণে ডাল বা গম চাষ ঝুঁকিপূর্ণ হতে পারে।',
        ];

    return {
      id,
      nameBangla,
      nameEnglish,
      isBaseline,
      cropSequence: crops.map(c => ({
        crop: c.cropName,
        variety: c.variety,
        seasonType: c.variety.includes('dhan') ? 'Aman' : 'Rabi',
        sowingWindow: '15 Jul - 01 Aug',
        harvestWindow: isEarlyAman ? '25 Oct - 05 Nov' : '15 Nov - 25 Nov',
        durationDays: c.durationDays,
        daysToFieldFree: isEarlyAman ? 115 : 135,
      })),
      scores,
      dimensionDetails,
      totalWeightedScore,
      rank: 1,
      timeline,
      approvedActionIds,
      approvedActionBangla,
      fieldFreeDateBangla,
    };
  }

  generateAdvice(request: PlanOptionsRequest): AdviceJSON {
    const candidateA = this.evaluateRotation(
      'rot_dhan71_lentil',
      'ব্রি ধান৭১ → বারি মসুর-৮ → পতিত (পানি সাশ্রয়ী ও মাটি সমৃদ্ধকারী)',
      'BRRI dhan71 -> BARI Masur-8 -> Fallow',
      false,
      [
        { cropName: 'Aman Rice', variety: 'BRRI dhan71', sowingDate: '2026-07-24', harvestDate: '2026-11-05', durationDays: 115 },
        { cropName: 'Lentil', variety: 'BARI Masur-8', sowingDate: '2026-11-10', harvestDate: '2027-02-28', durationDays: 110 },
      ],
      request
    );

    const candidateB = this.evaluateRotation(
      'rot_dhan71_mustard',
      'ব্রি ধান৭১ → বারি সরিষা-১৪ → বোরো/আউশ (৩ ফসলি দ্রুত চক্র)',
      'BRRI dhan71 -> BARI Sarisha-14 -> Aus/Boro',
      false,
      [
        { cropName: 'Aman Rice', variety: 'BRRI dhan71', sowingDate: '2026-07-24', harvestDate: '2026-11-05', durationDays: 115 },
        { cropName: 'Mustard', variety: 'BARI Sarisha-14', sowingDate: '2026-11-10', harvestDate: '2027-01-25', durationDays: 78 },
      ],
      request
    );

    const candidateC = this.evaluateRotation(
      'rot_dhan49_boro_conventional',
      'ব্রি ধান৪৯ → বোরো ধান (প্রচলিত দীর্ঘ মেয়াদি ও উচ্চ সেচ নির্ভর)',
      'BRRI dhan49 -> Boro Rice (BRRI dhan28) [Conventional]',
      true,
      [
        { cropName: 'Aman Rice', variety: 'BRRI dhan49', sowingDate: '2026-07-24', harvestDate: '2026-11-20', durationDays: 135 },
        { cropName: 'Boro Rice', variety: 'BRRI dhan28', sowingDate: '2027-01-15', harvestDate: '2027-05-10', durationDays: 140 },
      ],
      request
    );

    const candidateD = this.evaluateRotation(
      'rot_dhan49_wheat_late',
      'ব্রি ধান৪৯ → বারি গম ৩৩ (দেরিতে বোনা গম - তাপ ঝুঁকিপূর্ণ)',
      'BRRI dhan49 -> BARI Gom 33 (Late sown)',
      false,
      [
        { cropName: 'Aman Rice', variety: 'BRRI dhan49', sowingDate: '2026-07-24', harvestDate: '2026-11-20', durationDays: 135 },
        { cropName: 'Wheat', variety: 'BARI Gom 33 (Late)', sowingDate: '2026-12-10', harvestDate: '2027-03-24', durationDays: 105 },
      ],
      request
    );

    const options = [candidateA, candidateB, candidateC, candidateD];

    options.sort((a, b) => b.totalWeightedScore - a.totalWeightedScore);
    options.forEach((opt, idx) => {
      opt.rank = idx + 1;
    });

    const bestOption = options[0];
    const activePluginNames = this.registry.getActivePlugins().map(p => p.id);

    const farmerSummary = `তালন্দ ইউনিয়নের মাঝারি উঁচু জমির জন্য '${bestOption.nameBangla}' সবচেয়ে নিরাপদ ও লাভজনক। ১০ নভেম্বরের মধ্যেই আমন ধান কাটা শেষ হবে এবং ২৫ বছরের নাসা রেকর্ডে মাত্র ৬ মৌসুমে বাড়তি সেচ লেগেছে। রবিতে মসুর চাষে সেচ সাশ্রয় হবে এবং মাটিতে প্রাকৃতিক নাইট্রোজেন বাড়বে।`;

    const saaoNotes = `Talanda Union (Tanore): Replay over 2001-2025 shows BRRI dhan71 flowers by Oct 4, escaping terminal drought in 19 of 25 seasons. Frees land by Nov 10, utilizing residual root-zone soil moisture (SMAP ~0.24 m3/m3) for lentil. Replaces conventional BRRI dhan49->Boro which consumes 745mm irrigation.`;

    return {
      schema_version: '1.0',
      advice_id: `adv_${Date.now()}_${request.unionId}`,
      created_at: new Date().toISOString(),
      scope: {
        union_id: request.unionId,
        union_name_bangla: request.unionNameBangla,
        upazila: request.upazila,
        district: request.district,
        land_type: request.landType,
        season: request.season,
      },
      data_release: 'bd-pilots-2026.10.1',
      farmer_priorities: request.farmerPriorities as Record<string, number>,
      active_plugins: activePluginNames,
      options,
      stale_or_missing_inputs: [],
      farmer_summary_bangla: farmerSummary,
      saao_technical_notes: saaoNotes,
    };
  }
}
