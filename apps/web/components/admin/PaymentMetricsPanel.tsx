'use client';
import React from 'react';
export type MetricRange = '1H' | '24H' | '7D' | '30D';
export interface PaymentMetrics {
  generated_at: string; from_at: string; to_at: string; timezone: 'UTC';
  definition: 'recorded_paid_order_gross'; complete: boolean;
  currencies: { currency: string; amount: string; order_count: number; buckets: { starts_at: string; amount: string; order_count: number }[] }[];
  paid_without_timestamp: number; paid_invalid_amount_or_currency: number;
}
export function formatRecordedAmount(amount: string | number, currency: string): string {
  const value = Number(amount);
  if (!Number.isFinite(value) || !/^[A-Z]{3}$/.test(currency)) return 'Amount unavailable';
  // Keep the currency code visible even where symbols are ambiguous.
  return `${currency} ${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(value)}`;
}
export default function PaymentMetricsPanel({ data, loading, error, range, onRange, onRetry }: {
  data?: PaymentMetrics; loading: boolean; error: boolean; range: MetricRange;
  onRange: (value: MetricRange) => void; onRetry: () => void;
}) {
  const valid = data && data.definition === 'recorded_paid_order_gross' && data.complete === true && data.timezone === 'UTC' && [data.generated_at,data.from_at,data.to_at,...data.currencies.flatMap(c => c.buckets.map(b => b.starts_at))].every(t => Number.isFinite(Date.parse(t)));
  const age = data ? Date.now() - Date.parse(data.generated_at) : NaN;
  const stale = !Number.isFinite(age) || age > 120000 || age < -60000;
  return <section aria-label="Recorded payments" className="rounded-[32px] bg-black/40 border border-white/10 p-6 md:p-8 text-white">
    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
      <div><h2 className="text-xl font-bold">Recorded payments</h2><p className="mt-2 text-sm text-slate-400 max-w-2xl">Paid order totals by currency. Not settled funds, net revenue or refunds.</p></div>
      <div aria-label="Payment time range" className="flex flex-wrap gap-2">{(['1H','24H','7D','30D'] as MetricRange[]).map(value => <button key={value} type="button" aria-pressed={range === value} onClick={() => onRange(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${range === value ? 'bg-cyan-400 text-black' : 'bg-white/5 text-slate-300'}`}>{value}</button>)}</div>
    </div>
    {loading && !data ? <p role="status" className="mt-6 text-slate-300">Checking recorded payments...</p> : null}
    {error || (data && !valid) ? <div role="alert" className="mt-6 rounded-xl bg-amber-400/10 p-4 text-sm text-amber-100"><p>Payment metrics couldn't be refreshed. Don't use this view to confirm a payment or settlement.</p><button type="button" onClick={onRetry} className="mt-3 underline">Try again</button></div> : null}
    {valid ? <>
      <p className="mt-5 text-xs text-slate-400">UTC window: {new Date(data.from_at).toISOString().slice(0,16).replace('T',' ')} to {new Date(data.to_at).toISOString().slice(0,16).replace('T',' ')}. {error || stale ? 'Snapshot may be out of date.' : 'Snapshot, not a live payment feed.'}</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.currencies.map(group => <article key={group.currency} className="min-w-0 rounded-2xl bg-white/[0.03] border border-white/10 p-5">
        <p className="text-xs font-semibold text-cyan-300">{group.currency}</p><p className="mt-2 break-words text-2xl font-bold">{formatRecordedAmount(group.amount, group.currency)}</p>
        <p className="mt-1 text-sm text-slate-400">{group.order_count} paid {group.order_count === 1 ? 'order' : 'orders'} in this window</p>
        <details className="mt-4 text-sm"><summary className="cursor-pointer text-slate-300">View UTC time buckets</summary><ul className="mt-3 max-h-56 overflow-auto space-y-2">{group.buckets.map(bucket => <li key={bucket.starts_at} className="flex flex-wrap justify-between gap-2 text-xs text-slate-400"><span>{new Date(bucket.starts_at).toISOString().slice(0,16).replace('T',' ')}</span><span>{formatRecordedAmount(bucket.amount, group.currency)} · {bucket.order_count}</span></li>)}</ul></details>
      </article>)}</div>
      {data.currencies.length === 0 ? <p className="mt-6 text-slate-300">{error || stale ? 'The last successful snapshot had no timestamped paid orders in this window. Current payment data could not be confirmed.' : 'No timestamped paid orders in this window. This does not prove no payments occurred.'}</p> : null}
      {(data.paid_without_timestamp > 0 || data.paid_invalid_amount_or_currency > 0) ? <p className="mt-5 text-sm text-amber-200">Excluded from totals: {data.paid_without_timestamp} paid records without a payment timestamp (all time), {data.paid_invalid_amount_or_currency} records outside supported amount or currency limits in this window.</p> : null}
      <p className="mt-5 text-xs text-slate-500">Historical order amounts used float storage. These grouped records are not a financial statement.</p>
    </> : null}
  </section>;
}
