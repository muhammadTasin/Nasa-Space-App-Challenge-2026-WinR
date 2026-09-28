/**
 * Replay baseline extracted from 25 seasons of NASA POWER, GPM IMERG, SMAP, and SRDI Talanda soil card.
 * Verified against connect_check.py (seasons 2001-2025).
 */

export interface VarietyReplayRecord {
  variety: string;
  durationDays: number;
  floweringDroughtSeasons: number; // Seasons out of 25 that required rescue irrigation
  totalSeasons: number;
  typicalFieldFreeDate: string; // e.g. "10 Nov"
  waterUseMm: number; // Typical Aman water consumption
}

export interface RabiCropReplayRecord {
  cropName: string;
  variety: string;
  recommendedSowingDeadline: string;
  netIrrigationMm: number;
  heatStressRiskDays: number;
  compatibleWithFieldFreeDate: string; // earliest safe Aman harvest date
  fertilizerNeedKgPerHa: { urea: number; tsp: number; mop: number };
  grossMarginTkPerHa: number;
  fodderValue: 'high' | 'medium' | 'low';
}

export const TANORE_AMAN_REPLAY: Record<string, VarietyReplayRecord> = {
  'BRRI dhan71': {
    variety: 'BRRI dhan71',
    durationDays: 115,
    floweringDroughtSeasons: 6, // 6 of 25 seasons in connect_tanore_aman.csv
    totalSeasons: 25,
    typicalFieldFreeDate: '10 Nov',
    waterUseMm: 420,
  },
  'BRRI dhan87': {
    variety: 'BRRI dhan87',
    durationDays: 127,
    floweringDroughtSeasons: 7, // 7 of 25 seasons
    totalSeasons: 25,
    typicalFieldFreeDate: '15 Nov',
    waterUseMm: 435,
  },
  'BRRI dhan49': {
    variety: 'BRRI dhan49',
    durationDays: 135,
    floweringDroughtSeasons: 9, // 9 of 25 seasons (late flowering in mid-October)
    totalSeasons: 25,
    typicalFieldFreeDate: '20 Nov',
    waterUseMm: 450,
  },
  'Late dhan75': {
    variety: 'Late dhan75',
    durationDays: 115, // Delayed sowing
    floweringDroughtSeasons: 20, // 20 of 25 seasons!
    totalSeasons: 25,
    typicalFieldFreeDate: '05 Dec',
    waterUseMm: 410,
  },
};

export const TANORE_RABI_REPLAY: Record<string, RabiCropReplayRecord> = {
  'BARI Masur-8': {
    cropName: 'Lentil (মসুর)',
    variety: 'BARI Masur-8',
    recommendedSowingDeadline: '15 Nov',
    netIrrigationMm: 198,
    heatStressRiskDays: 0,
    compatibleWithFieldFreeDate: '10 Nov',
    fertilizerNeedKgPerHa: { urea: 45, tsp: 85, mop: 40 },
    grossMarginTkPerHa: 68000,
    fodderValue: 'medium',
  },
  'BARI Sarisha-14': {
    cropName: 'Mustard (সরিষা)',
    variety: 'BARI Sarisha-14',
    recommendedSowingDeadline: '15 Nov',
    netIrrigationMm: 114,
    heatStressRiskDays: 0,
    compatibleWithFieldFreeDate: '10 Nov',
    fertilizerNeedKgPerHa: { urea: 250, tsp: 170, mop: 90 },
    grossMarginTkPerHa: 52000,
    fodderValue: 'low',
  },
  'BARI Gom 33 (Early)': {
    cropName: 'Wheat (গম - আগাম)',
    variety: 'BARI Gom 33',
    recommendedSowingDeadline: '25 Nov',
    netIrrigationMm: 205,
    heatStressRiskDays: 12,
    compatibleWithFieldFreeDate: '20 Nov',
    fertilizerNeedKgPerHa: { urea: 220, tsp: 150, mop: 100 },
    grossMarginTkPerHa: 58000,
    fodderValue: 'high',
  },
  'BARI Gom 33 (Late)': {
    cropName: 'Wheat (গম - নাবি)',
    variety: 'BARI Gom 33',
    recommendedSowingDeadline: '10 Dec',
    netIrrigationMm: 275,
    heatStressRiskDays: 28, // High heat risk at grain filling!
    compatibleWithFieldFreeDate: '05 Dec',
    fertilizerNeedKgPerHa: { urea: 220, tsp: 150, mop: 100 },
    grossMarginTkPerHa: 39000,
    fodderValue: 'high',
  },
  'BRRI dhan28 (Boro)': {
    cropName: 'Boro Rice (বোরো ধান)',
    variety: 'BRRI dhan28',
    recommendedSowingDeadline: '15 Jan',
    netIrrigationMm: 745, // Heavy groundwater extraction
    heatStressRiskDays: 14,
    compatibleWithFieldFreeDate: '15 Dec',
    fertilizerNeedKgPerHa: { urea: 260, tsp: 130, mop: 120 },
    grossMarginTkPerHa: 62000,
    fodderValue: 'high',
  },
};
