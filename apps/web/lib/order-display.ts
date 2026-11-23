/** Order display is explicit about unknown money/status, never guesses USD. */
export function orderMoney(amount: number, currency?: string): string {
  if (!Number.isFinite(amount) || amount < 0 || !currency || !/^[A-Z]{3}$/.test(currency)) return 'Amount unavailable';
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, currencyDisplay: 'code' }).format(amount);
  } catch { return 'Amount unavailable'; }
}

export function orderDate(value?: string): string {
  if (!value) return 'Time unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString();
}

const statuses: Record<string, { label: string; className: string }> = {
  pending: { label: 'Awaiting payment confirmation', className: 'text-yellow-400' },
  processing: { label: 'Payment confirmed, processing', className: 'text-cyan-400' },
  assigned: { label: 'Assigned', className: 'text-cyan-400' },
  in_transit: { label: 'In transit', className: 'text-cyan-400' },
  delivered: { label: 'Delivered', className: 'text-green-400' },
  cancelled: { label: 'Cancelled', className: 'text-red-400' },
  failed: { label: 'Payment or order failed', className: 'text-red-400' },
  saved_for_later: { label: 'Saved for later, not purchased', className: 'text-gray-300' },
};
export function orderStatus(value: string) {
  return statuses[value?.toLowerCase()] || { label: 'Status unavailable', className: 'text-gray-300' };
}
