export function CatalogEvidence({product}: {product: {evidence_kind?: string; availability_note?: string}}) {
  if (!product.evidence_kind) return null;
  return <div className="my-2 rounded-xl border border-white/10 bg-white/[0.04] px-2.5 py-2 text-[11px] leading-relaxed text-white/65">
    <span className="block text-[10px] font-semibold uppercase tracking-wider text-sky-200/90">{product.evidence_kind === 'seeded_demo' ? 'Demo catalog' : 'Local catalog, not merchant verified'}</span>
    <span>{product.availability_note}</span>
  </div>;
}
