import manifest from './demo-images.json';
export type DemoIdentity = { sku?: unknown; name?: unknown; attributes?: unknown };
export function isDemoImageEligible(product?: DemoIdentity): boolean {
 const attrs = product?.attributes;
 return typeof product?.name === 'string' && manifest.template_names.includes(product.name)
  && typeof product?.sku === 'string' && /^ADL-DEMO-v1-[A-Za-z0-9_-]+-\d{8}$/.test(product.sku)
  && !!attrs && typeof attrs === 'object' && (attrs as Record<string,unknown>)._seed_dataset === 'airdeliver-demo-v1';
}
export function demoImageCandidate(product?: DemoIdentity) {
 if (!isDemoImageEligible(product)) return null;
 return manifest.items.find(row => row.template_name === product?.name) ?? null;
}
// Runtime gate remains explicit; candidate status does not certify an exact SKU photo.
export function reviewedDemoImage(product?: DemoIdentity) {
 if (!manifest.runtime_enabled) return null;
 return demoImageCandidate(product);
}

export function demoImagePresentation(product?: DemoIdentity) {
 if (!manifest.runtime_enabled || !isDemoImageEligible(product)) return null;
 return { candidate: demoImageCandidate(product), asset: demoImageCandidate(product)?.asset ?? '/images/demo-v1/neutral.svg' };
}
