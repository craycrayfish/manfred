import { NextRequest, NextResponse } from 'next/server';
import { fetchEvidence, createEvidence } from '@/lib/notion';
import type { Evidence } from '@/types';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ workflowId: string }> },
) {
  const { workflowId } = await params;
  try {
    const evidence = await fetchEvidence(workflowId);
    return NextResponse.json(evidence);
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ workflowId: string }> },
) {
  const { workflowId } = await params;
  let body: Omit<Evidence, 'id' | 'workflowId'>;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  try {
    const evidence = await createEvidence({ ...body, workflowId });
    return NextResponse.json(evidence, { status: 201 });
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
