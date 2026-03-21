'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { TreeData, AnyNode } from '@/types';

const TreeCanvas = dynamic(() => import('@/components/TreeCanvas').then((m) => m.TreeCanvas), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-gray-400">
      Loading tree…
    </div>
  ),
});

const NodeDetail = dynamic(() => import('@/components/NodeDetail').then((m) => m.NodeDetail), {
  ssr: false,
});

export default function Page() {
  const [data, setData] = useState<TreeData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<AnyNode | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/tree');
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }, []);

  useEffect(() => {
    load();
    // Poll every 30s to pick up changes from other users / agents
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 bg-white border-b shadow-sm">
        <h1 className="font-semibold text-lg">Hypothesis Tree</h1>
        <button
          onClick={load}
          className="text-sm text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50"
        >
          Refresh
        </button>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Tree canvas */}
        <div className="flex-1 relative">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md text-center">
                <p className="text-red-700 font-medium mb-1">Failed to load tree</p>
                <p className="text-red-500 text-sm mb-3">{error}</p>
                <button
                  onClick={load}
                  className="px-4 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            </div>
          )}
          {!error && data && (
            <TreeCanvas
              data={data}
              selectedId={selected?.id ?? null}
              onSelect={(node) => setSelected(node)}
            />
          )}
          {!error && !data && (
            <div className="flex items-center justify-center h-full text-gray-400">
              Loading…
            </div>
          )}
        </div>

        {/* Side panel */}
        {selected && (
          <NodeDetail
            node={selected}
            onClose={() => setSelected(null)}
            onUpdated={() => {
              load();
              setSelected(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
