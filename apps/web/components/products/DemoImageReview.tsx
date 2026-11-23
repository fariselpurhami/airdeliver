'use client';
import { useState } from 'react';
import { demoImageCandidate, type DemoIdentity } from '@/lib/catalog/demoImages';

/** Review-only pilot. Not mounted in storefront routes until audience approves it. */
export function DemoImageReview({ product }: { product: DemoIdentity }) {
 const candidate = demoImageCandidate(product);
 const [failed,setFailed] = useState(false);
 return <figure style={{margin:0,padding:16,background:'#111827',color:'white',borderRadius:16}}>
  <img src={candidate && !failed ? candidate.asset : '/images/demo-v1/neutral.svg'}
   alt={candidate && !failed ? `${candidate.title}. Demo reference only, not the listed SKU variant.` : 'Neutral demo illustration. Not a product photo.'}
   onError={()=>setFailed(true)} style={{width:'100%',height:220,objectFit:'contain'}}/>
  <figcaption style={{fontSize:14,lineHeight:1.5}}>
   <strong>{candidate && !failed ? candidate.label : 'DEMO ILLUSTRATION. Not a product photo.'}</strong>
   <p>{String(product.name || 'Demo item')}</p>
   {candidate && !failed && <p>Photo: {candidate.author}. <a style={{color:'#9bddff'}} href={candidate.source_url}>Source: {candidate.title}</a>. <a style={{color:'#9bddff'}} href={candidate.license_url}>{candidate.license}</a>. Commons thumbnail, no further pixel edits.</p>}
  </figcaption>
 </figure>;
}
