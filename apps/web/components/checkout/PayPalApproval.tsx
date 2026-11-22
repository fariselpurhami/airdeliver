'use client';
import { formatMoney } from '@/lib/commerce';

export function safePayPalApprovalUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port || !['www.paypal.com', 'www.sandbox.paypal.com', 'paypal.com', 'sandbox.paypal.com'].includes(url.hostname)) return null;
    return url.href;
  } catch { return null; }
}

export default function PayPalApproval({ approvalUrl, total, currency, orderId }: { approvalUrl: string; total: number; currency?: string; orderId: number }) {
  const url = safePayPalApprovalUrl(approvalUrl);
  return <section className="w-full h-full overflow-y-auto bg-slate-950 p-6 text-white">
    <h2 className="text-2xl font-semibold mb-4">Pay with PayPal</h2>
    <p className="mb-2">Order #{orderId}</p><p className="text-3xl mb-5">{formatMoney(total, currency)}</p>
    <p className="text-slate-300 mb-6">Review this amount on PayPal. You will return here to finish payment. Approval alone does not confirm your order.</p>
    {url ? <a href={url} className="inline-block rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950">Continue to PayPal</a> : <p role="alert">The payment link could not be verified. Return to your cart and try again.</p>}
  </section>;
}
