import type { ShippingAddress } from '@/lib/commerce';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ShippingAddressForm from '@/components/checkout/ShippingAddressForm';
import { api } from '@/lib/api';
import { formatMoney } from '@/lib/commerce';
import { useAIOrderingStore } from '@/hooks/useAIOrderingStore';
jest.mock('@/lib/api', () => ({ api: { get: jest.fn() } }));

it('collects delivery details and uses only configured payment methods', async () => {
  jest.mocked(api.get).mockResolvedValue({ data: { providers: ['stripe'] } });
  const submit = jest.fn<(address: ShippingAddress, provider: 'stripe' | 'paypal') => Promise<boolean>>().mockResolvedValue(true);
  render(<ShippingAddressForm onSubmit={submit} onBack={jest.fn()} />);
  await waitFor(() => expect(screen.getByRole('button', { name: /continue to secure payment/i })).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test Buyer' } });
  fireEvent.change(screen.getByLabelText('Street address'), { target: { value: '123 Main Street' } });
  fireEvent.change(screen.getByLabelText('City'), { target: { value: 'New York' } });
  fireEvent.change(screen.getByLabelText(/State or territory/), { target: { value: 'NY' } });
  fireEvent.change(screen.getByLabelText('ZIP code'), { target: { value: '10001' } });
  fireEvent.change(screen.getByLabelText('Delivery phone number'), { target: { value: '+12125550123' } });
  fireEvent.click(screen.getByRole('button', { name: /continue to secure payment/i }));
  await waitFor(() => expect(submit).toHaveBeenCalledWith(expect.objectContaining({ country: 'US', line1: '123 Main Street', postal_code: '10001' }), 'stripe'));
  expect(screen.queryByText('PayPal')).not.toBeInTheDocument();
});

it('formats money by currency/locale rather than a fixed dollar sign', () => {
  expect(formatMoney(12.5, 'USD', 'en-US')).toBe('$12.50');
  expect(formatMoney(12.5, 'EUR', 'de-DE')).toContain('12,50');
  expect(formatMoney(1200, 'JPY', 'ja-JP')).not.toContain('.00');
});

it('only sends structured shipping after explicit submission with an authenticated response connection', async () => {
  const original = useAIOrderingStore.getState();
  const post = jest.fn<(path: string, body?: Record<string, unknown>) => Promise<boolean>>().mockResolvedValue(true);
  useAIOrderingStore.setState({ _postCartCommand: post, socketStatus: 'connected', authToken: 'test-token' });
  const shipping = { recipient_name: 'Test Buyer', line1: '123 Main Street', line2: '', city: 'New York', region: 'NY', postal_code: '10001', country: 'US', phone: '+12125550123' };
  useAIOrderingStore.getState().confirmCurrentOrder();
  expect(post).not.toHaveBeenCalled();
  await useAIOrderingStore.getState().submitShippingAddress(shipping, 'stripe');
  expect(post).toHaveBeenCalledWith('/checkout/confirm', { shipping_address: shipping, payment_provider: 'stripe' });
  useAIOrderingStore.setState(original, true);
});
