'use client';

import { useState, useEffect } from 'react';
import type { AnyNode, Workflow, NodePatch } from '@/types';
import { ScoreBadge } from './ScoreBadge';
import { EvidencePanel } from './EvidencePanel';

interface Props {
  node: AnyNode;
  onClose: () => void;
  onUpdated: () => void;
}

const VERTICAL_STATUSES = ['Active', 'Parked', 'Killed'] as const;
const MARKET_STATUSES = ['Exploring', 'Validated', 'Invalidated', 'Parked'] as const;
const USE_CASE_STATUSES = ['Exploring', 'Validated', 'Invalidated', 'Parked'] as const;
const WORKFLOW_STATUSES = ['Open', 'Testing', 'Validated', 'Invalidated'] as const;
const WORKFLOW_TYPES = ['Desirability', 'Feasibility', 'Viability'] as const;
const CONFIDENCE_LEVELS = ['Untested', 'Low', 'Medium', 'High', 'Validated', 'Invalidated'] as const;

const NODE_LABEL: Record<AnyNode['nodeType'], string> = {
  vertical: 'Vertical',
  market: 'Market',
  useCase: 'Use Case',
  workflow: 'Workflow',
};

const NODE_COLOR: Record<AnyNode['nodeType'], string> = {
  vertical: 'text-blue-700 bg-blue-50 border-blue-200',
  market: 'text-green-700 bg-green-50 border-green-200',
  useCase: 'text-violet-700 bg-violet-50 border-violet-200',
  workflow: 'text-orange-700 bg-orange-50 border-orange-200',
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-500 mb-1 uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  multiline,
}: {
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
}) {
  const cls =
    'w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white';
  return multiline ? (
    <textarea
      className={`${cls} resize-none`}
      rows={3}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ) : (
    <input className={cls} value={value} onChange={(e) => onChange(e.target.value)} />
  );
}

function SelectInput({
  value,
  options,
  onChange,
}: {
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o} value={o}>{o === '' ? '— not set —' : o}</option>
      ))}
    </select>
  );
}

const RATING_ACTIVE: Record<string, string> = {
  '1': 'bg-red-500 text-white border-red-500',
  '2': 'bg-orange-400 text-white border-orange-400',
  '3': 'bg-amber-400 text-white border-amber-400',
  '4': 'bg-lime-500 text-white border-lime-500',
  '5': 'bg-green-500 text-white border-green-500',
};

