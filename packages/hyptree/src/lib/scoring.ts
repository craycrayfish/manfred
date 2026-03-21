import type { Evidence, ConfidenceLevel } from '../types';

const STRENGTH_WEIGHT: Record<Evidence['strength'], number> = {
  Anecdotal: 1,
  Qualitative: 2,
  Quantitative: 3,
  Statistical: 4,
};

const DIRECTION_SIGN: Record<Evidence['direction'], number> = {
  Supporting: 1,
  Neutral: 0,
  Contradicting: -1,
};

/**
 * Returns a 0–100 score where 50 = neutral/no evidence,
 * >50 = net supporting, <50 = net contradicting.
 */
export function scoreWorkflow(evidence: Evidence[]): number {
  if (evidence.length === 0) return 50;

  let weightedSum = 0;
  let totalWeight = 0;

  for (const e of evidence) {
    const weight = STRENGTH_WEIGHT[e.strength] ?? 1;
    const sign = DIRECTION_SIGN[e.direction] ?? 0;
    weightedSum += weight * sign;
    totalWeight += weight;
  }

  if (totalWeight === 0) return 50;

  // Maps [-1, 1] → [0, 100]
  const normalized = (weightedSum / totalWeight + 1) / 2;
  return Math.round(normalized * 100);
}

export function confidenceFromScore(score: number, hasEvidence: boolean): ConfidenceLevel {
  if (!hasEvidence) return 'Untested';
  if (score < 20) return 'Invalidated';
  if (score < 40) return 'Low';
  if (score < 60) return 'Medium';
  if (score < 80) return 'High';
  return 'Validated';
}
