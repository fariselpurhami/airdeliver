import React from 'react';
import {render,screen,fireEvent} from '@testing-library/react';
import {CatalogImage} from '@/components/products/CatalogImage';
import {DemoImageAttribution} from '@/components/products/DemoImageAttribution';
import fs from 'fs';
jest.mock('@/lib/catalog/demo-images.json',()=>{const m:any=jest.requireActual('@/lib/catalog/demo-images.json');return {...m,runtime_enabled:true};});
jest.mock('next/image',()=>({__esModule:true,default:({fill,unoptimized,priority,...props}:any)=><img {...props}/>}));
const p={name:'Adidas Samba OG',sku:'ADL-DEMO-v1-pilot-00000001',attributes:{_seed_dataset:'airdeliver-demo-v1'}};
it('activates only marker-bound known demo rows, with credit and failure fallback',()=>{
 const {rerender}=render(<><CatalogImage product={p} src="https://merchant.example/wrong.jpg" alt={p.name} width={240} height={180}/><DemoImageAttribution product={p}/></>);
 expect(screen.getByRole('img')).toHaveAttribute('src','/images/demo-v1/samba-reference.jpg');
 expect(screen.getByText(/Not an exact SKU/)).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'CC-BY-SA-4.0',hidden:true})).toBeInTheDocument();
 fireEvent.error(screen.getByRole('img'));
 expect(screen.getByRole('img')).toHaveAttribute('src','/images/demo-v1/neutral.svg');
 rerender(<><CatalogImage product={{...p,sku:'real-merchant'}} src="https://merchant.example/real.jpg" alt="Merchant product" width={240} height={180}/><DemoImageAttribution product={{...p,sku:'real-merchant'}}/></>);
 expect(screen.getByRole('img')).toHaveAttribute('src','https://merchant.example/real.jpg');
 expect(screen.queryByText(/Not an exact SKU/)).toBe(null);
});
it('known demo templates without approved photo use neutral art, not unverified remote URLs',()=>{
 render(<><CatalogImage product={{...p,name:'Audemars Piguet Royal Oak'}} src="https://merchant.example/wrong.jpg" alt="Watch" width={240} height={180}/><DemoImageAttribution product={{...p,name:'Audemars Piguet Royal Oak'}}/></>);
 expect(screen.getByRole('img')).toHaveAttribute('src','/images/demo-v1/neutral.svg');
 expect(screen.getByText(/DEMO ILLUSTRATION/)).toBeInTheDocument();
});
it('all required catalog surfaces carry image identity and visible attribution',()=>{
 for(const path of ['src/app/(main)/products/page.tsx','src/components/products/ProductCard.tsx','src/components/products/ProductDetailsCard.tsx','src/components/ai/AIChatOverlay.tsx']){
  const source=fs.readFileSync(path,'utf8');expect(source).toContain('product={product}');expect(source).toContain('DemoImageAttribution');
 }
});

it('keeps compact native keyboard/touch disclosure on cards and expanded details credit',()=>{
 const {container,rerender}=render(<DemoImageAttribution product={p}/>);
 const summary=screen.getByLabelText('Image information and license');
 expect(summary.tagName).toBe('SUMMARY');
 expect(container.querySelector('details')).not.toHaveAttribute('open');
 expect(container.querySelector('a[href*="creativecommons"]')).toBeInTheDocument();
 rerender(<DemoImageAttribution product={p} expanded/>);
 expect(container.querySelector('details')).toBe(null);
 expect(screen.getByRole('link',{name:'CC-BY-SA-4.0'})).toBeVisible();
});
