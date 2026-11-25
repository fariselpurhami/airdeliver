import { randomId } from '@/lib/random-id';
import { jwtDecode } from 'jwt-decode';

type StorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a],[b]) => a.localeCompare(b)).map(([key,item]) => [key, canonical(item)]));
  return value;
}

const PREFIX = 'airdeliver.checkout.request.v1.';
async function hash(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle?.digest) throw new Error('Checkout needs a secure browser connection. Open localhost on your computer or use HTTPS. No payment request was sent.');
  const bytes = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function getCheckoutRequestKey(token: string, details: Record<string, unknown>, items: { id: unknown; quantity: number; price: unknown }[], storage: StorageLike = localStorage): Promise<string> {
  // This decode is only a storage namespace, never authentication. The API
  // independently verifies the bearer token and binds its principal to the key.
  const subject = jwtDecode<{ sub: string }>(token).sub;
  if (!subject) throw new Error('Checkout requires an authenticated account');
  const fingerprint = await hash(JSON.stringify(canonical({ subject, details, items: items.map(item => ({ id: String(item.id), quantity: item.quantity, price: String(item.price) })).sort((a,b) => a.id.localeCompare(b.id)) })));
  const name = PREFIX + fingerprint;
  const acquire = () => {
    const current = storage.getItem(name);
    if (current && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(current)) return current;
    const key = randomId();
    storage.setItem(name, key);
    return key;
  };
  if (typeof navigator !== 'undefined' && navigator.locks) return navigator.locks.request(name, acquire);
  return acquire();
}

export function retireCheckoutRequestKey(key: string, storage: Storage = localStorage): void {
  for (let i = storage.length - 1; i >= 0; i--) {
    const name = storage.key(i);
    if (name?.startsWith(PREFIX) && storage.getItem(name) === key) storage.removeItem(name);
  }
}
