import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PayPalApproval, { safePayPalApprovalUrl } from '@/components/checkout/PayPalApproval';
import PayPalReturn from '@/app/(main)/checkout/paypal/return/page';
import { api } from '@/lib/api';
jest.mock('@/lib/api', () => ({ api: { post: jest.fn() } }));

it.each(['javascript:alert(1)', 'https://paypal.com.evil.test/checkout', 'https://evil.test/', 'http://www.paypal.com/', 'https://user@www.paypal.com/'])('rejects untrusted approval URL %s', value => {
  expect(safePayPalApprovalUrl(value)).toBeNull();
});
it('shows the bound amount and a verified PayPal redirect', () => {
  render(<PayPalApproval approvalUrl="https://www.sandbox.paypal.com/checkoutnow?token=ABC" total={12.5} currency="USD" orderId={7} />);
  expect(screen.getByText('$12.50')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Continue to PayPal' })).toHaveAttribute('href', 'https://www.sandbox.paypal.com/checkoutnow?token=ABC');
});
it('does not claim capture on landing and confirms only after the authenticated API response', async () => {
  window.history.replaceState({}, '', '/checkout/paypal/return?order_id=7&token=ABC123');
  jest.mocked(api.post).mockResolvedValue({ data: { status: 'captured' } });
  render(<PayPalReturn />);
  expect(screen.queryByText('Payment confirmed')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Complete payment' }));
  await waitFor(() => expect(screen.getByText('Payment confirmed')).toBeInTheDocument());
  expect(api.post).toHaveBeenCalledWith('/ai-ordering/checkout/paypal/capture', { order_id: '7', paypal_order_id: 'ABC123' });
});
it('keeps an uncertain capture outcome honest instead of claiming no charge', async () => {
  window.history.replaceState({}, '', '/checkout/paypal/return?order_id=7&token=ABC123');
  jest.mocked(api.post).mockRejectedValue(new Error('network'));
  render(<PayPalReturn />);
  fireEvent.click(screen.getByRole('button', { name: 'Complete payment' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Your payment may have completed'));
});
