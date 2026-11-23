import { demoImagePresentation, type DemoIdentity } from '@/lib/catalog/demoImages';
export function DemoImageAttribution({product}:{product:DemoIdentity}) {
 const demo=demoImagePresentation(product);
 if(!demo)return null;
 const item=demo.candidate;
 return <div data-demo-image-disclosure className="relative z-20 px-3 py-2 text-[10px] leading-relaxed text-slate-200 bg-slate-950/90 normal-case" onClick={e=>e.stopPropagation()}>
 <strong>{item ? item.label : 'DEMO ILLUSTRATION. Not a product photo.'}</strong>
 {item && <div>Photo: {item.author}. <a className="text-cyan-200 underline" href={item.source_url} target="_blank" rel="noopener noreferrer">Source</a>. <a className="text-cyan-200 underline" href={item.license_url} target="_blank" rel="noopener noreferrer">{item.license}</a>. Commons thumbnail, no further pixel edits. If unavailable, a neutral demo illustration is shown.</div>}
 </div>;
}
