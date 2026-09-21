/** The distributions a line is described against. */
import { NextResponse } from 'next/server';
import {
  freshnessPatterns,
  freshnessWeights,
  highNumbers,
  hmcCategoryDistribution,
  oddEvenPatterns,
  spreadDistribution,
  sumDistribution,
  sumDistributions,
  totalDraws,
} from '@/lib/data/distributions';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    totalDraws: totalDraws(),
    oddEven: oddEvenPatterns(),
    sums: sumDistributions(),
    sumStats: sumDistribution(),
    spread: spreadDistribution(),
    highNumbers: highNumbers(),
    freshnessPatterns: freshnessPatterns(),
    freshnessWeights: freshnessWeights(),
    hmc: hmcCategoryDistribution(),
  });
}
