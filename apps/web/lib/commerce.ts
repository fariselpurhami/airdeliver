export const DEFAULT_LOCALE = 'en-US';
export const DEFAULT_CURRENCY = 'USD';

export type ShippingAddress = {
  recipient_name: string;
  line1: string;
  line2: string;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  phone: string;
};

export function formatMoney(amount: number, currency = DEFAULT_CURRENCY, locale = DEFAULT_LOCALE): string {
  if (!Number.isFinite(amount)) throw new Error('Invalid monetary amount');
  return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(amount);
}
