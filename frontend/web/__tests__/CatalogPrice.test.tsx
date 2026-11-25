import { render, screen } from '@testing-library/react';
import { CatalogPrice, listedCatalogPrice } from '@/components/ai/CatalogPrice';

it.each([null, undefined, '', '  ', [], {}, true, 'NaN', 'Infinity', -1])('never displays invalid price %s as free', price => {
  render(<CatalogPrice product={{ price }} />);
  expect(screen.getByText('Price unverified')).toBeInTheDocument();
  expect(screen.queryByText('$0.00')).not.toBeInTheDocument();
});
it('keeps explicit unknown distinct from listed zero', () => {
  expect(listedCatalogPrice({ price: 0, price_status: 'unknown' })).toBeNull();
  render(<CatalogPrice product={{ price: '0.00', price_status: 'listed' }} />);
  expect(screen.getByText('$0.00')).toBeInTheDocument();
});
it('formats a listed finite amount', () => {
  render(<CatalogPrice product={{ price: '19.99' }} />);
  expect(screen.getByText('$19.99')).toBeInTheDocument();
});
