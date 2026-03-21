'use client';

import { useState, useEffect } from 'react';
import type { Evidence, EvidenceDirection, EvidenceStrength, EvidenceSourceType } from '@/types';

const DIRECTION_ICON: Record<EvidenceDirection, string> = {
  Supporting: '↑',
  Contradicting: '↓',
  Neutral: '→',
};

const DIRECTION_COLOR: Record<EvidenceDirection, string> = {
  Supporting: 'text-green-600 bg-green-50',
  Contradicting: 'text-red-600 bg-red-50',
  Neutral: 'text-gray-500 bg-gray-50',
};

const BLANK_FORM: Omit<Evidence, 'id' | 'workflowId'> = {
  name: '',
  notes: '',
  direction: 'Supporting',
  strength: 'Anecdotal',
  source: '',
  sourceType: 'Article',
  dateCollected: new Date().toISOString().slice(0, 10),
  collector: '',
};

interface Props {
  workflowId: string;
}

export function EvidencePanel({ workflowId }: Props) {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...BLANK_FORM });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/evidence/${workflowId}`);
      if (res.ok) setEvidence(await res.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  const handleAdd = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/evidence/${workflowId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setForm({ ...BLANK_FORM });
        setShowForm(false);
        await load();
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">Evidence ({evidence.length})</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          {showForm ? 'Cancel' : '+ Add'}
        </button>
      </div>

      {loading && <p className="text-xs text-gray-400">Loading…</p>}

      <div className="space-y-2">
        {evidence.map((e) => (
          <div key={e.id} className="rounded-lg border bg-white p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium text-gray-800 leading-tight">{e.name}</span>
              <span
                className={`shrink-0 text-xs px-1.5 py-0.5 rounded font-medium ${DIRECTION_COLOR[e.direction]}`}
              >
                {DIRECTION_ICON[e.direction]} {e.direction}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
              <span>{e.strength}</span>
              <span>·</span>
              <span>{e.sourceType}</span>
              {e.dateCollected && (
                <>
                  <span>·</span>
                  <span>{e.dateCollected}</span>
                </>
              )}
            </div>
            {e.notes && <p className="mt-1.5 text-xs text-gray-600 leading-snug">{e.notes}</p>}
            {e.source && (
              <a
                href={e.source}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 text-xs text-blue-500 hover:underline block truncate"
              >
                {e.source}
              </a>
            )}
          </div>
        ))}
        {!loading && evidence.length === 0 && (
          <p className="text-xs text-gray-400 italic">No evidence yet.</p>
        )}
      </div>

      {showForm && (
        <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2 text-sm">
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="Title / summary *"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <textarea
            className="w-full border rounded px-2 py-1 text-sm resize-none"
            rows={2}
            placeholder="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              className="border rounded px-2 py-1 text-sm"
              value={form.direction}
              onChange={(e) => setForm({ ...form, direction: e.target.value as EvidenceDirection })}
            >
              {(['Supporting', 'Neutral', 'Contradicting'] as const).map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
            <select
              className="border rounded px-2 py-1 text-sm"
              value={form.strength}
              onChange={(e) => setForm({ ...form, strength: e.target.value as EvidenceStrength })}
            >
              {(['Anecdotal', 'Qualitative', 'Quantitative', 'Statistical'] as const).map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select
              className="border rounded px-2 py-1 text-sm"
              value={form.sourceType}
              onChange={(e) =>
                setForm({ ...form, sourceType: e.target.value as EvidenceSourceType })
              }
            >
              {(
                ['Interview', 'Survey', 'Article', 'Data', 'Observation', 'Expert Opinion'] as const
              ).map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <input
              type="date"
              className="border rounded px-2 py-1 text-sm"
              value={form.dateCollected}
              onChange={(e) => setForm({ ...form, dateCollected: e.target.value })}
            />
          </div>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="Source URL"
            value={form.source}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
          />
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="Your name"
            value={form.collector}
            onChange={(e) => setForm({ ...form, collector: e.target.value })}
          />
          <button
            onClick={handleAdd}
            disabled={saving || !form.name.trim()}
            className="w-full py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Add Evidence'}
          </button>
        </div>
      )}
    </div>
  );
}
