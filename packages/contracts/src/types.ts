/**
 * Project EDEN — Shared Contracts & Data Types
 * Deterministic crop rotation engine, multi-objective ranking, and anti-hallucination narration.
 */

export type LandType = 'high' | 'medium_high' | 'medium_low' | 'low' | 'very_low';

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'uncertain';

export interface DataProvenance {
  source: string;
  timePeriod: string;
  spatialResolution: string;
  measuredOrModeled: 'measured' | 'modeled' | 'assumed';
  notesBangla?: string;
}

export interface DimensionScoreResult {
  dimensionId: string;
  score: number; // 0.0 to 1.0 (higher = better outcome)
  confidence: ConfidenceLevel;
  summaryBangla: string;
  summaryEnglish: string;
  metrics: Record<string, number | string | boolean>;
  provenance: DataProvenance;
  staleOrMissing?: boolean;
}

export interface EvaluationContext {
  unionId: string;
  upazilaId: string;
  districtId: string;
  landType: LandType;
  seasonYear: number;
  rotationId: string;
  crops: Array<{
    cropName: string;
    variety: string;
    sowingDate: string; // ISO format or relative
    harvestDate: string;
    durationDays: number;
  }>;
  farmerPriorities: Record<string, number>;
}

export interface IEvidenceDimensionPlugin {
  readonly id: string; // 'water' | 'heat' | 'flood' | 'soil' | 'fodder' | 'income'
  readonly displayNameBangla: string;
  readonly displayNameEnglish: string;
  readonly version: string;
  readonly isEnabled: boolean;

  evaluate(context: EvaluationContext): Promise<DimensionScoreResult> | DimensionScoreResult;
  explain(result: DimensionScoreResult): {
    banglaBullets: string[];
    englishBullets: string[];
  };
}

export interface CropPhase {
  crop: string;
  variety: string;
  seasonType: 'Aman' | 'Rabi' | 'Aus' | 'Pre-Kharif';
  sowingWindow: string;
  harvestWindow: string;
  durationDays: number;
  daysToFieldFree: number;
}

export interface MonthTimelineSlot {
  monthNameBangla: string;
  monthNameEnglish: string;
  status: 'occupied' | 'transplanting' | 'harvesting' | 'fallow_available';
  cropName?: string;
}

export interface CandidateRotation {
  id: string;
  nameBangla: string;
  nameEnglish: string;
  isBaseline: boolean;
  cropSequence: CropPhase[];
  scores: Record<string, number>; // Dimension ID -> normalized score (0.0 - 1.0)
  dimensionDetails: Record<string, DimensionScoreResult>;
  totalWeightedScore: number;
  rank: number;
  timeline: MonthTimelineSlot[];
  approvedActionIds: string[];
  approvedActionBangla: string[];
  fieldFreeDateBangla: string; // e.g. "১০ নভেম্বর"
}

export interface AdviceJSON {
  schema_version: '1.0';
  advice_id: string;
  created_at: string;
  scope: {
    union_id: string;
    union_name_bangla: string;
    upazila: string;
    district: string;
    land_type: LandType;
    season: string;
  };
  data_release: string;
  farmer_priorities: Record<string, number>;
  active_plugins: string[];
  options: CandidateRotation[];
  stale_or_missing_inputs: Array<{
    dataset: string;
    issue: string;
    affectedDimension: string;
  }>;
  farmer_summary_bangla: string;
  saao_technical_notes: string;
}

export interface FarmerProfile {
  id: string;
  name: string;
  phone: string;
  unionId: string;
  landType: LandType;
  primaryWaterSource: 'rainfed' | 'shallow_tube_well' | 'deep_tube_well' | 'canal';
  hasLivestock: boolean;
  priorities: {
    water: number;
    income: number;
    soil: number;
    fodder: number;
  };
  keypadSelection?: string; // "1" for water, "2" for income, "3" for soil
  consentGiven: boolean;
}

export interface NarrationAuditLog {
  gate1Passed: boolean;
  gate2Passed: boolean;
  tokenDiffOk: boolean;
  unapprovedNumbersFound: string[];
  unapprovedActionsFound: string[];
  latencyMs: number;
  engineUsed: 'verified_template' | 'local_model_checked' | 'fallback_template';
}

export interface NarrationResult {
  status: 'verified_template' | 'local_model_checked' | 'fallback_template';
  banglaSpeechText: string;
  banglaKeypadPrompt: string;
  durationSecondsEstimate: number;
  auditLog: NarrationAuditLog;
}
