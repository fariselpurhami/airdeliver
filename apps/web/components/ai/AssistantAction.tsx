'use client';
import {useRef,useState} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {parseCartItems} from '@/lib/cart-snapshot';
import {useCartStore} from '@/hooks/useCartStore';

export default function AssistantAction({action}:{action:unknown}) {
 const [state,setState]=useState<'idle'|'pending'|'checked'|'uncertain'>('idle');
 const busy=useRef(false);
 if(!action || typeof action!=='object')return null;
 const candidate=action as {action?:string,payload?:Record<string,unknown>};
 const payload=candidate.payload;
 const button='inline-flex min-h-11 items-center justify-center rounded-xl border border-cyan-300/25 bg-gradient-to-br from-cyan-400/15 to-indigo-400/10 px-4 py-2 text-xs font-medium text-cyan-100 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-cyan-300 disabled:opacity-50';
 if(candidate.action==='track_order') {
  const id=payload?.order_id ?? payload?.orderId;
  if(typeof id!=='string' || !/^[1-9]\d{0,9}$/.test(id) || Number(id)>2147483647)return null;
  return <Link className={button} href={`/tracking/${id}`}>Open order #{id}</Link>;
 }
 if(candidate.action==='initiate_support_handoff')return <div className="mt-3 rounded-xl border border-amber-300/20 bg-amber-500/5 p-3 text-xs text-amber-100" role="status">Human support is not connected here yet. No ticket or callback has been requested. <Link href="/help" className="underline">Open help</Link></div>;
 if(candidate.action!=='review_cart_change' || !payload)return null;
 const {product_id:id,product_name:name,operation,quantity,price,currency,review_id:reviewId}=payload;
 if(typeof reviewId!=='string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(reviewId) || !Number.isInteger(id) || Number(id)<1 || Number(id)>2147483647 || typeof name!=='string' || !name.trim() || name.length>512 || !['add','remove'].includes(String(operation)) || !Number.isInteger(quantity) || Number(quantity)<1 || Number(quantity)>99 || typeof price!=='string' || !/^\d+(\.\d{1,2})?$/.test(price) || currency!=='USD')return null;
 const submit=async()=>{
  if(busy.current || state!=='idle')return;
  busy.current=true;setState('pending');
  try {
   await api.post(`/ai-ordering/cart/${operation}`,{product_id:id,...(operation==='add'?{quantity}:{})},{headers:{'Idempotency-Key':reviewId}});
   const response=await api.get('/ai-ordering/cart');
   useCartStore.getState().replaceItems(parseCartItems(response.data));
   setState('checked');
  }catch{setState('uncertain');}
 };
 return <section className="mt-3 space-y-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs">
  <p className="text-slate-200">{operation==='add'?`Add ${quantity} × ${name}`:`Remove the entire ${name} line`} · listed unit price USD {price}</p>
  <p className="text-slate-400">Only your button press submits this change. Current price and stock are checked by the store. No payment.</p>
  {state==='idle' && <button type="button" onClick={()=>void submit()} className={button}>{operation==='add'?'Confirm add to cart':'Confirm remove from cart'}</button>}
  {state==='pending' && <p role="status">Submitting and checking your cart...</p>}
  {state==='checked' && <p role="status">Request processed. Review your refreshed cart for the current quantities and price. Unavailable items may not have been added.</p>}
  {state==='uncertain' && <p role="alert">The change could not be confirmed. Do not submit it again blindly. Open your cart and refresh before deciding what to do next.</p>}
  <Link href="/cart" className="inline-block underline text-cyan-200">Review cart</Link>
 </section>;
}
