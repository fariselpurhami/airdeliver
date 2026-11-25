import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AIReasoning, CarouselProductCard } from '@/components/ai/AIChatOverlay';
import { ProductCard } from '@/components/products/ProductCard';
import { normalizeProductData } from '@/components/products/ProductOverlay';
import { ProductDetailsCard } from '@/components/products/ProductDetailsCard';
jest.mock('react-markdown', () => ({__esModule:true,default:()=>null}));
jest.mock('remark-gfm', () => ({__esModule:true,default:()=>null}));
jest.mock('next/navigation', () => ({useRouter:jest.fn()}));
jest.mock('next/image', () => ({__esModule:true,default:(p:any)=><img alt={p.alt}/>}));
jest.mock('framer-motion', () => {
  const React = require('react'); const tags=new Map();
  return {useMotionValue:()=>({set:jest.fn()}),useTransform:()=>0,useAnimation:jest.fn(),AnimatePresence:({children}:any)=>children,motion:new Proxy({},{get:(_,tag)=>{
    if(!tags.has(tag)) tags.set(tag,React.forwardRef(({children,initial,animate,exit,transition,layout,whileHover,whileTap,...p}:any,ref:any)=>React.createElement(tag,{...p,ref},children)));
    return tags.get(tag);
  }})};
});
it('unknown carousel price cannot add but can open details', () => {
  const onSelect=jest.fn(), onViewDetails=jest.fn();
  const {container}=render(<div style={{background:'#080b12',padding:24,display:'flex'}}><CarouselProductCard totalItems={2} product={{id:1,name:'Atlas Headphones',price:null,price_status:'unknown'}} onSelect={onSelect} onViewDetails={onViewDetails}/><CarouselProductCard totalItems={2} product={{id:2,name:'Listed Zero Sample',price:0,price_status:'listed'}} onSelect={onSelect} onViewDetails={onViewDetails}/></div>);
  expect(screen.getByText('Price unverified')).toBeInTheDocument();
  expect(screen.getByText('$0.00')).toBeInTheDocument();
  const buttons=screen.getAllByRole('button',{name:'ADD'});
  expect(buttons[0]).toBeDisabled(); expect(buttons[1]).toBeEnabled();
  fireEvent.click(buttons[0]!); expect(onSelect).not.toHaveBeenCalled();
  if(process.env.PRICE_PREVIEW_HTML) require('fs').writeFileSync(process.env.PRICE_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/price-ui.css"></head><body style="margin:0">'+container.innerHTML+'</body></html>');
});
it('details preserve unknown price instead of displaying zero',()=>{
 render(<ProductDetailsCard product={{id:1,name:'Atlas Headphones',price:null,price_status:'unknown'}} onClose={jest.fn()}/>);
 expect(screen.getByText('Price unverified')).toBeInTheDocument(); expect(screen.queryByText('$0.00')).not.toBeInTheDocument();
});

it('overlay normalization preserves unknown status through the full catalog card',()=>{
 const product=normalizeProductData({id:7,name:'Atlas Headphones',price:null});
 expect(product.price_status).toBe('unknown');
 const {container}=render(<div style={{background:'#080b12',padding:24,width:300}}><ProductCard product={product} onOpen={jest.fn()}/></div>);
 expect(screen.getByText('Price unverified')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'order with air'})).toBeDisabled();
 if(process.env.CATALOG_PREVIEW_HTML) require('fs').writeFileSync(process.env.CATALOG_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/price-ui.css"></head><body style="margin:0">'+container.innerHTML+'</body></html>');
});

it('renders recovered opening editorial with the same displayed cards',()=>{
 if(!process.env.INSIGHT_PREVIEW)return;
 const fixture=require('fs').readFileSync('/tmp/insight-fixture.json','utf8');const data=JSON.parse(fixture);
 for(const mode of ['before','after']){
 const view=render(<div style={{background:'#080b12',color:'white',padding:24,maxWidth:520,margin:'auto'}}><h2 className="text-lg mb-6">Order with Air</h2><p className="text-sm mb-5">{data[mode][0]}</p><div style={{display:'flex',gap:12,overflow:'hidden'}}>{data.products.map((product:any)=><CarouselProductCard key={product.id} totalItems={2} product={product} onSelect={jest.fn()} onViewDetails={jest.fn()}/>)}</div><AIReasoning text={data[mode][1]}/></div>);
 require('fs').writeFileSync('/tmp/insight-'+mode+'.html','<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/insight.css"></head><body style="margin:0;background:#080b12">'+view.container.innerHTML+'</body></html>');view.unmount();
 }
});
