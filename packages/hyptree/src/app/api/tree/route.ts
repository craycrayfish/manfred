import { NextResponse } from 'next/server';
import { fetchVerticals, fetchMarkets, fetchUseCases, fetchWorkflows } from '@/lib/notion';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const [verticals, markets, useCases, workflows] = await Promise.all([
      fetchVerticals(),
      fetchMarkets(),
      fetchUseCases(),
      fetchWorkflows(),
    ]);
    return NextResponse.json({ verticals, markets, useCases, workflows });
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
