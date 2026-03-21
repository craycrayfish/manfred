import { NextRequest, NextResponse } from 'next/server';
import { updateNode } from '@/lib/notion';
import type { NodePatch } from '@/types';

export const dynamic = 'force-dynamic';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  let body: { patch: NodePatch; lastEdited: string };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { patch, lastEdited } = body;
  if (!patch || !lastEdited) {
    return NextResponse.json({ error: 'patch and lastEdited are required' }, { status: 400 });
  }

  try {
    const result = await updateNode(id, patch, lastEdited);
    if (result.conflict) {
      return NextResponse.json({ error: 'Conflict — node was modified by another user' }, { status: 409 });
    }
    return NextResponse.json({ ok: true });
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
