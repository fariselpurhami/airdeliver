// ============================================================================
// FILE: frontend/web/app/(main)/page.tsx
// ============================================================================
import { randomId } from '@/lib/random-id';
import React, { Suspense, experimental_taintUniqueValue } from 'react';
import { headers } from 'next/headers';
import { LandingClient } from './_components/LandingClient';

// Node.js Enterprise Runtime (replaces deprecated Edge runtime)
export const runtime = 'nodejs';
export const preferredRegion = 'auto';

/**
 * STATIC APPLICATION SHELL (PPR COMPLIANT)
 * Invariant: Never read dynamic properties (headers, cookies) inside the static shell.
 */
export default function Page() {
  return (
    <main className="relative min-h-screen w-full bg-[#050505] overflow-x-hidden">
      <Suspense fallback={<StaticAppShell />}>
        <DynamicLandingBoundary />
      </Suspense>
    </main>
  );
}

function StaticAppShell() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black" aria-hidden="true">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
    </div>
  );
}

/**
 * DYNAMIC SUSPENSE BOUNDARY
 * Invariant: Unwraps Next.js 15 Asynchronous Headers inside Suspense to preserve Edge cache.
 */
async function DynamicLandingBoundary() {
  // Next.js 15 headers() returns a Promise and MUST be awaited
  const reqHeaders = await headers();
  const cspNonce = reqHeaders.get('x-nonce') ?? '';
  const traceId = reqHeaders.get('x-trace-id') ?? randomId();

  // Data Access Layer (DAL) Taint Protection
  const internalServerToken = process.env.INTERNAL_ROUTING_TOKEN ?? 'sealed-vault-token';
  experimental_taintUniqueValue(
    'CRITICAL: Internal routing token must never be leaked to client components.',
    process,
    internalServerToken
  );

  return <LandingClient nonce={cspNonce} initialTraceId={traceId} />;
}
