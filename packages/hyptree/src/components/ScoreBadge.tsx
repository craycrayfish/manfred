import type { ConfidenceLevel } from '@/types';

const COLORS: Record<ConfidenceLevel, string> = {
  Untested: 'bg-gray-100 text-gray-500',
  Low: 'bg-red-100 text-red-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  High: 'bg-green-100 text-green-700',
  Validated: 'bg-emerald-100 text-emerald-700 font-semibold',
  Invalidated: 'bg-red-200 text-red-800 font-semibold',
};

export function ScoreBadge({
  confidence,
  score,
}: {
  confidence: ConfidenceLevel;
  score?: number;
}) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${COLORS[confidence]}`}>
      {confidence}
      {score !== undefined && score !== 50 && (
        <span className="opacity-60">({score})</span>
      )}
    </span>
  );
}
