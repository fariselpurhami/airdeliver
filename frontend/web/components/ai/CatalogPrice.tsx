export function listedCatalogPrice(product: { price?: unknown; price_status?: string }): number | null {
  if (product.price_status === 'unknown' || product.price === null || product.price === undefined || (typeof product.price !== 'number' && typeof product.price !== 'string') || (typeof product.price === 'string' && product.price.trim() === '')) return null;
  const price = Number(product.price);
  return Number.isFinite(price) && price >= 0 ? price : null;
}

export function CatalogPrice({ product }: { product: { price?: unknown; price_status?: string; currency?: string } }) {
  const price = listedCatalogPrice(product);
  return <span>{price === null ? 'Price unverified' : product.currency && product.currency !== 'USD' ? `${product.currency} ${price.toFixed(2)}` : `$${price.toFixed(2)}`}</span>;
}
