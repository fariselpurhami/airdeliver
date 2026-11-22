'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { ShippingAddress } from '@/lib/commerce';

export default function ShippingAddressForm({ onSubmit, onBack, initialValue }: {
  onSubmit: (address: ShippingAddress, provider: 'stripe' | 'paypal') => Promise<boolean>;
  onBack: () => void;
  initialValue?: ShippingAddress | null;
}) {
  const [address, setAddress] = useState<ShippingAddress>(initialValue || {
    recipient_name: '', line1: '', line2: '', city: '', region: '', postal_code: '', country: 'US', phone: '',
  });
  const [providers, setProviders] = useState<string[]>([]);
  const [provider, setProvider] = useState<'stripe' | 'paypal'>('stripe');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const busy = useRef(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api.get<{ providers: string[] }>('/ai-ordering/checkout/options').then(({ data }) => {
      if (!active) return;
      const available = data.providers.filter(value => value === 'stripe' || value === 'paypal');
      setProviders(available);
      setProvider(available.includes('stripe') ? 'stripe' : 'paypal');
      if (!available.length) setError('Payment is temporarily unavailable. No charge has been made.');
    }).catch(() => { if (active) setError('Sign in and check your connection to continue checkout.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const fields: { key: keyof ShippingAddress; label: string; autoComplete: string; required?: boolean; type?: string; pattern?: string }[] = [
    { key: 'recipient_name', label: 'Full name', autoComplete: 'shipping name' },
    { key: 'line1', label: 'Street address', autoComplete: 'shipping address-line1' },
    { key: 'line2', label: 'Apartment, suite, etc. (optional)', autoComplete: 'shipping address-line2', required: false },
    { key: 'city', label: 'City', autoComplete: 'shipping address-level2' },
    { key: 'region', label: 'State or territory (two-letter code)', autoComplete: 'shipping address-level1', pattern: '[A-Za-z]{2}' },
    { key: 'postal_code', label: 'ZIP code', autoComplete: 'shipping postal-code', pattern: '[0-9]{5}(-[0-9]{4})?' },
    { key: 'phone', label: 'Delivery phone number', autoComplete: 'shipping tel', type: 'tel' },
  ];
  return (
    <section className="w-full h-full overflow-y-auto p-6 text-white bg-slate-950">
      <h2 className="text-2xl font-semibold mb-2">Delivery details</h2>
      <p className="text-sm text-slate-300 mb-5">Review your address before payment. Your total is checked against the current catalog.</p>
      <form onSubmit={async event => {
        event.preventDefault();
        if (busy.current || !providers.includes(provider)) return;
        busy.current = true;
        setSubmitting(true); setError('');
        try {
          const ok = await onSubmit(address, provider);
          if (!ok) setError('Checkout could not start. Check your details and try again. No charge has been made.');
        } catch { setError('Checkout could not start. Please try again.'); }
        finally { busy.current = false; setSubmitting(false); }
      }} className="grid grid-cols-1 gap-4">
        {fields.map(field => <label key={field.key} className="block text-sm text-slate-200">
          {field.label}
          <input name={field.key} value={address[field.key]} required={field.required !== false} autoComplete={field.autoComplete}
            type={field.type || 'text'} pattern={field.pattern} maxLength={field.key === 'line1' || field.key === 'line2' ? 120 : 100}
            onChange={event => setAddress(previous => ({ ...previous, [field.key]: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400" />
        </label>)}
        <label className="text-sm text-slate-200">Country
          <select name="country" value={address.country} onChange={event => setAddress(previous => ({ ...previous, country: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-3">
            <option value="US">United States</option>
          </select>
        </label>
        <label className="text-sm text-slate-200">Payment method
          <select name="payment_provider" value={provider} onChange={event => setProvider(event.target.value as 'stripe' | 'paypal')} disabled={loading || submitting}
            className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-3">
            {loading ? <option>Loading payment methods...</option> : providers.map(value => <option key={value} value={value}>{value === 'stripe' ? 'Card and available Stripe payment methods' : 'PayPal'}</option>)}
          </select>
        </label>
        {error && <div role="alert" className="rounded-lg border border-red-400 p-3 text-sm text-red-200">{error} <Link href="/login" className="underline">Sign in</Link></div>}
        <p className="text-xs text-slate-400">US shipping only at launch. This form checks address format, not carrier deliverability. No payment details are collected here.</p>
        <button type="submit" disabled={submitting || loading || !providers.length} className="rounded-lg bg-cyan-400 px-4 py-3 font-semibold text-slate-950 disabled:opacity-40">{submitting ? 'Preparing secure payment...' : 'Continue to secure payment'}</button>
        <button type="button" onClick={onBack} disabled={submitting} className="rounded-lg border border-slate-600 px-4 py-3">Back to cart</button>
      </form>
    </section>
  );
}
