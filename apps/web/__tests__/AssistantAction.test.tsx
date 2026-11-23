import React from 'react';
import fs from 'fs';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import AssistantAction from '@/components/ai/AssistantAction';
import {api} from '@/lib/api';
import {useCartStore} from '@/hooks/useCartStore';
jest.mock('@/lib/api',()=>({api:{post:jest.fn(),get:jest.fn()}}));
const action={action:'review_cart_change',payload:{review_id:'00000000-0000-4000-8000-000000000001',product_id:7,product_name:'Atlas headphones',operation:'add',quantity:2,price:'25.00',currency:'USD'}};
beforeEach(()=>{jest.clearAllMocks();useCartStore.setState({items:[]});Object.defineProperty(global.crypto,'randomUUID',{value:()=> '00000000-0000-4000-8000-000000000001',configurable:true});});
it('never mutates on model response and submits exact reviewed target only on explicit click',async()=>{
 jest.mocked(api.post).mockResolvedValue({});jest.mocked(api.get).mockResolvedValue({data:{items:[{product_id:7,name:'Atlas headphones',quantity:2,price:'25.00'}]}});
 render(<AssistantAction action={action}/>);
 expect(api.post).not.toHaveBeenCalled();
 if(process.env.ACTION_REVIEW_HTML)fs.writeFileSync(process.env.ACTION_REVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/actions-preview.css"></head><body style="margin:0;background:black;color:white;padding:20px;max-width:520px">'+document.body.innerHTML+'</body></html>');
 fireEvent.click(screen.getByRole('button',{name:'Confirm add to cart'}));
 await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('Request processed'));
 expect(api.post).toHaveBeenCalledWith('/ai-ordering/cart/add',{product_id:7,quantity:2},{headers:{'Idempotency-Key':'00000000-0000-4000-8000-000000000001'}});
 expect(useCartStore.getState().items[0]?.quantity).toBe(2);
 if(process.env.ACTION_PREVIEW_HTML)fs.writeFileSync(process.env.ACTION_PREVIEW_HTML,'<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="file:///tmp/actions-preview.css"></head><body style="margin:0;background:black;color:white;padding:20px;max-width:520px">'+document.body.innerHTML+'</body></html>');
});
it('keeps uncertain operation locked and offers authoritative cart review, not blind retry',async()=>{
 jest.mocked(api.post).mockRejectedValue(new Error('timeout'));render(<AssistantAction action={action}/>);
 fireEvent.click(screen.getByRole('button',{name:'Confirm add to cart'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Do not submit');
 expect(screen.queryByRole('button')).not.toBeInTheDocument();expect(api.post).toHaveBeenCalledTimes(1);
});
it('opens tracking only for a safe literal owned-order route',()=>{
 const {rerender}=render(<AssistantAction action={{action:'track_order',payload:{order_id:'7'}}}/>);
 expect(screen.getByRole('link')).toHaveAttribute('href','/tracking/7');
 rerender(<AssistantAction action={{action:'track_order',payload:{order_id:'../../admin'}}}/>);expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
it('does not pretend to create a human ticket or use model-supplied destination',()=>{
 render(<AssistantAction action={{action:'initiate_support_handoff',payload:{url:'https://untrusted.invalid'}}}/>);
 expect(screen.getByRole('status')).toHaveTextContent('No ticket or callback');expect(screen.getByRole('link')).toHaveAttribute('href','/help');
});
it('does not execute old model add_to_cart actions with user identifiers',()=>{
 render(<AssistantAction action={{action:'add_to_cart',payload:{userId:'other',sku:'7',qty:99}}}/>);expect(screen.queryByRole('button')).not.toBeInTheDocument();expect(api.post).not.toHaveBeenCalled();
});
