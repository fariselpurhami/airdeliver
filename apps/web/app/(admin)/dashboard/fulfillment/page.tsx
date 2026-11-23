'use client';
import {useState} from 'react';
import {useSession} from 'next-auth/react';
import useSWR from 'swr';
import Link from 'next/link';
import {Package,ShieldCheck,ArrowLeft} from 'lucide-react';
import {api} from '@/lib/api';
type Order={id:number,status:string,is_paid:boolean,currency:string,total_price:number};
const next:Record<string,string>={processing:'assigned',assigned:'in_transit',in_transit:'delivered'};
const label:Record<string,string>={assigned:'Assign to fulfillment',in_transit:'Mark in transit',delivered:'Mark delivered'};
function OrderControl({order,onChanged}:{order:Order,onChanged:()=>void}){
 const [evidence,setEvidence]=useState(''),[review,setReview]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 const target=next[order.status];
 return <article className="rounded-[28px] border border-white/10 bg-white/[0.04] backdrop-blur-xl p-5 sm:p-7 space-y-4">
  <div className="flex flex-wrap justify-between gap-2"><h2 className="font-mono text-cyan-200">Order #{order.id}</h2><span className="text-sm text-slate-300">{order.status.replaceAll('_',' ')} · {order.is_paid?'Payment confirmed':'Unpaid'}</span></div>
  {!order.is_paid || !target?<p className="text-xs text-slate-400">No fulfillment transition available for this state. No payment or refund can be changed here.</p>:<>
   <label className="block text-xs text-slate-300">Operator evidence, 10 to 500 characters. Record the real handoff/delivery reference, not a guess or customer secrets.
    <textarea value={evidence} maxLength={500} onChange={e=>{setEvidence(e.target.value);setReview(false);}} className="mt-2 w-full min-h-24 rounded-xl border border-white/15 bg-black/40 px-3 py-3 text-white"/>
   </label>
   {review?<div className="space-y-3 rounded-xl border border-amber-300/25 bg-amber-500/5 p-4 text-sm">
    <p>You are attesting that order #{order.id} moved from {order.status.replaceAll('_',' ')} to {target.replaceAll('_',' ')}. This is not an automatic carrier update. A customer in-app notification will be saved.</p>
    <button type="button" disabled={busy} onClick={async()=>{
     if(busy)return;setBusy(true);setMessage('');
     try{await api.post(`/admin/orders/${order.id}/fulfillment`,{from_status:order.status,to_status:target,evidence});setMessage('Recorded. Refreshing order state.');setReview(false);setEvidence('');onChanged();}
     catch{setMessage('Update could not be confirmed. Refresh the list before trying again; never assume a physical handoff from this screen.');setReview(false);}
     finally{setBusy(false);}
    }} className="rounded-xl bg-cyan-300 px-4 py-3 font-semibold text-black disabled:opacity-50">{busy?'Recording...':'Confirm operator attestation'}</button>
    <button type="button" disabled={busy} onClick={()=>setReview(false)} className="ml-3 underline">Back</button>
   </div>:<button type="button" disabled={evidence.trim().length<10 || busy} onClick={()=>setReview(true)} className="rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100 disabled:opacity-40">Review: {label[target]}</button>}
  </>}
  {message&&<p role="status" className="text-sm text-amber-100">{message}</p>}
 </article>;
}
export default function FulfillmentPage(){
 const {data:session,status}=useSession();const [page,setPage]=useState(1);
 const admin=status==='authenticated' && session?.user?.role==='admin';
 const {data:configuration,error:configurationError}=useSWR<{enabled:boolean}>(admin?'/admin/fulfillment/config':null,url=>api.get(url).then(r=>r.data),{shouldRetryOnError:false});
 const enabled=configuration?.enabled===true;
 const {data,error,isLoading,mutate}=useSWR<{orders:Order[],total_orders:number}>(admin && enabled?`/admin/orders?page=${page}&limit=10`:null,url=>api.get(url).then(r=>r.data),{shouldRetryOnError:false});
 return <main className="min-h-screen bg-black text-white px-4 pt-24 pb-16 relative isolate">
  <div aria-hidden="true" className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,rgba(6,182,212,0.09),transparent_65%)]"/>
  <div className="max-w-3xl mx-auto space-y-6">
   <Link href="/dashboard" className="inline-flex gap-2 items-center py-3 text-xs text-slate-400"><ArrowLeft size={14}/>Back to dashboard</Link>
   <header className="py-5 space-y-4"><p className="flex items-center gap-2 uppercase tracking-[.2em] text-[10px] text-cyan-300"><ShieldCheck size={14}/>Authorized operator workspace</p><h1 className="text-3xl sm:text-4xl font-black tracking-tight">MANUAL <span className="text-cyan-300">FULFILLMENT</span></h1><p className="text-sm text-slate-400">Record real operational events. No carrier, ETA, payment or refund is inferred or called here.</p></header>
   {status==='loading'?<p role="status">Checking account...</p>:!admin?<p role="alert">An administrator account is required. Server permissions are checked on every request.</p>:!enabled?<p role="status" className="rounded-xl border border-amber-300/20 p-5 text-sm text-amber-100">{configurationError?'Fulfillment availability could not be checked. No order controls are enabled.':configuration?'Manual fulfillment is not enabled. An approved operator and evidence policy must be configured before order controls are available.':'Checking fulfillment availability...'}</p>:<>
    <button type="button" onClick={()=>void mutate()} className="rounded-xl border border-white/15 px-4 py-3 text-xs">Refresh order list</button>
    {error&&<p role="alert" className="text-amber-200">Order list could not be refreshed. Refresh before recording another event.</p>}
    {isLoading?<p role="status">Loading orders...</p>:data?.orders.map(order=><OrderControl key={`${order.id}-${order.status}`} order={order} onChanged={()=>void mutate()}/>)}
    {data?.orders.length===0&&<p>No orders on this page.</p>}
    <nav aria-label="Fulfillment pages" className="flex justify-between items-center text-sm"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="p-3 disabled:opacity-40">Previous</button><span>Page {page}</span><button disabled={!data || page*10>=data.total_orders} onClick={()=>setPage(p=>p+1)} className="p-3 disabled:opacity-40">Next</button></nav>
   </>}
   <p className="text-xs text-slate-500 flex gap-2"><Package size={14}/>Updates are saved as operator attestations with audit records, not evidence of carrier verification.</p>
  </div>
 </main>;
}
