/** HTTP assistant boundary. A malformed evidence/card contract never falls back
 * to displaying potentially unsupported sales prose without its cards. */
export function parseSupportReply(input: unknown): {
  text: string; action?: unknown; response_kind?: string; products: Record<string, unknown>[];
} {
  if (!input || typeof input !== 'object') throw new Error('Invalid assistant response');
  const data = input as Record<string, unknown>;
  if (typeof data.text !== 'string' || !data.text.trim() || data.text.length > 10000) throw new Error('Invalid assistant text');
  if (data.products !== undefined && (!Array.isArray(data.products) || data.products.length > 5)) throw new Error('Invalid catalog response');
  const seen = new Set<number>();
  const products = ((data.products ?? []) as unknown[]).map(value => {
    if (!value || typeof value !== 'object') throw new Error('Invalid catalog card');
    const card = value as Record<string, unknown>;
    if (typeof card.id !== 'number' || !Number.isSafeInteger(card.id) || card.id < 1 || seen.has(card.id) || typeof card.name !== 'string' || !card.name.trim()) throw new Error('Invalid catalog identity');
    seen.add(card.id);
    if (!['seeded_demo', 'local_catalog'].includes(String(card.evidence_kind)) || typeof card.availability_note !== 'string' || !card.availability_note.trim()) throw new Error('Missing catalog evidence');
    if (!['demo', 'local_in_stock', 'local_out_of_stock', 'unverified'].includes(String(card.stock_status))) throw new Error('Invalid stock evidence');
    if (card.evidence_kind === 'seeded_demo' && card.stock_status !== 'demo') throw new Error('Invalid demo evidence');
    if (card.price_status === 'listed') {
      if (typeof card.price !== 'string' || !/^\d+(?:\.\d+)?$/.test(card.price) || !Number.isFinite(Number(card.price)) || typeof card.currency !== 'string' || !/^[A-Z]{3}$/.test(card.currency)) throw new Error('Invalid catalog price');
    } else if (card.price_status !== 'unknown' || card.price !== null || card.currency !== null) throw new Error('Invalid unknown price');
    return card;
  });
  return { text: data.text, action: data.action, response_kind: typeof data.response_kind === 'string' ? data.response_kind : undefined, products };
}