function RatingButtons({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-1.5">
      {(['1', '2', '3', '4', '5'] as const).map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(value === n ? '' : n)}
          className={`w-10 h-10 rounded text-sm font-semibold border-2 transition-colors
            ${value === n
              ? RATING_ACTIVE[n]
              : 'bg-white text-gray-400 border-gray-200 hover:border-gray-400 hover:text-gray-600'
            }`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

export function NodeDetail({ node, onClose, onUpdated }: Props) {
  const [form, setForm] = useState<NodePatch>({});
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setForm({
      name: node.name,
      description: node.description,
      status: node.status,
      marketNeed: node.marketNeed,
      willingnessToPay: node.willingnessToPay,
      technicalFeasibility: node.technicalFeasibility,
      regulatoryFeasibility: node.regulatoryFeasibility,
      easeOfEntry: node.easeOfEntry,
      currentDeployments: node.currentDeployments,
      alternativeSolutions: node.alternativeSolutions,
      ...(node.nodeType === 'market' ? { tam: node.tam ?? undefined } : {}),
      ...(node.nodeType === 'workflow'
        ? { type: node.type, confidence: node.confidence, score: node.score }
        : {}),
    });
    setConflict(false);
    setError(null);
  }, [node.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (key: keyof NodePatch) => (v: string | number | null) =>
    setForm((f) => ({ ...f, [key]: v }));

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/node/${node.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patch: form, lastEdited: node.lastEdited }),
      });
      if (res.status === 409) {
        setConflict(true);
      } else if (res.ok) {
        onUpdated();
      } else {
        const body = await res.json();
        setError(body.error ?? 'Save failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const statuses =
    node.nodeType === 'vertical'
      ? VERTICAL_STATUSES
      : node.nodeType === 'market'
        ? MARKET_STATUSES
        : node.nodeType === 'useCase'
          ? USE_CASE_STATUSES
          : WORKFLOW_STATUSES;

  return (
    <div className="w-80 flex flex-col bg-white border-l shadow-xl overflow-hidden">
      {/* Header */}
      <div
        className={`px-4 py-3 border-b flex items-center justify-between ${NODE_COLOR[node.nodeType]}`}
      >
        <span className="text-xs font-semibold uppercase tracking-widest">
          {NODE_LABEL[node.nodeType]}
        </span>
        <button onClick={onClose} className="text-lg leading-none opacity-50 hover:opacity-100">
          ×
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {conflict && (
          <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
            This node was modified by someone else. Refresh to see the latest before editing.
          </div>
        )}
        {error && (
          <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            {error}
          </div>
        )}

        <Field label="Name">
          <TextInput value={form.name ?? ''} onChange={set('name')} />
        </Field>

        <Field label="Description">
          <TextInput value={form.description ?? ''} onChange={set('description')} multiline />
        </Field>

        <Field label="Status">
          <SelectInput value={form.status ?? ''} options={statuses} onChange={set('status')} />
        </Field>

        {node.nodeType === 'market' && (
          <Field label="TAM ($M)">
            <input
              type="number"
              className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
              value={form.tam ?? ''}
              onChange={(e) =>
                set('tam')(e.target.value === '' ? null : Number(e.target.value))
              }
            />
          </Field>
        )}

        {node.nodeType === 'workflow' && (
          <>
            <Field label="Type">
              <SelectInput
                value={form.type ?? ''}
                options={WORKFLOW_TYPES}
                onChange={set('type')}
              />
            </Field>
            <Field label="Confidence">
              <div className="flex items-center gap-2">
                <SelectInput
                  value={form.confidence ?? ''}
                  options={CONFIDENCE_LEVELS}
                  onChange={set('confidence')}
                />
                <ScoreBadge
                  confidence={(form.confidence ?? 'Untested') as Workflow['confidence']}
                />
              </div>
            </Field>
            <Field label="Score (0–100)">
              <input
                type="number"
                min={0}
                max={100}
                className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
                value={form.score ?? 50}
                onChange={(e) => set('score')(Number(e.target.value))}
              />
            </Field>
          </>
        )}

        <div className="mt-2 pt-2 border-t">
          <p className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">Assessment</p>

          <Field label="Technical Feasibility">
            <RatingButtons value={form.technicalFeasibility ?? ''} onChange={set('technicalFeasibility')} />
          </Field>

          <Field label="Regulatory Feasibility">
            <RatingButtons value={form.regulatoryFeasibility ?? ''} onChange={set('regulatoryFeasibility')} />
          </Field>

          <Field label="Market Need">
            <RatingButtons value={form.marketNeed ?? ''} onChange={set('marketNeed')} />
          </Field>

          <Field label="Willingness to Pay">
            <RatingButtons value={form.willingnessToPay ?? ''} onChange={set('willingnessToPay')} />
          </Field>

          <Field label="Ease of Entry">
            <RatingButtons value={form.easeOfEntry ?? ''} onChange={set('easeOfEntry')} />
          </Field>

          <Field label="Current Deployments">
            <TextInput value={form.currentDeployments ?? ''} onChange={set('currentDeployments')} multiline />
          </Field>

          <Field label="Alternative Solutions">
            <TextInput value={form.alternativeSolutions ?? ''} onChange={set('alternativeSolutions')} multiline />
          </Field>
        </div>

        <div className="mt-2 pt-2 border-t text-xs text-gray-400">
          Last edited: {new Date(node.lastEdited).toLocaleString()}
        </div>

        {node.nodeType === 'workflow' && <EvidencePanel workflowId={node.id} />}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t bg-gray-50 flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={onClose}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
