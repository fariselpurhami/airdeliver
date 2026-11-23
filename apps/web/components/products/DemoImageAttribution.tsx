'use client';
import { demoImagePresentation, type DemoIdentity } from '@/lib/catalog/demoImages';

export function DemoImageAttribution({product, expanded=false}:{product:DemoIdentity;expanded?:boolean}) {
 const demo=demoImagePresentation(product);
 if(!demo)return null;
 const item=demo.candidate;
 const credit=<div className="rounded-xl border border-cyan-100/10 bg-[#0b1426] px-3 py-2.5 text-[10px] leading-relaxed text-slate-300 normal-case shadow-lg">
  <strong className="font-medium text-slate-100">{item ? item.label : 'DEMO ILLUSTRATION. Not a product photo.'}</strong>
  {item && <div className="mt-1">Photo: {item.author}. <a className="text-cyan-200 underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300" href={item.source_url} target="_blank" rel="noopener noreferrer">Source</a>. <a className="text-cyan-200 underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300" href={item.license_url} target="_blank" rel="noopener noreferrer">{item.license}</a>. Commons thumbnail, no further pixel edits. If unavailable, a neutral demo illustration is shown.</div>}
 </div>;
 return <div data-demo-image-disclosure className="relative z-20 w-full min-w-0" onClick={e=>e.stopPropagation()} onKeyDown={e=>e.stopPropagation()}>
  {expanded ? <div className="p-2">{credit}</div> : <details className="group px-1" data-compact-image-credit>
   <summary aria-label="Image information and license" title="Image information and license" className="ml-auto flex h-11 w-11 cursor-pointer list-none items-center justify-center rounded-full text-slate-400 transition-colors hover:text-cyan-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300 focus-visible:outline-offset-[-4px] [&::-webkit-details-marker]:hidden">
    <span aria-hidden="true" className="flex h-5 w-5 items-center justify-center rounded-full border border-slate-400/40 bg-slate-950/70 font-serif text-xs italic group-open:border-cyan-200/60 group-open:text-cyan-100">i</span>
   </summary>
   <div className="pb-2">{credit}</div>
  </details>}
 </div>;
}
