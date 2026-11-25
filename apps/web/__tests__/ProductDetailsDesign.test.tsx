import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ProductDetailsCard} from '@/components/products/ProductDetailsCard';
jest.mock('next/image',()=>({__esModule:true,default:({fill,priority,unoptimized,...p}:any)=><img {...p}/>}));
jest.mock('framer-motion',()=>{const React=require('react');return {AnimatePresence:({children}:any)=>children,motion:{div:React.forwardRef(({children,initial,animate,exit,transition,...p}:any,ref:any)=><div ref={ref} {...p}>{children}</div>)}};});
const open=jest.fn(),send=jest.fn();
import {api} from '@/lib/api';
jest.mock('@/lib/api',()=>({api:{post:jest.fn()}}));
beforeEach(()=>{jest.clearAllMocks();});
jest.mock('@/hooks/useAIOrderingStore',()=>({useAIOrderingStore:(selector:any)=>selector({addProductById:jest.fn(),setOverlayVisible:open,sendMessage:send,isLoading:false})}));
const product={id:118,name:'Black Satin lipstick - Single pack',price:12,price_status:'listed',image_url:'/dev-fixtures/makeup.svg',description:'Satin lipstick. Black shade; single pack. Synthetic local test product, not a merchant offer.',sku:'ADL-DEV-v1-lip-00000118',attributes:{_seed_dataset:'airdeliver-dev-fixtures-v1'},rating:4.8,inventory:10};
it('renders design evidence',()=>{
 const view=render(<ProductDetailsCard product={product} onClose={jest.fn()}/>);
 if(process.env.DETAIL_PREVIEW_HTML)require('fs').writeFileSync(process.env.DETAIL_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="file:///tmp/product-detail.css"></head><body style="margin:0;background:#020303;font-family:Arial,sans-serif"><main style="display:flex;align-items:center;justify-content:center;min-height:100dvh;padding:18px;box-sizing:border-box">'+view.container.innerHTML+'</main></body></html>');
});

const merchant={...product,id:8,sku:'LIP-8',attributes:{color:'Black'},description:'Satin lipstick.',rating:null};
it('does not invent ratings or sell synthetic stock',()=>{
 render(<ProductDetailsCard product={product} onClose={jest.fn()}/>);
 expect(screen.queryByText(/4.8/)).not.toBeInTheDocument();
 expect(screen.queryByText(/SKU|Synthetic local/)).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Unavailable to purchase'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Increase quantity'})).toBeDisabled();
 expect(api.post).not.toHaveBeenCalled();expect(send).not.toHaveBeenCalled();
});
it('sends quantity only once, does not claim added on an accepted response',async()=>{
 let resolve!:(value:any)=>void;
 jest.mocked(api.post).mockImplementation(()=>new Promise(r=>{resolve=r;}));
 render(<ProductDetailsCard product={merchant} onClose={jest.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Increase quantity'}));
 const add=screen.getByRole('button',{name:'Add to cart'});
 fireEvent.click(add);fireEvent.click(add);
 expect(api.post).toHaveBeenCalledTimes(1);
 expect(api.post).toHaveBeenCalledWith('/ai-ordering/cart/add',{product_id:8,quantity:2},{headers:{'Idempotency-Key':expect.any(String)}});
 expect(add).toBeDisabled();
 resolve({status:202});
 expect(await screen.findByRole('status')).toHaveTextContent('Check your cart for confirmation');
 expect(screen.queryByText('Added')).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Check cart for confirmation'})).toBeDisabled();
});
it('preserves uncertain state without retrying',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('network timeout'));
 render(<ProductDetailsCard product={merchant} onClose={jest.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Add to cart'}));
 expect(await screen.findByRole('status')).toHaveTextContent('could not be confirmed');
 expect(api.post).toHaveBeenCalledTimes(1);
 expect(screen.getByRole('link',{name:'View cart'})).toHaveAttribute('href','/cart');
});
it('guards unknown price, inactive, missing id and exhausted inventory',()=>{
 for(const change of [{price:null},{is_active:false},{id:'bad'},{inventory:0}]){
 const view=render(<ProductDetailsCard product={{...merchant,...change}} onClose={jest.fn()}/>);
 expect(screen.getByRole('button',{name:'Unavailable to purchase'})).toBeDisabled();view.unmount();
 }
 expect(api.post).not.toHaveBeenCalled();
});
it('shows only provided rating and details, asks only on explicit click',()=>{
 const close=jest.fn();
 render(<ProductDetailsCard product={{...merchant,rating:4.2,predicted_delivery:'Delivery estimate: 2 days',currency:'EGP'}} onClose={close}/>);
 expect(screen.getByText('4.2')).toBeInTheDocument();
 expect(screen.getByText('EGP 12.00')).toBeInTheDocument();
 expect(screen.getByText('Delivery estimate: 2 days')).toBeInTheDocument();
 expect(send).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Ask about this'}));
 expect(open).toHaveBeenCalledWith(true);expect(send).toHaveBeenCalledWith('Tell me about '+merchant.name);expect(close).toHaveBeenCalledTimes(1);
});
it('focuses close, traps tab and supports Escape',()=>{
 const close=jest.fn();
 render(<ProductDetailsCard product={merchant} onClose={close}/>);
 const button=screen.getByRole('button',{name:'Close product details'});
 expect(button).toHaveFocus();
 fireEvent.keyDown(document,{key:'Tab',shiftKey:true});
 expect(screen.getByRole('button',{name:'Ask about this'})).toHaveFocus();
 fireEvent.keyDown(document,{key:'Tab'});expect(button).toHaveFocus();
 fireEvent.keyDown(document,{key:'Escape'});expect(close).toHaveBeenCalledTimes(1);
});
it('resets product-specific quantities and notices when switching product',()=>{
 const view=render(<ProductDetailsCard product={merchant} onClose={jest.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Increase quantity'}));
 expect(screen.getByRole('textbox',{name:'Quantity'})).toHaveValue('2');
 view.rerender(<ProductDetailsCard product={{...merchant,id:9}} onClose={jest.fn()}/>);
 expect(screen.getByRole('textbox',{name:'Quantity'})).toHaveValue('1');
});
