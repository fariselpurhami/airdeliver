import React from 'react';
import { render,screen,fireEvent } from '@testing-library/react';
import { demoImageCandidate,reviewedDemoImage,isDemoImageEligible } from '@/lib/catalog/demoImages';
import { DemoImageReview } from '@/components/products/DemoImageReview';
const p={name:'Adidas Samba OG',sku:'ADL-DEMO-v1-pilot-00000001',attributes:{_seed_dataset:'airdeliver-demo-v1'}};
it('requires both independent demo markers and a known template',()=>{
 expect(demoImageCandidate(p)?.author).toBe('Pangalau');
 expect(isDemoImageEligible({...p,sku:'merchant-1'})).toBe(false);
 expect(demoImageCandidate({...p,attributes:{}})).toBe(null);
 expect(demoImageCandidate({...p,name:'Other item'})).toBe(null);
 expect(reviewedDemoImage(p)).toBe(null);
});
it('shows reference and license disclosure, then honest neutral on load failure',()=>{
 render(<DemoImageReview product={p}/>);
 expect(screen.getByText(/DEMO REFERENCE/)).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'CC-BY-SA-4.0'})).toHaveAttribute('href','https://creativecommons.org/licenses/by-sa/4.0/');
 fireEvent.error(screen.getByRole('img'));
 expect(screen.getByText(/DEMO ILLUSTRATION/)).toBeInTheDocument();
});

it('renders review evidence when explicitly requested',()=>{
 if (!process.env.DEMO_IMAGE_PREVIEW_HTML) return;
 const {container}=render(<div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:20}}><DemoImageReview product={p}/><DemoImageReview product={{...p,name:'Nike Air Jordan 1 Retro High OG'}}/><DemoImageReview product={{...p,name:'Audemars Piguet Royal Oak'}}/></div>);
 require('fs').writeFileSync(process.env.DEMO_IMAGE_PREVIEW_HTML,'<!doctype html><html><body style="background:#070d17;color:white;font:16px Arial;padding:24px"><h1>Demo image review pilot</h1><p>Two licensed family references, one honest neutral fallback. Not exact SKU photography.</p>'+container.innerHTML+'</body></html>');
});
