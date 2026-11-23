import { type CartItem } from '@/hooks/useCartStore';

/** Validate an authoritative response before replacing any preserved UI cart. */
export function parseCartItems(content: unknown): CartItem[] {
  if (!content || typeof content !== 'object' || !Array.isArray((content as {items?:unknown}).items)) throw new Error('Invalid cart response');
  const seen = new Set<number>();
  return (content as {items:Record<string,unknown>[]}).items.map(item => {
    if (!item || typeof item !== 'object') throw new Error('Invalid cart line');
    const id = item.product_id ?? item.id;
    const quantity = item.quantity;
    if (typeof id !== 'number' || !Number.isSafeInteger(id) || id < 1 || seen.has(id)) throw new Error('Invalid cart product');
    if (typeof quantity !== 'number' || !Number.isInteger(quantity) || quantity < 1 || quantity > 99) throw new Error('Invalid cart quantity');
    if ((typeof item.price !== 'string' && typeof item.price !== 'number') || (typeof item.price === 'string' && !item.price.trim()) || item.price_status === 'unknown') throw new Error('Unverified cart price');
    const price = Number(item.price);
    if (!Number.isFinite(price) || price < 0 || typeof item.name !== 'string' || !item.name.trim()) throw new Error('Invalid cart price/name');
    seen.add(id);
    return { ...item, id, name:item.name, quantity, price, image_url:typeof item.image_url === 'string' ? item.image_url : null, description:typeof item.description === 'string' ? item.description : '', inventory:0 } as CartItem;
  });
}
