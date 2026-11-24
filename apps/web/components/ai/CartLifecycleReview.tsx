'use client';
import {useRef,useState} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {parseCartItems} from '@/lib/cart-snapshot';
import {useCartStore} from '@/hooks/useCartStore';
export default function CartLifecycleReview({payload}:{payload:Record<string,unknown>}) {
 const [state,setState]=useState('idle');const busy=useRef(false);
 const {review_id:id,operation,item_count:count}=payload;
 if(typeof id!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id)||!['clear','save'].includes(String(operation))||!Number.isInteger(count)||Number(count)<1)return null;
 const submit=async()=>{
  if(busy.current||state!=='idle')return;
  busy.current=true;setState('pending');
  try {
   const result=await api.post('/ai-ordering/cart/review/confirm',{review_id:id});
   if(!['saved','cleared'].includes(result.data?.status))throw new Error('Unconfirmed');
   const current=await api.get('/ai-ordering/cart');
   useCartStore.getState().replaceItems(parseCartItems(current.data));setState('checked');
  }catch{setState('uncertain');}
 };
 return <section className="mt-3 space-y-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs">
  <p className="text-slate-200">{operation==='clear'?`Clear ${count} active cart lines. Existing orders will not be cancelled.`:`Save ${count} lines as a cancelled Saved List record in your profile, then clear the active cart.`}</p>
  <p className="text-slate-400">No payment or order placement. This review expires after five minutes. A changed cart requires a fresh review.</p>
  {state==='idle'&&<button type="button" onClick={()=>void submit()} className="inline-flex min-h-11 items-center rounded-xl border border-cyan-300/25 px-4 py-2 text-cyan-100">{operation==='clear'?'Confirm clear active cart':'Confirm save list and clear cart'}</button>}
  {state==='pending'&&<p role="status">Submitting and checking your cart...</p>}
  {state==='checked'&&<p role="status">Request confirmed. Your refreshed cart is ready to review.</p>}
  {state==='uncertain'&&<p role="alert">This change could not be confirmed. Do not retry blindly. Refresh your cart and check saved lists before requesting another review.</p>}
  <Link href="/cart" className="flex min-h-11 w-fit items-center underline text-cyan-200">Open cart</Link>
 </section>;
}
