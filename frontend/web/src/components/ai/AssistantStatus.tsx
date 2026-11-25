'use client';
import Link from 'next/link';
import {useState} from 'react';
import {useAIOrderingStore} from '@/hooks/useAIOrderingStore';

const ALLOWED = new Set(['opening_unverified','opening_empty','capacity','assistant_unavailable','reply_unverified','catalog_unverified','visual_unavailable','preferences_changed','research_unavailable','research_unverified','research_empty','research_scope','catalog_not_ready','selection_recent']);
export default function AssistantStatus({code,recovery,text,messageId}:{code:unknown;recovery:unknown;text:string;messageId:number|string}) {
 const [submitted,setSubmitted]=useState(false);
 const loading=useAIOrderingStore(state=>state.isLoading);
 const messages=useAIOrderingStore(state=>state.messages);
 const send=useAIOrderingStore(state=>state.sendMessage);
 const opening=useAIOrderingStore(state=>state.fetchInitialSuggestions);
 const index=messages.findIndex(message=>message.id===messageId);
 const question=index<0?undefined:[...messages.slice(0,index)].reverse().find(message=>message.sender==='user');
 const current=index>=0 && !messages.slice(index+1).some(message=>message.sender==='user');
 const retryableQuestion=question?.contentType==='text' && typeof question.content==='string';
 if(typeof code!=='string' || !ALLOWED.has(code))return <p>{text}</p>;
 const canRetry=current && !submitted && !loading && (recovery==='retry_opening' || (recovery==='retry_chat' && retryableQuestion));
 const retry=()=>{
  if(!canRetry)return;
  setSubmitted(true);
  if(recovery==='retry_opening')opening();
  // Only the last user-written question. Never queued commands or checkout.
  else if(question && typeof question.content==='string')send(question.content);
 };
 return <section role="status" aria-live="polite" className="rounded-2xl bg-white/[.04] px-4 py-4 text-sm leading-relaxed text-white/75">
  <p>{text}</p>
  <div className="mt-3 flex flex-wrap items-center gap-2">
   {canRetry && <button type="button" onClick={retry} className="min-h-11 rounded-full bg-white/10 px-4 text-xs font-medium text-white/85 hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white">{recovery==='retry_opening'?'Reload selection':'Try question again'}</button>}
   {submitted && <span className="text-xs text-white/45">Request sent. Waiting for a reply.</span>}
   <Link href="/products" className="inline-flex min-h-11 items-center rounded-full bg-white/10 px-4 text-xs font-medium text-white/85 hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white">Browse products</Link>
  </div>
 </section>;
}
